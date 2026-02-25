"""Tests for Wave 7: Batch trigger API endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_log import BatchLog


@pytest.mark.anyio
class TestTriggerCascade:
    """POST /api/v1/batch/trigger."""

    async def test_trigger_success(self, client: AsyncClient, db: AsyncSession):
        """Trigger succeeds with no reading_queued cases (empty batch = success)."""
        resp = await client.post("/api/v1/batch/trigger")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "success"
        assert data["total_fetched"] == 0
        assert "batch_log_id" in data

    async def test_already_running_returns_409(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """If a cascade batch is already running → 409."""
        # Insert a running batch_log to simulate lock
        running_log = BatchLog(
            source="system",
            batch_type="cascade_pipeline",
            feature_origin="F-002",
            status="running",
        )
        db.add(running_log)
        await db.flush()

        resp = await client.post("/api/v1/batch/trigger")
        assert resp.status_code == 409
        error = resp.json()["error"]
        assert error["code"] == "BATCH_ALREADY_RUNNING"
