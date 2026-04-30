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


# Static exchange rates to EUR (consistent across services)
EXCHANGE_RATES_TO_EUR: dict[str, float] = {
    "EUR": 1.0,
    "USD": 0.92,
    "CHF": 1.05,
    "GBP": 1.17,
}


def convert_to_eur(amount: Optional[float], currency: Optional[str]) -> float:
    """Convert an amount to EUR using static exchange rates."""
    if amount is None:
        return 0.0
    curr = (currency or "EUR").upper().strip()
    rate = EXCHANGE_RATES_TO_EUR.get(curr, 1.0)
    return round(float(amount) * rate, 2)


async def get_payout_metrics(session: AsyncSession) -> dict:
    """Aggregate payout metrics for monitoring dashboard."""
    from datetime import datetime

    # Fetch all records for calculation
    result = await session.execute(select(PayoutRecord))
    all_records = list(result.scalars().all())
    
    total_count = len(all_records)

    # Status breakdown
    status_counts = {}
    for r in all_records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    # Total volume paid (converted to EUR)
    paid_records = [r for r in all_records if r.status == "PAID"]
    total_paid_eur = round(sum(convert_to_eur(r.amount, r.currency) for r in paid_records), 2)

    # Total volume failed (converted to EUR)
    failed_records = [r for r in all_records if r.status == "PAYOUT_FAILED"]
    total_failed_eur = round(sum(convert_to_eur(r.amount, r.currency) for r in failed_records), 2)

    # Today's payouts (naive comparison)
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = sum(1 for r in all_records if r.created_at and r.created_at >= today_start)

    # Success rate
    paid_count = status_counts.get("PAID", 0)
    failed_count = status_counts.get("PAYOUT_FAILED", 0)
    success_rate = round((paid_count / (paid_count + failed_count) * 100), 1) if (paid_count + failed_count) > 0 else 0.0

    return {
        "total_count": total_count,
        "status_counts": status_counts,
        "total_paid": total_paid_eur,
        "total_failed": total_failed_eur,
        "today_count": today_count,
        "success_rate": success_rate,
    }

