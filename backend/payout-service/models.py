"""
Payout Service — SQLAlchemy Models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text
from database import Base


class PayoutRecord(Base):
    """Records the payout execution for a budget-confirmed expense."""
    __tablename__ = "payout_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    expense_id = Column(String, nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    status = Column(String(25), nullable=True)  # PAID, PAYOUT_FAILED
    failure_reason = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
