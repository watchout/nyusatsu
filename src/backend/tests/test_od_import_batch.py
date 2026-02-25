"""Tests for TASK-16: OD import batch runner integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.models.batch_log import BatchLog
from app.services.batch.od_import_batch import ODImportBatch
from app.services.batch.runner import BatchRunner

FIXTURES = Path(__file__).parent / "fixtures" / "od"


@pytest.mark.anyio
class TestODImportBatch:
    """Test OD import end-to-end via BatchRunner."""

    async def test_full_import(self, db: AsyncSession):
        """Full CSV → 5 rows in base_bids, batch_log success."""
        csv_text = (FIXTURES / "sample_full.csv").read_text(encoding="utf-8-sig")
        batch = ODImportBatch(csv_text=csv_text, sha256="abc123")
        runner = BatchRunner()

        batch_log, result = await runner.run(db, batch)

        assert batch_log.status == "success"
        assert batch_log.batch_type == "od_import"
        assert batch_log.feature_origin == "F-005"
        assert result.total_fetched == 5
        assert result.new_count == 5
        assert result.error_count == 0

        # Verify DB
        bids = (await db.execute(select(BaseBid))).scalars().all()
        assert len(bids) == 5

    async def test_partial_failure_with_invalid(self, db: AsyncSession):
        """CSV with invalid rows → partial success."""
        csv_text = (FIXTURES / "sample_invalid.csv").read_text(encoding="utf-8-sig")
        batch = ODImportBatch(csv_text=csv_text, sha256="def456")
        runner = BatchRunner()

        batch_log, result = await runner.run(db, batch)

        # 1 good + 3 errors (empty row skipped by parser)
        assert batch_log.status == "partial"
        assert result.new_count == 1
        assert result.error_count == 3

    async def test_batch_log_persisted(self, db: AsyncSession):
        """batch_log is queryable after import."""
        csv_text = (FIXTURES / "sample_full.csv").read_text(encoding="utf-8-sig")
        batch = ODImportBatch(csv_text=csv_text, sha256="ghi789")
        runner = BatchRunner()

        batch_log, _ = await runner.run(db, batch)

        found = (
            await db.execute(
                select(BatchLog).where(BatchLog.id == batch_log.id),
            )
        ).scalar_one()
        assert found.source == "open_data"
        assert found.total_fetched == 5
        assert found.status == "success"
