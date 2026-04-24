"""
Budget Service — SQLAlchemy Models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime
from database import Base


class BudgetCheck(Base):
    """Records the budget verification for an approved expense."""
    __tablename__ = "budget_checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    expense_id = Column(String, nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    budget_available = Column(Float, default=10000.0)
    result = Column(String(25), nullable=True)  # BUDGET_CONFIRMED, BUDGET_DENIED
    checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
