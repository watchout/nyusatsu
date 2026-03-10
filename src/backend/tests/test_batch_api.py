"""Tests for Batch API — TASK-36.

Tests GET /api/v1/batch/latest, /logs, /logs/:id, POST /trigger.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_log import BatchLog

_NOW = datetime.now(UTC)


async def _create_batch_log(
    db: AsyncSession,
    *,
    status: str = "success",
    source: str = "chotatku_portal",
    batch_type: str = "case_fetch",
) -> BatchLog:
    log = BatchLog(
        id=uuid.uuid4(),
        source=source,
        feature_origin="F-001",
        batch_type=batch_type,
        started_at=_NOW,
        status=status,
        total_fetched=10,
        new_count=3,
        updated_count=2,
        unchanged_count=5,
        error_count=0,
    )
    db.add(log)
    await db.flush()
    return log


@pytest.mark.anyio
class TestGetLatestBatch:
    """GET /api/v1/batch/latest."""

    async def test_latest_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/batch/latest")
        assert resp.status_code == 200
        assert resp.json()["data"] is None

    async def test_latest_returns_most_recent(self, client: AsyncClient, db: AsyncSession) -> None:
        await _create_batch_log(db)
        resp = await client.get("/api/v1/batch/latest")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data is not None
        assert data["status"] == "success"


@pytest.mark.anyio
class TestListBatchLogs:
    """GET /api/v1/batch/logs."""

    async def test_list_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/batch/logs")
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 0

    async def test_list_returns_logs(self, client: AsyncClient, db: AsyncSession) -> None:
        await _create_batch_log(db)
        await _create_batch_log(db, batch_type="od_import")
        resp = await client.get("/api/v1/batch/logs")
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 2


@pytest.mark.anyio
class TestGetBatchLog:
    """GET /api/v1/batch/logs/:id."""

    async def test_get_by_id(self, client: AsyncClient, db: AsyncSession) -> None:
        log = await _create_batch_log(db)
        resp = await client.get(f"/api/v1/batch/logs/{log.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == str(log.id)

    async def test_not_found(self, client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/batch/logs/{fake_id}")
        assert resp.status_code == 404
