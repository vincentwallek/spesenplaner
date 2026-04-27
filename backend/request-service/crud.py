"""
Request Service — CRUD Operations.
Database operations for creating, reading, updating, and deleting expenses.
"""

from typing import Optional, List

from sqlalchemy import select, func, case, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models import Expense
from schemas import ExpenseCreate, ExpenseUpdate


# Static exchange rates to EUR (must match budget-service rates)
EXCHANGE_RATES_TO_EUR: dict[str, float] = {
    "EUR": 1.0,
    "USD": 0.92,
    "CHF": 1.05,
    "GBP": 1.17,
}


def convert_to_eur(amount: float, currency: str) -> float:
    """Convert an amount to EUR using static exchange rates."""
    rate = EXCHANGE_RATES_TO_EUR.get(currency.upper(), 1.0)
    return round(amount * rate, 2)


async def create_expense(session: AsyncSession, data: ExpenseCreate, created_by: str) -> Expense:
    """Create a new expense in DRAFT status."""
    expense = Expense(
        title=data.title,
        description=data.description,
        amount=data.amount,
        currency=data.currency,
        category=data.category,
        created_by=created_by,
        status="DRAFT",
    )
    session.add(expense)
    await session.commit()
    await session.refresh(expense)
    return expense


async def get_expense(session: AsyncSession, expense_id: str) -> Optional[Expense]:
    """Get a single expense by ID."""
    result = await session.execute(select(Expense).where(Expense.id == expense_id))
    return result.scalar_one_or_none()


def can_access_expense(expense: Expense, username: Optional[str], role: Optional[str]) -> bool:
    """Role-based access: managers/admins can access all, users only own records."""
    normalized_role = (role or "user").lower()
    if normalized_role in ("manager", "admin"):
        return True
    return bool(username) and expense.created_by == username


async def list_expenses(
    session: AsyncSession,
    created_by: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Expense]:
    """List all expenses with optional filters."""
    query = select(Expense)
    if created_by:
        query = query.where(Expense.created_by == created_by)
    if status:
        query = query.where(Expense.status == status)
    query = query.order_by(Expense.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_expense(
    session: AsyncSession,
    expense_id: str,
    data: ExpenseUpdate,
) -> Optional[Expense]:
    """Update an expense (only allowed in DRAFT, REJECTED, or NEEDS_REVISION status)."""
    expense = await get_expense(session, expense_id)
    if not expense:
        return None
    if expense.status not in ("DRAFT", "REJECTED", "NEEDS_REVISION"):
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)

    if expense.status in ("REJECTED", "NEEDS_REVISION"):
        expense.status = "DRAFT"

    await session.commit()
    await session.refresh(expense)
    return expense


async def delete_expense(session: AsyncSession, expense_id: str) -> bool:
    """Delete an expense (only allowed in DRAFT, REJECTED, or NEEDS_REVISION status)."""
    expense = await get_expense(session, expense_id)
    if not expense or expense.status not in ("DRAFT", "REJECTED", "NEEDS_REVISION"):
        return False
    await session.delete(expense)
    await session.commit()
    return True


async def update_expense_status(
    session: AsyncSession,
    expense_id: str,
    new_status: str,
) -> Optional[Expense]:
    """Update the status of an expense (internal use for service callbacks)."""
    expense = await get_expense(session, expense_id)
    if not expense:
        return None
    expense.status = new_status
    await session.commit()
    await session.refresh(expense)
    return expense


async def get_expense_metrics(session: AsyncSession) -> dict:
    """Aggregate expense metrics for monitoring dashboard."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Total count
    total_result = await session.execute(select(func.count(Expense.id)))
    total_count = total_result.scalar() or 0

    # Count per status
    status_result = await session.execute(
        select(Expense.status, func.count(Expense.id))
        .group_by(Expense.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # Total and average amount (converted to EUR for accurate aggregation)
    all_expenses_result = await session.execute(select(Expense))
    all_expenses = list(all_expenses_result.scalars().all())
    total_amount_eur = round(sum(convert_to_eur(e.amount, e.currency) for e in all_expenses), 2)
    avg_amount_eur = round(total_amount_eur / len(all_expenses), 2) if all_expenses else 0.0

    # Today's count
    today_result = await session.execute(
        select(func.count(Expense.id))
        .where(Expense.created_at >= today_start)
    )
    today_count = today_result.scalar() or 0

    # This week's count
    week_result = await session.execute(
        select(func.count(Expense.id))
        .where(Expense.created_at >= week_start)
    )
    week_count = week_result.scalar() or 0

    # Top categories (with EUR-converted totals)
    cat_expenses: dict[str, dict] = {}
    for e in all_expenses:
        cat = e.category or "Sonstige"
        if cat not in cat_expenses:
            cat_expenses[cat] = {"count": 0, "total_amount": 0.0}
        cat_expenses[cat]["count"] += 1
        cat_expenses[cat]["total_amount"] += convert_to_eur(e.amount, e.currency)
    top_categories = [
        {"category": k, "count": v["count"], "total_amount": round(v["total_amount"], 2)}
        for k, v in sorted(cat_expenses.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    ]

    # Unique users
    users_result = await session.execute(
        select(func.count(distinct(Expense.created_by)))
    )
    unique_users = users_result.scalar() or 0

    # Recent expenses (last 10)
    recent_result = await session.execute(
        select(Expense)
        .order_by(Expense.created_at.desc())
        .limit(10)
    )
    recent_expenses = [
        {
            "id": e.id,
            "title": e.title,
            "amount": e.amount,
            "currency": e.currency,
            "status": e.status,
            "created_by": e.created_by,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in recent_result.scalars().all()
    ]

    return {
        "total_count": total_count,
        "status_counts": status_counts,
        "total_amount": total_amount_eur,
        "average_amount": avg_amount_eur,
        "today_count": today_count,
        "week_count": week_count,
        "top_categories": top_categories,
        "unique_users": unique_users,
        "recent_expenses": recent_expenses,
    }

