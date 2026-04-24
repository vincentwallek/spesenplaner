"""
Request Service — SQLAlchemy Models.
Defines the Expense entity stored in this service's own database.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Text

from database import Base


class Expense(Base):
    """Expense report entity — the core domain object of the request-service."""
    __tablename__ = "expenses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    status = Column(String(30), default="DRAFT")
    # Possible statuses: DRAFT, SUBMITTED, APPROVED, REJECTED,
    #                    BUDGET_CONFIRMED, BUDGET_DENIED, PAID, PAYOUT_FAILED
    category = Column(String(50), nullable=True)  # e.g., travel, food, hotel
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
