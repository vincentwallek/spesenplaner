"""
Payout Service — Main FastAPI Application.
Processes payouts for budget-confirmed expenses.
Consumes Kafka events from budget-service as a background task.
Also provides REST API for manual payout queries and retries.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db
from crud import list_records, get_record, get_record_by_expense, process_payout, get_payout_metrics
from schemas import PayoutResponse
from kafka_consumer import consume_payout_events

import os

logger = logging.getLogger(__name__)

REQUEST_SERVICE_URL = os.getenv("REQUEST_SERVICE_URL", "http://localhost:3001")

# Reference to the Kafka consumer background task
_consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and start Kafka consumer as background task."""
    global _consumer_task
    await init_db()

    # Start Kafka consumer as background task
    _consumer_task = asyncio.create_task(consume_payout_events())
    logger.info("Kafka consumer background task started")

    yield

    # Cancel consumer task on shutdown
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    logger.info("Kafka consumer background task stopped")


app = FastAPI(
    title="Payout Service — Auszahlung",
    description="Führt die finale Auszahlung durch. "
                "Empfängt Kafka-Events vom budget-service. "
                "Bietet REST-API für Abfragen und Wiederholungen.",
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
    """Convert a PayoutRecord to a response dict with HATEOAS links."""
    return {
        "id": record.id,
        "expense_id": record.expense_id,
        "title": record.title,
        "amount": record.amount,
        "currency": record.currency,
        "status": record.status,
        "failure_reason": record.failure_reason,
        "paid_at": record.paid_at.isoformat() if record.paid_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "_links": PayoutResponse.build_links(record.id, record.expense_id, record.status),
    }


async def _notify_request_service(expense_id: str, status: str):
    """Callback to request-service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(
                f"{REQUEST_SERVICE_URL}/expenses/{expense_id}/status",
                json={"status": status},
            )
    except Exception as e:
        logger.warning(f"Failed to notify request-service: {e}")


# =============================================
# Health Check
# =============================================

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "payout-service"}


# =============================================
# Metrics Endpoint (Monitoring)
# =============================================

@app.get("/metrics", tags=["Monitoring"])
async def metrics(session: AsyncSession = Depends(get_db)):
    """Aggregate payout metrics for the monitoring dashboard."""
    return await get_payout_metrics(session)


# =============================================
# REST API Endpoints
# =============================================

@app.get("/payouts", tags=["Payouts"])
async def list_all_payouts(session: AsyncSession = Depends(get_db)):
    """List all payout records."""
    records = await list_records(session)
    items = [_record_to_response(r) for r in records]
    return {
        "items": items,
        "total": len(items),
        "_links": {
            "self": {"href": "/api/v1/payouts", "method": "GET", "rel": "self"},
        },
    }


@app.get("/payouts/{record_id}", tags=["Payouts"])
async def get_payout(record_id: str, session: AsyncSession = Depends(get_db)):
    """Get a single payout record."""
    record = await get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Payout record not found")
    return _record_to_response(record)


@app.get("/payouts/expense/{expense_id}", tags=["Payouts"])
async def get_payout_for_expense(expense_id: str, session: AsyncSession = Depends(get_db)):
    """Get payout information by expense id for workflow traceability."""
    record = await get_record_by_expense(session, expense_id)
    if not record:
        raise HTTPException(status_code=404, detail="Payout record not found for expense")
    return _record_to_response(record)


@app.post("/payouts/{record_id}/retry", tags=["Payouts"])
async def retry_payout(record_id: str, session: AsyncSession = Depends(get_db)):
    """Retry a failed payout."""
    record = await get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Payout record not found")
    if record.status != "PAYOUT_FAILED":
        raise HTTPException(status_code=400, detail="Can only retry failed payouts")

    # Re-process payout
    updated = await process_payout(
        session, record.expense_id, record.title, record.amount, record.currency
    )

    # Notify request-service
    await _notify_request_service(updated.expense_id, updated.status)

    return _record_to_response(updated)
