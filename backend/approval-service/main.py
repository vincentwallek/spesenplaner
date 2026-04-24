"""
Approval Service — Main FastAPI + gRPC Co-hosting Application.
Runs both a REST API (FastAPI) and a gRPC server concurrently.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db
from crud import list_records, get_record, get_record_by_expense, make_decision
from schemas import ApprovalResponse, DecisionRequest
from rest_client import notify_budget_service, notify_request_service

import approval_pb2_grpc
from grpc_server import ApprovalServiceServicer

logger = logging.getLogger(__name__)

# Global reference for gRPC server lifecycle
grpc_server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start gRPC server alongside FastAPI."""
    global grpc_server
    await init_db()

    # Start gRPC server
    grpc_server = grpc.aio.server()
    approval_pb2_grpc.add_ApprovalServiceServicer_to_server(
        ApprovalServiceServicer(), grpc_server
    )
    grpc_server.add_insecure_port("[::]:50051")
    await grpc_server.start()
    logger.info("gRPC server started on port 50051")

    yield

    # Shutdown gRPC server
    await grpc_server.stop(grace=5)
    logger.info("gRPC server stopped")


app = FastAPI(
    title="Approval Service — Genehmigung",
    description="Genehmigungslogik für Spesenanträge. "
                "Empfängt Anträge via gRPC, bietet REST-API für manuelle Entscheidungen. "
                "Kommuniziert via REST mit dem budget-service.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _record_to_response(record) -> dict:
    """Convert an ApprovalRecord to a response dict with HATEOAS links."""
    return {
        "id": record.id,
        "expense_id": record.expense_id,
        "title": record.title,
        "original_amount": record.original_amount,
        "currency": record.currency,
        "decision": record.decision,
        "reason": record.reason,
        "decided_by": record.decided_by,
        "submitted_by": record.submitted_by,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        "_links": ApprovalResponse.build_links(record.id, record.expense_id, record.decision),
    }


# =============================================
# Health Check
# =============================================

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "approval-service", "grpc_port": 50051}


# =============================================
# REST API Endpoints
# =============================================

@app.get("/approvals", tags=["Approvals"])
async def list_all_approvals(session: AsyncSession = Depends(get_db)):
    """List all approval records."""
    records = await list_records(session)
    items = [_record_to_response(r) for r in records]
    return {
        "items": items,
        "total": len(items),
        "_links": {
            "self": {"href": "/api/v1/approvals", "method": "GET", "rel": "self"},
        },
    }

@app.get("/approvals/expense/{expense_id}", tags=["Approvals"])
async def get_approval_for_expense(expense_id: str, session: AsyncSession = Depends(get_db)):
    """Get approval record by expense id."""
    record = await get_record_by_expense(session, expense_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    return _record_to_response(record)


@app.get("/approvals/{record_id}", tags=["Approvals"])
async def get_approval(record_id: str, session: AsyncSession = Depends(get_db)):
    """Get a single approval record."""
    record = await get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    return _record_to_response(record)


@app.post("/approvals/{record_id}/approve", tags=["Approvals"])
async def approve_expense(
    record_id: str,
    body: DecisionRequest = DecisionRequest(),
    session: AsyncSession = Depends(get_db),
    x_user_name: str = Header(default="manager"),
):
    """Manually approve an expense."""
    record = await get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    if record.decision is not None:
        raise HTTPException(status_code=400, detail="Decision already made")
    if record.submitted_by == x_user_name:
        raise HTTPException(status_code=403, detail="You cannot approve your own expense")

    record = await make_decision(
        session, record, "APPROVED",
        body.reason or "Manually approved",
        x_user_name,
    )
    await notify_request_service(record.expense_id, "APPROVED")

    # Forward to budget-service
    try:
        await notify_budget_service(
            expense_id=record.expense_id,
            title=record.title,
            amount=record.original_amount,
            currency=record.currency,
        )
    except Exception as e:
        logger.warning(f"Failed to notify budget-service: {e}")

    return _record_to_response(record)


@app.post("/approvals/{record_id}/reject", tags=["Approvals"])
async def reject_expense(
    record_id: str,
    body: DecisionRequest = DecisionRequest(),
    session: AsyncSession = Depends(get_db),
    x_user_name: str = Header(default="manager"),
):
    """Manually reject an expense."""
    record = await get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    if record.decision is not None:
        raise HTTPException(status_code=400, detail="Decision already made")
    if record.submitted_by == x_user_name:
        raise HTTPException(status_code=403, detail="You cannot reject your own expense")

    record = await make_decision(
        session, record, "REJECTED",
        body.reason or "Manually rejected",
        x_user_name,
    )
    await notify_request_service(record.expense_id, "REJECTED")
    return _record_to_response(record)


@app.post("/approvals/{record_id}/request_revision", tags=["Approvals"])
async def request_revision(
    record_id: str,
    body: DecisionRequest = DecisionRequest(),
    session: AsyncSession = Depends(get_db),
    x_user_name: str = Header(default="manager"),
):
    """Request a revision for an expense."""
    record = await get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    if record.decision is not None:
        raise HTTPException(status_code=400, detail="Decision already made")
    if record.submitted_by == x_user_name:
        raise HTTPException(status_code=403, detail="You cannot request revision on your own expense")

    record = await make_decision(
        session, record, "NEEDS_REVISION",
        body.reason or "Revision requested",
        x_user_name,
    )
    await notify_request_service(record.expense_id, "NEEDS_REVISION")
    return _record_to_response(record)
