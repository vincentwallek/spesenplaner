"""
Payout Service — Pydantic Schemas with HATEOAS Links.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class PayoutResponse(BaseModel):
    """Response schema for a payout record."""
    id: str
    expense_id: str
    title: Optional[str]
    amount: float
    currency: str
    status: Optional[str]
    failure_reason: Optional[str]
    paid_at: Optional[datetime]
    created_at: Optional[datetime]
    _links: Dict[str, Any] = {}

    model_config = {"from_attributes": True}

    @staticmethod
    def build_links(record_id: str, expense_id: str, payout_status: Optional[str]) -> Dict[str, Any]:
        """Generate HATEOAS links based on payout state."""
        links = {
            "self": {"href": f"/api/v1/payouts/{record_id}", "method": "GET", "rel": "self"},
            "expense": {"href": f"/api/v1/expenses/{expense_id}", "method": "GET", "rel": "expense"},
        }
        if payout_status == "PAYOUT_FAILED":
            links["retry"] = {"href": f"/api/v1/payouts/{record_id}/retry", "method": "POST", "rel": "retry"}
        links["collection"] = {"href": "/api/v1/payouts", "method": "GET", "rel": "collection"}
        return links
