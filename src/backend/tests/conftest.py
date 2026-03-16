"""Shared pytest fixtures for backend tests.

Prerequisites: `alembic upgrade head` must be run before test suite.
Each test gets a DB session wrapped in a SAVEPOINT that is rolled back
after the test, keeping the DB schema intact but data isolated.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.main import create_app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def engine():
    """Session-scoped async engine (NullPool for test isolation)."""
    return create_async_engine(settings.DATABASE_URL, poolclass=NullPool)


async def _delete_all_tables(conn) -> None:
    """Delete all test data (preserving schema and reseeding company_profiles)."""
    tables_to_clear = [
        'checklists',
        'case_cards',
        'case_events',
        'eligibility_results',
        'bid_details',
        'base_bids',
        'batch_logs',
        'cases',
        'company_profiles',  # Clear to reinsert seed data
    ]
    for table in tables_to_clear:
        try:
            await conn.execute(text(f'DELETE FROM {table} CASCADE'))
        except Exception:
            pass  # Table might not exist, that's ok
    
    # Re-insert seed data (SSOT-4 §7-3)
    try:
        await conn.execute(text("""
            INSERT INTO company_profiles (
                unified_qualification, grade, business_categories, regions,
                licenses, certifications, experience, subcontractors
            ) VALUES (
                true,
                'D',
                '["物品の販売", "役務の提供その他"]'::JSONB,
                '["関東・甲信越"]'::JSONB,
                '[]'::JSONB,
                '[]'::JSONB,
                '[]'::JSONB,
                '[
                    {"name": "クローバー運輸", "license": "運送業", "capabilities": ["軽運送", "配送"]},
                    {"name": "電気工事会社", "license": "電気工事業", "capabilities": ["電気工事"]},
                    {"name": "内装関係", "license": "内装業", "capabilities": ["内装工事"]}
                ]'::JSONB
            )
        """))
    except Exception:
        pass  # Seed insert may fail if table doesn't exist yet


@pytest.fixture
async def db(engine):
    """Per-test async session with SAVEPOINT rollback.

    Wraps each test in a transaction + savepoint so that any data
    written during the test is automatically rolled back.
    Also clears test data at the start.
    """
    # Clear all test data before this test
    async with engine.begin() as conn:
        await _delete_all_tables(conn)
    
    async with engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Nested savepoint — the test operates inside this
        nested = await conn.begin_nested()

        yield session

        # Rollback savepoint (test data)
        if nested.is_active:
            await nested.rollback()
        # Rollback outer transaction
        if txn.is_active:
            await txn.rollback()
        await session.close()


@pytest.fixture
async def client(db):
    """Async HTTP client with DB session override."""
    app = create_app()

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
