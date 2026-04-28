"""
Approval Service — Database Setup.
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./approval.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables."""
    from models import ApprovalRecord  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency: Yield an async database session."""
    async with async_session() as session:
        yield session


async def seed_data():
    """Seed the database with persistent sample approval records."""
    from models import ApprovalRecord
    from datetime import datetime, timezone

    sample_records = [
        ApprovalRecord(
            id="a2222222-2222-2222-2222-222222222222",
            expense_id="e2222222-2222-2222-2222-222222222222",
            title="Hotelübernachtung Hamburg",
            original_amount=180.0,
            currency="EUR",
            decision=None,
            submitted_by="jane.smith@company.com",
            decided_by="auto-approver"
        ),
        ApprovalRecord(
            id="a3333333-3333-3333-3333-333333333333",
            expense_id="e3333333-3333-3333-3333-333333333333",
            title="Team-Essen",
            original_amount=150.0,
            currency="EUR",
            decision="APPROVED",
            reason="Genehmigt für Teambuilding",
            decided_by="manager@company.com",
            submitted_by="john.doe@company.com",
            decided_at=datetime.now(timezone.utc)
        ),
        ApprovalRecord(
            id="a4444444-4444-4444-4444-444444444444",
            expense_id="e4444444-4444-4444-4444-444444444444",
            title="Privates Taxi",
            original_amount=45.0,
            currency="EUR",
            decision="REJECTED",
            reason="Private Ausgaben werden nicht erstattet.",
            decided_by="manager@company.com",
            submitted_by="jane.smith@company.com",
            decided_at=datetime.now(timezone.utc)
        ),
        ApprovalRecord(
            id="a5555555-5555-5555-5555-555555555555",
            expense_id="e5555555-5555-5555-5555-555555555555",
            title="Mietwagen München",
            original_amount=320.0,
            currency="EUR",
            decision="APPROVED",
            reason="Notwendig für Kundenbesuch",
            decided_by="manager@company.com",
            submitted_by="bob.jones@company.com",
            decided_at=datetime.now(timezone.utc)
        ),
        ApprovalRecord(
            id="a6666666-6666-6666-6666-666666666666",
            expense_id="e6666666-6666-6666-6666-666666666666",
            title="Konferenz-Ticket AWS",
            original_amount=1200.0,
            currency="EUR",
            decision="APPROVED",
            reason="Weiterbildung genehmigt",
            decided_by="manager@company.com",
            submitted_by="alice.wonder@company.com",
            decided_at=datetime.now(timezone.utc)
        ),
        ApprovalRecord(
            id="a7777777-7777-7777-7777-777777777777",
            expense_id="e7777777-7777-7777-7777-777777777777",
            title="Büromaterial",
            original_amount=85.0,
            currency="EUR",
            decision="APPROVED",
            reason="Standard Bürobedarf",
            decided_by="manager@company.com",
            submitted_by="john.doe@company.com",
            decided_at=datetime.now(timezone.utc)
        ),
        ApprovalRecord(
            id="a8888888-8888-8888-8888-888888888888",
            expense_id="e8888888-8888-8888-8888-888888888888",
            title="Zugticket Köln",
            original_amount=110.0,
            currency="EUR",
            decision="NEEDS_REVISION",
            reason="Bitte Beleg nachreichen.",
            decided_by="manager@company.com",
            submitted_by="jane.smith@company.com",
            decided_at=datetime.now(timezone.utc)
        ),
        ApprovalRecord(
            id="a9999999-9999-9999-9999-999999999999",
            expense_id="e9999999-9999-9999-9999-999999999999",
            title="Kunden-Lunch",
            original_amount=95.0,
            currency="EUR",
            decision="APPROVED",
            reason="Kundenpflege",
            decided_by="manager@company.com",
            submitted_by="bob.jones@company.com",
            decided_at=datetime.now(timezone.utc)
        )
    ]

    async with async_session() as session:
        for rec in sample_records:
            result = await session.get(ApprovalRecord, rec.id)
            if not result:
                session.add(rec)
        await session.commit()

