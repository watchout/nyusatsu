"""Tests for TASK-20: Case fetch batch integration."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_log import BatchLog
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.services.batch.case_fetch_batch import CaseFetchBatch
from app.services.batch.runner import BatchRunner
from app.services.case_fetch.base_adapter import BaseSourceAdapter, RawCase


class _MockAdapter(BaseSourceAdapter):
    """Mock adapter returning pre-configured RawCases."""

    def __init__(self, cases: list[RawCase]) -> None:
        self._cases = cases

    @property
    def source_name(self) -> str:
        return "mock_portal"

    async def fetch(self) -> list[RawCase]:
        return self._cases


def _make_raw_case(source_id: str = "FETCH-001", **overrides) -> RawCase:
    """Create a test RawCase."""
    defaults = {
        "source": "mock_portal",
        "source_id": source_id,
        "case_name": "テスト案件",
        "issuing_org": "テスト省",
        "bid_type": "一般競争入札",
        "region": "東京都",
        "deadline": date(2025, 5, 1),
    }
    defaults.update(overrides)
    return RawCase(**defaults)


@pytest.mark.anyio
class TestCaseFetchBatch:
    """Test case fetch batch pipeline."""

    async def test_normal_fetch_pipeline(self, db: AsyncSession):
        """Normal fetch → normalise → store → score → event."""
        raw_cases = [
            _make_raw_case("FETCH-001"),
            _make_raw_case("FETCH-002", case_name="別の案件"),
        ]
        adapter = _MockAdapter(raw_cases)
        batch = CaseFetchBatch(adapter=adapter)
        runner = BatchRunner()

        batch_log, result = await runner.run(db, batch)

        assert batch_log.status == "success"
        assert result.total_fetched == 2
        assert result.new_count == 2

        # Cases stored in DB
        cases = (await db.execute(select(Case))).scalars().all()
        stored = [c for c in cases if c.source == "mock_portal"]
        assert len(stored) == 2

        # Score populated
        for c in stored:
            assert c.score is not None
            assert c.score_detail is not None

    async def test_case_events_created(self, db: AsyncSession):
        """discovered → scored transition creates case_events."""
        adapter = _MockAdapter([_make_raw_case("EVT-001")])
        batch = CaseFetchBatch(adapter=adapter)
        runner = BatchRunner()

        await runner.run(db, batch)

        # Find the case
        case = (
            await db.execute(
                select(Case).where(Case.source_id == "EVT-001"),
            )
        ).scalar_one()

        # Check event was created
        events = (
            await db.execute(
                select(CaseEvent).where(CaseEvent.case_id == case.id),
            )
        ).scalars().all()

        assert len(events) == 1
        assert events[0].event_type == "case_scored"
        assert events[0].to_status == "scored"

    async def test_batch_log_persisted(self, db: AsyncSession):
        """batch_log is queryable after fetch."""
        adapter = _MockAdapter([_make_raw_case("LOG-001")])
        batch = CaseFetchBatch(adapter=adapter)
        runner = BatchRunner()

        batch_log, _ = await runner.run(db, batch)

        found = (
            await db.execute(
                select(BatchLog).where(BatchLog.id == batch_log.id),
            )
        ).scalar_one()

        assert found.source == "mock_portal"
        assert found.batch_type == "case_fetch"
        assert found.feature_origin == "F-001"
        assert found.status == "success"

    async def test_skip_unchanged_case(self, db: AsyncSession):
        """Second fetch of same case → SKIP (unchanged)."""
        adapter = _MockAdapter([_make_raw_case("DUP-001")])
        batch = CaseFetchBatch(adapter=adapter)
        runner = BatchRunner()

        # First run
        _, result1 = await runner.run(db, batch)
        assert result1.new_count == 1

        # Second run — same data
        batch2 = CaseFetchBatch(adapter=adapter)
        _, result2 = await runner.run(db, batch2)
        assert result2.unchanged_count == 1
        assert result2.new_count == 0

    async def test_normalisation_error(self, db: AsyncSession):
        """Invalid raw case (empty name) → FAILED item."""
        raw = _make_raw_case("BAD-001", case_name="")
        adapter = _MockAdapter([raw])
        batch = CaseFetchBatch(adapter=adapter)
        runner = BatchRunner()

        batch_log, result = await runner.run(db, batch)

        assert result.error_count == 1
        assert batch_log.status == "failed"
