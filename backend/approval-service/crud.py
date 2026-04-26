"""
Approval Service — CRUD Operations.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func
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


async def get_approval_metrics(session: AsyncSession) -> dict:
    """Aggregate approval metrics for monitoring dashboard."""
    # Total records
    total_result = await session.execute(select(func.count(ApprovalRecord.id)))
    total_count = total_result.scalar() or 0

    # Decision breakdown
    decision_result = await session.execute(
        select(ApprovalRecord.decision, func.count(ApprovalRecord.id))
        .group_by(ApprovalRecord.decision)
    )
    decision_counts = {}
    for row in decision_result.all():
        key = row[0] or "PENDING"
        decision_counts[key] = row[1]

    approved = decision_counts.get("APPROVED", 0)
    rejected = decision_counts.get("REJECTED", 0)
    needs_revision = decision_counts.get("NEEDS_REVISION", 0)
    pending = decision_counts.get("PENDING", 0)
    decided_total = approved + rejected + needs_revision

    approval_rate = round((approved / decided_total * 100), 1) if decided_total > 0 else 0.0

    # Total volume approved
    vol_result = await session.execute(
        select(func.sum(ApprovalRecord.original_amount))
        .where(ApprovalRecord.decision == "APPROVED")
    )
    approved_volume = round(vol_result.scalar() or 0.0, 2)

    # Average processing time (decided_at - created_at) in hours
    decided_records = await session.execute(
        select(ApprovalRecord)
        .where(ApprovalRecord.decided_at.isnot(None))
    )
    processing_times = []
    for r in decided_records.scalars().all():
        if r.decided_at and r.created_at:
            delta = (r.decided_at - r.created_at).total_seconds() / 3600
            processing_times.append(delta)
    avg_processing_hours = round(sum(processing_times) / len(processing_times), 2) if processing_times else 0.0

    # Decisions per reviewer
    reviewer_result = await session.execute(
        select(ApprovalRecord.decided_by, func.count(ApprovalRecord.id))
        .where(ApprovalRecord.decided_by.isnot(None))
        .group_by(ApprovalRecord.decided_by)
        .order_by(func.count(ApprovalRecord.id).desc())
        .limit(10)
    )
    reviewers = [
        {"reviewer": r[0], "count": r[1]}
        for r in reviewer_result.all()
    ]

    return {
        "total_count": total_count,
        "decision_counts": decision_counts,
        "approval_rate": approval_rate,
        "approved_volume": approved_volume,
        "average_processing_hours": avg_processing_hours,
        "reviewers": reviewers,
    }

