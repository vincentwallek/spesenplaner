"""
Budget Service — CRUD Operations.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import BudgetCheck


# Simulated total budget pool
TOTAL_BUDGET = 10000.0


async def check_budget(
    session: AsyncSession,
    expense_id: str,
    title: str,
    amount: float,
    currency: str,
) -> BudgetCheck:
    """
    Check if there is sufficient budget for the expense.
    Simple simulation: budget starts at 10,000 EUR, each confirmed expense reduces it.
    """
    # Calculate remaining budget
    result = await session.execute(
        select(BudgetCheck).where(BudgetCheck.result == "BUDGET_CONFIRMED")
    )
    confirmed = result.scalars().all()
    spent = sum(c.amount for c in confirmed)
    remaining = TOTAL_BUDGET - spent

    # Create budget check record
    record = BudgetCheck(
        expense_id=expense_id,
        title=title,
        amount=amount,
        currency=currency,
        budget_available=remaining,
        checked_at=datetime.now(timezone.utc),
    )

    if amount <= remaining:
        record.result = "BUDGET_CONFIRMED"
    else:
        record.result = "BUDGET_DENIED"

    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_check(session: AsyncSession, check_id: str) -> Optional[BudgetCheck]:
    """Get a single budget check by ID."""
    result = await session.execute(
        select(BudgetCheck).where(BudgetCheck.id == check_id)
    )
    return result.scalar_one_or_none()


async def get_check_by_expense(session: AsyncSession, expense_id: str) -> Optional[BudgetCheck]:
    """Get budget check by expense ID."""
    result = await session.execute(
        select(BudgetCheck)
        .where(BudgetCheck.expense_id == expense_id)
        .order_by(BudgetCheck.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_checks(session: AsyncSession) -> List[BudgetCheck]:
    """List all budget checks."""
    result = await session.execute(
        select(BudgetCheck).order_by(BudgetCheck.created_at.desc())
    )
    return list(result.scalars().all())


async def get_budget_summary(session: AsyncSession) -> dict:
    """Get a summary of the budget status."""
    result = await session.execute(
        select(BudgetCheck).where(BudgetCheck.result == "BUDGET_CONFIRMED")
    )
    confirmed = result.scalars().all()
    spent = sum(c.amount for c in confirmed)
    return {
        "total_budget": TOTAL_BUDGET,
        "spent": spent,
        "remaining": TOTAL_BUDGET - spent,
        "confirmed_count": len(confirmed),
    }


async def get_budget_metrics(session: AsyncSession) -> dict:
    """Aggregate budget metrics for monitoring dashboard."""
    # Total checks
    total_result = await session.execute(select(func.count(BudgetCheck.id)))
    total_count = total_result.scalar() or 0

    # Result breakdown
    result_data = await session.execute(
        select(BudgetCheck.result, func.count(BudgetCheck.id))
        .group_by(BudgetCheck.result)
    )
    result_counts = {row[0]: row[1] for row in result_data.all()}

    # Budget summary
    confirmed_result = await session.execute(
        select(BudgetCheck).where(BudgetCheck.result == "BUDGET_CONFIRMED")
    )
    confirmed = confirmed_result.scalars().all()
    spent = sum(c.amount for c in confirmed)

    # Total volume checked
    vol_result = await session.execute(
        select(func.sum(BudgetCheck.amount))
    )
    total_volume_checked = round(vol_result.scalar() or 0.0, 2)

    # Average check amount
    avg_result = await session.execute(
        select(func.avg(BudgetCheck.amount))
    )
    avg_check_amount = round(avg_result.scalar() or 0.0, 2)

    return {
        "total_count": total_count,
        "result_counts": result_counts,
        "total_budget": TOTAL_BUDGET,
        "spent": round(spent, 2),
        "remaining": round(TOTAL_BUDGET - spent, 2),
        "total_volume_checked": total_volume_checked,
        "average_check_amount": avg_check_amount,
    }

