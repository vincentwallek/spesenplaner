"""
Budget Service — Pydantic Schemas with HATEOAS Links.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BudgetCheckRequest(BaseModel):
    """Incoming request from approval-service."""
    expense_id: str
    title: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = "EUR"


class BudgetCheckResponse(BaseModel):
    """Response schema with HATEOAS links."""
    id: str
    expense_id: str
    title: Optional[str]
    amount: float
    currency: str
    budget_available: float
    result: Optional[str]
    checked_at: Optional[datetime]
    created_at: Optional[datetime]
    _links: Dict[str, Any] = {}

    model_config = {"from_attributes": True}

    @staticmethod
    def build_links(record_id: str, expense_id: str, result: Optional[str]) -> Dict[str, Any]:
        """Generate HATEOAS links based on budget check state."""
        links = {
            "self": {"href": f"/api/v1/budgets/{record_id}", "method": "GET", "rel": "self"},
            "expense": {"href": f"/api/v1/expenses/{expense_id}", "method": "GET", "rel": "expense"},
        }
        if result == "BUDGET_CONFIRMED":
            links["payout"] = {"href": f"/api/v1/payouts/{expense_id}", "method": "GET", "rel": "payout"}
        links["collection"] = {"href": "/api/v1/budgets", "method": "GET", "rel": "collection"}
        return links
