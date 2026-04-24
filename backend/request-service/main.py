"""
Request Service — Main FastAPI Application.
CRUD endpoints for expense management with HATEOAS support.
Communicates with approval-service via gRPC when submitting expenses.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db
from crud import (
    create_expense,
    get_expense,
    list_expenses,
    update_expense,
    delete_expense,
    update_expense_status,
    can_access_expense,
)
from schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Request Service — Spesen-Eingang",
    description="CRUD-API für Spesenanträge mit HATEOAS. "
                "Kommuniziert via gRPC mit dem approval-service.",
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


def _expense_to_response(expense) -> dict:
    """Convert an Expense ORM object to a dict with HATEOAS links."""
    data = {
        "id": expense.id,
        "title": expense.title,
        "description": expense.description,
        "amount": expense.amount,
        "currency": expense.currency,
        "status": expense.status,
        "category": expense.category,
        "created_by": expense.created_by,
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
        "updated_at": expense.updated_at.isoformat() if expense.updated_at else None,
        "_links": ExpenseResponse.build_links(expense.id, expense.status),
    }
    return data


# =============================================
# Health Check
# =============================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check for Kubernetes probes."""
    return {"status": "healthy", "service": "request-service"}


# =============================================
# CRUD Endpoints
# =============================================

@app.post("/expenses", status_code=201, tags=["Expenses"])
async def create_new_expense(
    data: ExpenseCreate,
    session: AsyncSession = Depends(get_db),
    x_user_name: str = Header(default="anonymous"),
):
    """Create a new expense report in DRAFT status."""
    expense = await create_expense(session, data, created_by=x_user_name)
    return _expense_to_response(expense)


@app.get("/expenses", tags=["Expenses"])
async def list_all_expenses(
    session: AsyncSession = Depends(get_db),
    x_user_name: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default="user"),
    status_filter: Optional[str] = None,
):
    """List all expenses (optionally filtered by status)."""
    created_by = None if (x_user_role or "user").lower() in ("manager", "admin") else x_user_name
    expenses = await list_expenses(session, created_by=created_by, status=status_filter)
    items = [_expense_to_response(e) for e in expenses]
    return {
        "items": items,
        "total": len(items),
        "_links": {
            "self": {"href": "/api/v1/expenses", "method": "GET", "rel": "self"},
            "create": {"href": "/api/v1/expenses", "method": "POST", "rel": "create"},
        },
    }


@app.get("/expenses/{expense_id}", tags=["Expenses"])
async def get_single_expense(
    expense_id: str,
    session: AsyncSession = Depends(get_db),
    x_user_name: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default="user"),
):
    """Get a single expense by ID."""
    expense = await get_expense(session, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if not can_access_expense(expense, x_user_name, x_user_role):
        raise HTTPException(status_code=403, detail="Access denied")
    return _expense_to_response(expense)


@app.put("/expenses/{expense_id}", tags=["Expenses"])
async def update_existing_expense(
    expense_id: str,
    data: ExpenseUpdate,
    session: AsyncSession = Depends(get_db),
    x_user_name: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default="user"),
):
    """Update an expense (only in DRAFT or REJECTED status)."""
    existing = await get_expense(session, expense_id)
    if not existing:
        raise HTTPException(
            status_code=400,
            detail="Expense not found or cannot be updated in current status",
        )
    if not can_access_expense(existing, x_user_name, x_user_role):
        raise HTTPException(status_code=403, detail="Access denied")
    expense = await update_expense(session, expense_id, data)
    if not expense:
        raise HTTPException(
            status_code=400,
            detail="Expense not found or cannot be updated in current status",
        )
    return _expense_to_response(expense)


@app.delete("/expenses/{expense_id}", status_code=204, tags=["Expenses"])
async def delete_existing_expense(
    expense_id: str,
    session: AsyncSession = Depends(get_db),
    x_user_name: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default="user"),
):
    """Delete an expense (only in DRAFT or REJECTED status)."""
    existing = await get_expense(session, expense_id)
    if not existing:
        raise HTTPException(
            status_code=400,
            detail="Expense not found or cannot be deleted in current status",
        )
    if not can_access_expense(existing, x_user_name, x_user_role):
        raise HTTPException(status_code=403, detail="Access denied")
    success = await delete_expense(session, expense_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Expense not found or cannot be deleted in current status",
        )


# =============================================
# Workflow Endpoints
# =============================================

@app.post("/expenses/{expense_id}/submit", tags=["Workflow"])
async def submit_expense(
    expense_id: str,
    session: AsyncSession = Depends(get_db),
    x_user_name: str = Header(default="anonymous"),
    x_user_role: Optional[str] = Header(default="user"),
):
    """
    Submit an expense for approval.
    Changes status from DRAFT to SUBMITTED, then sends to approval-service via gRPC.
    """
    expense = await get_expense(session, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if not can_access_expense(expense, x_user_name, x_user_role):
        raise HTTPException(status_code=403, detail="Access denied")
    if expense.status not in ("DRAFT", "NEEDS_REVISION"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit expense in '{expense.status}' status. Must be DRAFT or NEEDS_REVISION.",
        )

    # Update status to SUBMITTED
    expense = await update_expense_status(session, expense_id, "SUBMITTED")

    # Call approval-service via gRPC
    try:
        from grpc_client import submit_for_approval

        result = await submit_for_approval(
            expense_id=expense.id,
            title=expense.title,
            amount=expense.amount,
            currency=expense.currency,
            description=expense.description or "",
            submitted_by=x_user_name,
        )

        # Keep status as SUBMITTED until manager decision arrives.
        new_status = result.get("status", "SUBMITTED")
        if new_status in ("APPROVED", "REJECTED"):
            expense = await update_expense_status(session, expense_id, new_status)

        return {
            **_expense_to_response(expense),
            "approval_result": result,
        }
    except Exception as e:
        # If gRPC call fails, keep status as SUBMITTED for retry
        logger.warning(f"gRPC call to approval-service failed: {e}. Keeping status as SUBMITTED.")
        return {
            **_expense_to_response(expense),
            "approval_result": {"status": "PENDING", "reason": "Approval service temporarily unavailable"},
        }


@app.post("/expenses/{expense_id}/cancel", tags=["Workflow"])
async def cancel_expense(
    expense_id: str,
    session: AsyncSession = Depends(get_db),
    x_user_name: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default="user"),
):
    """Cancel a submitted expense (back to DRAFT)."""
    expense = await get_expense(session, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if not can_access_expense(expense, x_user_name, x_user_role):
        raise HTTPException(status_code=403, detail="Access denied")
    if expense.status != "SUBMITTED":
        raise HTTPException(status_code=400, detail="Can only cancel SUBMITTED expenses")

    expense = await update_expense_status(session, expense_id, "DRAFT")
    return _expense_to_response(expense)


# =============================================
# Internal Callback Endpoint (for other services)
# =============================================

@app.put("/expenses/{expense_id}/status", tags=["Internal"])
async def update_status_callback(
    expense_id: str,
    body: dict,
    session: AsyncSession = Depends(get_db),
):
    """
    Internal endpoint for other services to update expense status.
    Used by budget-service and payout-service to report back results.
    """
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing 'status' field")

    valid_statuses = {
        "APPROVED", "REJECTED", "BUDGET_CONFIRMED",
        "BUDGET_DENIED", "PAID", "PAYOUT_FAILED", "NEEDS_REVISION",
    }
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    expense = await update_expense_status(session, expense_id, new_status)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    return _expense_to_response(expense)
