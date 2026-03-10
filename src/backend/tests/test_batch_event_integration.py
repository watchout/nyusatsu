"""Tests for Wave 0 Item 0-1: batch runner → case_events integration.

Verifies that BatchRunner's process_item() can use EventService
to record lifecycle transitions in case_events, while BatchRunner
itself manages batch_logs independently.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_log import BatchLog
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.services.batch.base import BaseBatchRunner
from app.services.batch.runner import BatchRunner
from app.services.batch.types import (
    BatchConfig,
    BatchItemResult,
    ItemStatus,
)
from app.services.event_service import EventService


class _EventEmittingBatchRunner(BaseBatchRunner):
    """Mock batch runner that records lifecycle transitions in process_item."""

    def __init__(self, cases: list[Case]) -> None:
        self._cases = cases

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="test_integration",
            batch_type="event_test",
            feature_origin="F-TEST",
        )

    async def fetch_items(self, db: AsyncSession) -> AsyncIterator[Case]:
        for case in self._cases:
            yield case

    async def process_item(
        self, db: AsyncSession, item: Case,
    ) -> BatchItemResult:
        """Transition discovered → scored using EventService."""
        svc = EventService()
        await svc.record_transition(
            db,
            case=item,
            to_stage="scored",
            triggered_by="batch",
            feature_origin="F-TEST",
        )
        return BatchItemResult(item_id=str(item.id), status=ItemStatus.SUCCESS)


class _FailingBatchRunner(BaseBatchRunner):
    """Mock batch runner whose process_item always raises."""

    def __init__(self, cases: list[Case]) -> None:
        self._cases = cases

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="test_integration",
            batch_type="fail_test",
            feature_origin="F-TEST",
        )

    async def fetch_items(self, db: AsyncSession) -> AsyncIterator[Case]:
        for case in self._cases:
            yield case

    async def process_item(
        self, db: AsyncSession, item: Case,
    ) -> BatchItemResult:
        raise RuntimeError("Simulated failure")


@pytest.mark.anyio
class TestBatchEventIntegration:
    """Verify batch runner + event service work together."""

    async def _create_case(self, db: AsyncSession, suffix: str = "") -> Case:
        """Helper: create a test case in discovered stage."""
        case = Case(
            source="test",
            source_id=f"evt-test-{suffix}",
            case_name=f"Integration Test Case {suffix}",
            issuing_org="Test Org",
            current_lifecycle_stage="discovered",
        )
        db.add(case)
        await db.flush()
        return case

    async def test_process_item_records_event(self, db: AsyncSession):
        """process_item can use EventService to create case_events."""
        case = await self._create_case(db, "success")
        runner = BatchRunner()
        batch_runner = _EventEmittingBatchRunner(cases=[case])

        batch_log, result = await runner.run(db, batch_runner)

        # batch_log is success
        assert batch_log.status == "success"
        assert result.success_count == 1

        # case_event was recorded
        events = (
            await db.execute(
                select(CaseEvent).where(CaseEvent.case_id == case.id),
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].event_type == "case_scored"
        assert events[0].to_status == "scored"

    async def test_failure_does_not_emit_event(self, db: AsyncSession):
        """When process_item raises, no case_event is recorded."""
        case = await self._create_case(db, "failure")
        runner = BatchRunner()
        batch_runner = _FailingBatchRunner(cases=[case])

        batch_log, result = await runner.run(db, batch_runner)

        assert batch_log.status == "failed"
        assert result.error_count == 1

        # No case_event should exist
        events = (
            await db.execute(
                select(CaseEvent).where(CaseEvent.case_id == case.id),
            )
        ).scalars().all()
        assert len(events) == 0

    async def test_batch_log_and_event_coexist(self, db: AsyncSession):
        """Both batch_log and case_events are recorded in same batch run."""
        case1 = await self._create_case(db, "coexist-1")
        case2 = await self._create_case(db, "coexist-2")
        runner = BatchRunner()
        batch_runner = _EventEmittingBatchRunner(cases=[case1, case2])

        batch_log, result = await runner.run(db, batch_runner)

        # batch_log exists with correct counts
        found_log = (
            await db.execute(
                select(BatchLog).where(BatchLog.id == batch_log.id),
            )
        ).scalar_one()
        assert found_log.total_fetched == 2
        assert found_log.status == "success"

        # Both case_events exist
        all_events = (
            await db.execute(
                select(CaseEvent).where(
                    CaseEvent.case_id.in_([case1.id, case2.id]),
                ),
            )
        ).scalars().all()
        assert len(all_events) == 2
