"""
Budget Service — Main FastAPI Application.
Receives approved expenses, performs budget checks, and publishes
payout events to Kafka for the payout-service.
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db
from crud import check_budget, get_check, get_check_by_expense, list_checks, get_budget_summary, get_budget_metrics
from schemas import BudgetCheckRequest, BudgetCheckResponse
from kafka_producer import start_producer, stop_producer, publish_payout_event

import os

logger = logging.getLogger(__name__)

REQUEST_SERVICE_URL = os.getenv("REQUEST_SERVICE_URL", "http://localhost:3001")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and Kafka producer."""
    await init_db()
    await start_producer()
    yield
    await stop_producer()


app = FastAPI(
    title="Budget Service — Finanzprüfung",
    description="Prüft die finanzielle Deckung für genehmigte Spesenanträge. "
                "Empfängt REST-Anfragen vom approval-service, "
                "publiziert Kafka-Events an den payout-service.",
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


def _check_to_response(record) -> dict:
    """Convert a BudgetCheck to a response dict with HATEOAS links."""
    return {
        "id": record.id,
        "expense_id": record.expense_id,
        "title": record.title,
        "amount": record.amount,
        "amount_eur": record.amount_eur,
        "currency": record.currency,
        "budget_available": record.budget_available,
        "result": record.result,
        "checked_at": record.checked_at.isoformat() if record.checked_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "_links": BudgetCheckResponse.build_links(record.id, record.expense_id, record.result),
    }


async def _notify_request_service(expense_id: str, status: str):
    """Callback to request-service to update expense status."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(
                f"{REQUEST_SERVICE_URL}/expenses/{expense_id}/status",
                json={"status": status},
            )
            logger.info(f"Notified request-service: expense {expense_id} -> {status}")
    except Exception as e:
        logger.warning(f"Failed to notify request-service: {e}")


# =============================================
# Health Check
# =============================================

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "budget-service"}


# =============================================
# Metrics Endpoint (Monitoring)
# =============================================

@app.get("/metrics", tags=["Monitoring"])
async def metrics(session: AsyncSession = Depends(get_db)):
    """Aggregate budget metrics for the monitoring dashboard."""
    return await get_budget_metrics(session)


# =============================================
# REST API Endpoints
# =============================================

@app.post("/budgets/check", status_code=201, tags=["Budget"])
async def perform_budget_check(
    data: BudgetCheckRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Perform a budget check for an approved expense.
    Called by approval-service via REST.
    If budget is confirmed, publishes a Kafka event to payout-service.
    """
    # Check if already processed
    existing = await get_check_by_expense(session, data.expense_id)
    if existing:
        return _check_to_response(existing)

    # Perform budget check
    record = await check_budget(
        session, data.expense_id, data.title, data.amount, data.currency
    )

    # Notify request-service of the result
    await _notify_request_service(data.expense_id, record.result)

    # If confirmed, publish Kafka event for payout
    if record.result == "BUDGET_CONFIRMED":
        published = await publish_payout_event(
            expense_id=record.expense_id,
            title=record.title or "",
            amount=record.amount,
            currency=record.currency,
        )
        if published:
            logger.info(f"Payout event published for expense {record.expense_id}")
        else:
            logger.warning(f"Could not publish payout event for {record.expense_id}")

    return _check_to_response(record)


@app.get("/budgets", tags=["Budget"])
async def list_all_checks(session: AsyncSession = Depends(get_db)):
    """List all budget checks."""
    checks = await list_checks(session)
    items = [_check_to_response(c) for c in checks]
    return {
        "items": items,
        "total": len(items),
        "_links": {
            "self": {"href": "/api/v1/budgets", "method": "GET", "rel": "self"},
            "summary": {"href": "/api/v1/budgets/summary", "method": "GET", "rel": "summary"},
        },
    }


@app.get("/budgets/summary", tags=["Budget"])
async def budget_summary(session: AsyncSession = Depends(get_db)):
    """Get the current budget summary."""
    summary = await get_budget_summary(session)
    summary["_links"] = {
        "self": {"href": "/api/v1/budgets/summary", "method": "GET", "rel": "self"},
        "collection": {"href": "/api/v1/budgets", "method": "GET", "rel": "collection"},
    }
    return summary


@app.get("/budgets/{check_id}", tags=["Budget"])
async def get_single_check(check_id: str, session: AsyncSession = Depends(get_db)):
    """Get a single budget check by ID."""
    record = await get_check(session, check_id)
    if not record:
        raise HTTPException(status_code=404, detail="Budget check not found")
    return _check_to_response(record)


@app.get("/budgets/expense/{expense_id}", tags=["Budget"])
async def get_check_for_expense(expense_id: str, session: AsyncSession = Depends(get_db)):
    """Get budget check by expense id (manager-friendly traceability endpoint)."""
    record = await get_check_by_expense(session, expense_id)
    if not record:
        raise HTTPException(status_code=404, detail="Budget check not found for expense")
    return _check_to_response(record)
