"""
Request Service — Database Setup.
Async SQLAlchemy engine and session factory for SQLite.
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./request.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables."""
    from models import Expense  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency: Yield an async database session."""
    async with async_session() as session:
        yield session


async def seed_data():
    """Seed the database with 10 persistent sample expenses."""
    from models import Expense
    from datetime import datetime, timezone

    sample_expenses = [
        Expense(
            id="e1111111-1111-1111-1111-111111111111",
            title="Flug nach Berlin",
            description="Projekt-Kickoff bei Kunde X",
            amount=250.0,
            currency="EUR",
            status="DRAFT",
            category="travel",
            created_by="john.doe@company.com"
        ),
        Expense(
            id="e2222222-2222-2222-2222-222222222222",
            title="Hotelübernachtung Hamburg",
            description="2 Nächte inkl. Frühstück",
            amount=180.0,
            currency="EUR",
            status="SUBMITTED",
            category="hotel",
            created_by="jane.smith@company.com"
        ),
        Expense(
            id="e3333333-3333-3333-3333-333333333333",
            title="Team-Essen",
            description="Abendessen mit dem Entwicklungsteam",
            amount=150.0,
            currency="EUR",
            status="PAID",
            category="food",
            created_by="john.doe@company.com"
        ),
        Expense(
            id="e4444444-4444-4444-4444-444444444444",
            title="Privates Taxi",
            description="Fahrt zum Flughafen (privat)",
            amount=45.0,
            currency="EUR",
            status="REJECTED",
            category="travel",
            created_by="jane.smith@company.com"
        ),
        Expense(
            id="e5555555-5555-5555-5555-555555555555",
            title="Mietwagen München",
            description="Kundenbesuch Vertrieb",
            amount=320.0,
            currency="EUR",
            status="BUDGET_CONFIRMED",
            category="travel",
            created_by="bob.jones@company.com"
        ),
        Expense(
            id="e6666666-6666-6666-6666-666666666666",
            title="Konferenz-Ticket AWS",
            description="Weiterbildung Cloud Architektur",
            amount=1200.0,
            currency="EUR",
            status="BUDGET_DENIED",
            category="other",
            created_by="alice.wonder@company.com"
        ),
        Expense(
            id="e7777777-7777-7777-7777-777777777777",
            title="Büromaterial",
            description="Whiteboard-Marker und Post-its",
            amount=85.0,
            currency="EUR",
            status="PAYOUT_FAILED",
            category="other",
            created_by="john.doe@company.com"
        ),
        Expense(
            id="e8888888-8888-8888-8888-888888888888",
            title="Zugticket Köln",
            description="Meeting mit Partner Y",
            amount=110.0,
            currency="EUR",
            status="NEEDS_REVISION",
            category="travel",
            created_by="jane.smith@company.com"
        ),
        Expense(
            id="e9999999-9999-9999-9999-999999999999",
            title="Kunden-Lunch",
            description="Besprechung Projekt-Erweiterung",
            amount=95.0,
            currency="EUR",
            status="PAID",
            category="food",
            created_by="bob.jones@company.com"
        ),
        Expense(
            id="e0000000-0000-0000-0000-000000000000",
            title="Tanken Dienstwagen",
            description="Rückfahrt von Messe",
            amount=65.0,
            currency="EUR",
            status="DRAFT",
            category="travel",
            created_by="alice.wonder@company.com"
        )
    ]

    async with async_session() as session:
        for exp in sample_expenses:
            result = await session.get(Expense, exp.id)
            if not result:
                session.add(exp)
        await session.commit()

