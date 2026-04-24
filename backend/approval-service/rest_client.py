"""
Approval Service — REST Client.
Sends approved expenses to the budget-service via REST.
"""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

BUDGET_SERVICE_URL = os.getenv("BUDGET_SERVICE_URL", "http://localhost:3003")
REQUEST_SERVICE_URL = os.getenv("REQUEST_SERVICE_URL", "http://request-service:3001")


async def notify_budget_service(
    expense_id: str,
    title: str,
    amount: float,
    currency: str,
) -> dict:
    """
    Send an approved expense to the budget-service for financial checking via REST.
    This is the REST leg of the inter-service communication chain.
    """
    url = f"{BUDGET_SERVICE_URL}/budgets/check"

    payload = {
        "expense_id": expense_id,
        "title": title,
        "amount": amount,
        "currency": currency,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Budget-service response for {expense_id}: {result}")
            return result
    except httpx.ConnectError:
        logger.error(f"Cannot connect to budget-service at {BUDGET_SERVICE_URL}")
        raise Exception("Budget service unavailable")
    except httpx.HTTPStatusError as e:
        logger.error(f"Budget-service returned error: {e.response.status_code}")
        raise


async def notify_request_service(expense_id: str, status: str) -> None:
    """Update request-service expense status after manager decision."""
    url = f"{REQUEST_SERVICE_URL}/expenses/{expense_id}/status"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(url, json={"status": status})
            response.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to notify request-service for {expense_id}: {e}")
