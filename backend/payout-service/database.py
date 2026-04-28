"""
Payout Service — Database Setup.
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./payout.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables."""
    from models import PayoutRecord  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency: Yield an async database session."""
    async with async_session() as session:
        yield session


async def seed_data():
    """Seed the database with persistent sample payouts."""
    from models import PayoutRecord
    from datetime import datetime, timezone

    sample_payouts = [
        PayoutRecord(
            id="p3333333-3333-3333-3333-333333333333",
            expense_id="e3333333-3333-3333-3333-333333333333",
            title="Team-Essen",
            amount=150.0,
            currency="EUR",
            status="PAID",
            paid_at=datetime.now(timezone.utc)
        ),
        PayoutRecord(
            id="p7777777-7777-7777-7777-777777777777",
            expense_id="e7777777-7777-7777-7777-777777777777",
            title="Büromaterial",
            amount=85.0,
            currency="EUR",
            status="PAYOUT_FAILED",
            failure_reason="Bankverbindung ungültig",
            paid_at=None
        ),
        PayoutRecord(
            id="p9999999-9999-9999-9999-999999999999",
            expense_id="e9999999-9999-9999-9999-999999999999",
            title="Kunden-Lunch",
            amount=95.0,
            currency="EUR",
            status="PAID",
            paid_at=datetime.now(timezone.utc)
        )
    ]

    async with async_session() as session:
        for pay in sample_payouts:
            result = await session.get(PayoutRecord, pay.id)
            if not result:
                session.add(pay)
        await session.commit()

