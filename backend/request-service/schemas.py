"""
Request Service — Pydantic Schemas with HATEOAS Links.
Defines request/response models including hypermedia links.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class HATEOASLink(BaseModel):
    """A single HATEOAS link."""
    href: str
    method: str
    rel: Optional[str] = None


class ExpenseCreate(BaseModel):
    """Schema for creating a new expense."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="EUR", max_length=3)
    category: Optional[str] = Field(default=None, max_length=50)


class ExpenseUpdate(BaseModel):
    """Schema for updating an existing expense (partial update)."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=3)
    category: Optional[str] = Field(None, max_length=50)


class ExpenseResponse(BaseModel):
    """Schema for expense response with HATEOAS links."""
    id: str
    title: str
    description: Optional[str]
    amount: float
    currency: str
    status: str
    category: Optional[str]
    created_by: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    _links: Dict[str, HATEOASLink] = {}

    model_config = {"from_attributes": True}

    @staticmethod
    def build_links(expense_id: str, status: str) -> Dict[str, Any]:
        """Generate HATEOAS links based on current expense status."""
        base = f"/api/v1/expenses/{expense_id}"
        links = {
            "self": {"href": base, "method": "GET", "rel": "self"},
        }

        if status in ("DRAFT", "NEEDS_REVISION"):
            links["update"] = {"href": base, "method": "PUT", "rel": "update"}
            links["delete"] = {"href": base, "method": "DELETE", "rel": "delete"}
            links["submit"] = {"href": f"{base}/submit", "method": "POST", "rel": "submit"}
        elif status == "SUBMITTED":
            links["cancel"] = {"href": f"{base}/cancel", "method": "POST", "rel": "cancel"}
        elif status == "APPROVED":
            links["budget_check"] = {"href": f"/api/v1/budgets/expense/{expense_id}", "method": "GET", "rel": "budget_check"}
        elif status == "BUDGET_CONFIRMED":
            links["payout"] = {"href": f"/api/v1/payouts/expense/{expense_id}", "method": "GET", "rel": "payout"}
        elif status == "REJECTED":
            links["resubmit"] = {"href": base, "method": "PUT", "rel": "resubmit"}
            links["delete"] = {"href": base, "method": "DELETE", "rel": "delete"}
        elif status in ("PAID", "PAYOUT_FAILED", "BUDGET_DENIED"):
            pass  # Terminal states — no further actions

        links["collection"] = {"href": "/api/v1/expenses", "method": "GET", "rel": "collection"}
        return links


class ExpenseListResponse(BaseModel):
    """Schema for paginated list of expenses."""
    items: List[dict]
    total: int
    _links: Dict[str, Any] = {}

    @staticmethod
    def build_links() -> Dict[str, Any]:
        return {
            "self": {"href": "/api/v1/expenses", "method": "GET", "rel": "self"},
            "create": {"href": "/api/v1/expenses", "method": "POST", "rel": "create"},
        }
