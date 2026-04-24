"""
Approval Service — SQLAlchemy Models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text
from database import Base


class ApprovalRecord(Base):
    """Records the approval decision for an expense."""
    __tablename__ = "approval_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    expense_id = Column(String, nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=True)
    original_amount = Column(Float, nullable=True)
    currency = Column(String(3), default="EUR")
    decision = Column(String(20), nullable=True)  # APPROVED, REJECTED
    reason = Column(Text, nullable=True)
    decided_by = Column(String(100), default="auto-approver")
    submitted_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    decided_at = Column(DateTime, nullable=True)
