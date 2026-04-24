"""
Request Service — CRUD Operations.
Database operations for creating, reading, updating, and deleting expenses.
"""

from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import Expense
from schemas import ExpenseCreate, ExpenseUpdate


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
