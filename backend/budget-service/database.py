"""
Budget Service — Database Setup.
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./budget.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables."""
    from models import BudgetCheck  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency: Yield an async database session."""
    async with async_session() as session:
        yield session


async def seed_data():
    """Seed the database with persistent sample budget checks."""
    from models import BudgetCheck
    from datetime import datetime, timezone

    sample_checks = [
        BudgetCheck(
            id="b3333333-3333-3333-3333-333333333333",
            expense_id="e3333333-3333-3333-3333-333333333333",
            title="Team-Essen",
            amount=150.0,
            amount_eur=150.0,
            currency="EUR",
            budget_available=10000.0,
            result="BUDGET_CONFIRMED",
            checked_at=datetime.now(timezone.utc)
        ),
        BudgetCheck(
            id="b5555555-5555-5555-5555-555555555555",
            expense_id="e5555555-5555-5555-5555-555555555555",
            title="Mietwagen München",
            amount=320.0,
            amount_eur=320.0,
            currency="EUR",
            budget_available=9850.0,
            result="BUDGET_CONFIRMED",
            checked_at=datetime.now(timezone.utc)
        ),
        BudgetCheck(
            id="b6666666-6666-6666-6666-666666666666",
            expense_id="e6666666-6666-6666-6666-666666666666",
            title="Konferenz-Ticket AWS",
            amount=1200.0,
            amount_eur=1200.0,
            currency="EUR",
            budget_available=9530.0,
            result="BUDGET_DENIED",
            checked_at=datetime.now(timezone.utc)
        ),
        BudgetCheck(
            id="b7777777-7777-7777-7777-777777777777",
            expense_id="e7777777-7777-7777-7777-777777777777",
            title="Büromaterial",
            amount=85.0,
            amount_eur=85.0,
            currency="EUR",
            budget_available=9530.0,
            result="BUDGET_CONFIRMED",
            checked_at=datetime.now(timezone.utc)
        ),
        BudgetCheck(
            id="b9999999-9999-9999-9999-999999999999",
            expense_id="e9999999-9999-9999-9999-999999999999",
            title="Kunden-Lunch",
            amount=95.0,
            amount_eur=95.0,
            currency="EUR",
            budget_available=9445.0,
            result="BUDGET_CONFIRMED",
            checked_at=datetime.now(timezone.utc)
        )
    ]

    async with async_session() as session:
        for chk in sample_checks:
            result = await session.get(BudgetCheck, chk.id)
            if not result:
                session.add(chk)
        await session.commit()

