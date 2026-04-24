"""
Approval Service — Pydantic Schemas with HATEOAS Links.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    """Response schema for an approval record."""
    id: str
    expense_id: str
    title: Optional[str]
    original_amount: Optional[float]
    currency: str
    decision: Optional[str]
    reason: Optional[str]
    decided_by: str
    submitted_by: Optional[str]
    created_at: Optional[datetime]
    decided_at: Optional[datetime]
    _links: Dict[str, Any] = {}

    model_config = {"from_attributes": True}

    @staticmethod
    def build_links(record_id: str, expense_id: str, decision: Optional[str]) -> Dict[str, Any]:
        """Generate HATEOAS links based on approval state."""
        links = {
            "self": {"href": f"/api/v1/approvals/{record_id}", "method": "GET", "rel": "self"},
            "expense": {"href": f"/api/v1/expenses/{expense_id}", "method": "GET", "rel": "expense"},
        }
        if decision is None:
            links["approve"] = {"href": f"/api/v1/approvals/{record_id}/approve", "method": "POST", "rel": "approve"}
            links["reject"] = {"href": f"/api/v1/approvals/{record_id}/reject", "method": "POST", "rel": "reject"}
            links["request_revision"] = {"href": f"/api/v1/approvals/{record_id}/request_revision", "method": "POST", "rel": "request_revision"}
        elif decision == "APPROVED":
            links["budget_check"] = {"href": f"/api/v1/budgets/{expense_id}", "method": "GET", "rel": "budget_check"}
        links["collection"] = {"href": "/api/v1/approvals", "method": "GET", "rel": "collection"}
        return links


class DecisionRequest(BaseModel):
    """Request body for manual approval/rejection."""
    reason: Optional[str] = None
