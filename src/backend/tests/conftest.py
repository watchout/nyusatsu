"""Shared pytest fixtures for backend tests.

Prerequisites: `alembic upgrade head` must be run before test suite.
Each test gets a DB session wrapped in a SAVEPOINT that is rolled back
after the test, keeping the DB schema intact but data isolated.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
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


@pytest.fixture
async def db(engine):
    """Per-test async session with SAVEPOINT rollback.

    Wraps each test in a transaction + savepoint so that any data
    written during the test is automatically rolled back.
    """
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
