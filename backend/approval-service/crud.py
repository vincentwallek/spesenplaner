"""
Approval Service — CRUD Operations.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ApprovalRecord


async def create_approval_record(
    session: AsyncSession,
    expense_id: str,
    title: str,
    amount: float,
    currency: str,
    submitted_by: str,
) -> ApprovalRecord:
    """Create a new approval record for an incoming expense."""
    record = ApprovalRecord(
        expense_id=expense_id,
        title=title,
        original_amount=amount,
        currency=currency,
        submitted_by=submitted_by,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_record(session: AsyncSession, record_id: str) -> Optional[ApprovalRecord]:
    """Get a single approval record by ID."""
    result = await session.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == record_id)
    )
    return result.scalar_one_or_none()


async def get_record_by_expense(session: AsyncSession, expense_id: str) -> Optional[ApprovalRecord]:
    """Get approval record by expense ID."""
    result = await session.execute(
        select(ApprovalRecord)
        .where(ApprovalRecord.expense_id == expense_id)
        .order_by(ApprovalRecord.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_records(session: AsyncSession) -> List[ApprovalRecord]:
    """List all approval records."""
    result = await session.execute(
        select(ApprovalRecord).order_by(ApprovalRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def make_decision(
    session: AsyncSession,
    record: ApprovalRecord,
    decision: str,
    reason: str,
    decided_by: str,
) -> ApprovalRecord:
    """Record an approval decision (APPROVED or REJECTED)."""
    record.decision = decision
    record.reason = reason
    record.decided_by = decided_by
    record.decided_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(record)
    return record


