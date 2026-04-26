"""
Payout Service — CRUD Operations.
"""

import random
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import PayoutRecord


async def process_payout(
    session: AsyncSession,
    expense_id: str,
    title: str,
    amount: float,
    currency: str,
) -> PayoutRecord:
    """
    Process a payout for an expense.
    Simulates a payment gateway:
    - 90% chance of success (PAID)
    - 10% chance of failure (PAYOUT_FAILED)
    """
    # Check if already processed
    existing = await get_record_by_expense(session, expense_id)
    if existing and existing.status == "PAID":
        return existing

    # If there's a failed record, update it (retry)
    if existing and existing.status == "PAYOUT_FAILED":
        record = existing
    else:
        record = PayoutRecord(
            expense_id=expense_id,
            title=title,
            amount=amount,
            currency=currency,
        )
        session.add(record)

    # Simulate payment processing (90% success rate)
    if random.random() < 0.9:
        record.status = "PAID"
        record.paid_at = datetime.now(timezone.utc)
        record.failure_reason = None
    else:
        record.status = "PAYOUT_FAILED"
        record.failure_reason = "Simulated payment gateway error. Please retry."

    await session.commit()
    await session.refresh(record)
    return record


async def get_record(session: AsyncSession, record_id: str) -> Optional[PayoutRecord]:
    """Get a single payout record by ID."""
    result = await session.execute(
        select(PayoutRecord).where(PayoutRecord.id == record_id)
    )
    return result.scalar_one_or_none()


async def get_record_by_expense(session: AsyncSession, expense_id: str) -> Optional[PayoutRecord]:
    """Get payout record by expense ID."""
    result = await session.execute(
        select(PayoutRecord)
        .where(PayoutRecord.expense_id == expense_id)
        .order_by(PayoutRecord.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_records(session: AsyncSession) -> List[PayoutRecord]:
    """List all payout records."""
    result = await session.execute(
        select(PayoutRecord).order_by(PayoutRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def get_payout_metrics(session: AsyncSession) -> dict:
    """Aggregate payout metrics for monitoring dashboard."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total records
    total_result = await session.execute(select(func.count(PayoutRecord.id)))
    total_count = total_result.scalar() or 0

    # Status breakdown
    status_result = await session.execute(
        select(PayoutRecord.status, func.count(PayoutRecord.id))
        .group_by(PayoutRecord.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # Total volume paid
    paid_vol = await session.execute(
        select(func.sum(PayoutRecord.amount))
        .where(PayoutRecord.status == "PAID")
    )
    total_paid = round(paid_vol.scalar() or 0.0, 2)

    # Total volume failed
    failed_vol = await session.execute(
        select(func.sum(PayoutRecord.amount))
        .where(PayoutRecord.status == "PAYOUT_FAILED")
    )
    total_failed = round(failed_vol.scalar() or 0.0, 2)

    # Today's payouts
    today_result = await session.execute(
        select(func.count(PayoutRecord.id))
        .where(PayoutRecord.created_at >= today_start)
    )
    today_count = today_result.scalar() or 0

    # Success rate
    paid = status_counts.get("PAID", 0)
    failed = status_counts.get("PAYOUT_FAILED", 0)
    success_rate = round((paid / (paid + failed) * 100), 1) if (paid + failed) > 0 else 0.0

    return {
        "total_count": total_count,
        "status_counts": status_counts,
        "total_paid": total_paid,
        "total_failed": total_failed,
        "today_count": today_count,
        "success_rate": success_rate,
    }

