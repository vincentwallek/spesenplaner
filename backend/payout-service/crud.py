"""
Payout Service — CRUD Operations.
"""

import random
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select
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
