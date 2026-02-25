"""Tests for TASK-14: BatchRunner orchestrator."""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from app.core.errors import BatchAlreadyRunningError
from app.models.batch_log import BatchLog
from app.services.batch.base import BaseBatchRunner
from app.services.batch.runner import BatchRunner
from app.services.batch.types import (
    BatchConfig,
    BatchItemResult,
    BatchStatus,
    ItemStatus,
)


# ---------------------------------------------------------------------------
# Mock batch runner for testing
# ---------------------------------------------------------------------------


class MockBatchRunner(BaseBatchRunner):
    """Configurable mock for testing BatchRunner."""

    def __init__(
        self,
        items: list[Any] | None = None,
        *,
        fail_items: set[str] | None = None,
        skip_items: set[str] | None = None,
        raise_on_item: str | None = None,
        source: str = "test",
        batch_type: str = "test_batch",
    ) -> None:
        self._items = items or []
        self._fail_items = fail_items or set()
        self._skip_items = skip_items or set()
        self._raise_on_item = raise_on_item
        self._source = source
        self._batch_type = batch_type
        self.started = False
        self.ended = False

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source=self._source,
            batch_type=self._batch_type,
            feature_origin="F-TEST",
        )

    async def fetch_items(self, db: Any) -> AsyncIterator[str]:
        for item in self._items:
            yield item

    async def process_item(self, db: Any, item: str) -> BatchItemResult:
        if item == self._raise_on_item:
            raise RuntimeError(f"Unexpected error on {item}")

        if item in self._fail_items:
            return BatchItemResult(
                item_id=item,
                status=ItemStatus.FAILED,
                error_message=f"Failed: {item}",
            )

        if item in self._skip_items:
            return BatchItemResult(
                item_id=item,
                status=ItemStatus.SKIPPED,
            )

        return BatchItemResult(item_id=item, status=ItemStatus.SUCCESS)

    async def on_batch_start(self) -> None:
        self.started = True

    async def on_batch_end(self) -> None:
        self.ended = True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestBatchRunner:
    """Test BatchRunner orchestration."""

    async def test_success_batch(self, db):
        """All items succeed → status=success, counts correct."""
        runner = BatchRunner()
        mock = MockBatchRunner(items=["a", "b", "c"])

        batch_log, result = await runner.run(db, mock)

        assert batch_log.status == "success"
        assert batch_log.total_fetched == 3
        assert batch_log.new_count == 3
        assert batch_log.error_count == 0
        assert batch_log.finished_at is not None
        assert result.status == BatchStatus.SUCCESS
        assert mock.started is True
        assert mock.ended is True

    async def test_empty_batch(self, db):
        """0-item batch → success per §2-5."""
        runner = BatchRunner()
        mock = MockBatchRunner(items=[])

        batch_log, result = await runner.run(db, mock)

        assert batch_log.status == "success"
        assert batch_log.total_fetched == 0
        assert result.status == BatchStatus.SUCCESS

    async def test_partial_failure(self, db):
        """Some items fail → status=partial."""
        runner = BatchRunner()
        mock = MockBatchRunner(
            items=["ok1", "fail1", "ok2"],
            fail_items={"fail1"},
        )

        batch_log, result = await runner.run(db, mock)

        assert batch_log.status == "partial"
        assert batch_log.total_fetched == 3
        assert batch_log.new_count == 2
        assert batch_log.error_count == 1
        assert result.status == BatchStatus.PARTIAL
        assert batch_log.error_details is not None
        assert len(batch_log.error_details) == 1
        assert batch_log.error_details[0]["item_id"] == "fail1"

    async def test_all_failed(self, db):
        """All items fail → status=failed."""
        runner = BatchRunner()
        mock = MockBatchRunner(
            items=["a", "b"],
            fail_items={"a", "b"},
        )

        batch_log, result = await runner.run(db, mock)

        assert batch_log.status == "failed"
        assert batch_log.error_count == 2
        assert result.status == BatchStatus.FAILED

    async def test_exception_in_process_item(self, db):
        """Unhandled exception in process_item → recorded as failure, batch continues."""
        runner = BatchRunner()
        mock = MockBatchRunner(
            items=["ok1", "crash", "ok2"],
            raise_on_item="crash",
        )

        batch_log, result = await runner.run(db, mock)

        assert batch_log.status == "partial"
        assert batch_log.new_count == 2
        assert batch_log.error_count == 1
        # Error details contain exception type
        error_item = [
            e for e in batch_log.error_details if e["item_id"] == "crash"
        ]
        assert len(error_item) == 1
        assert error_item[0]["exception_type"] == "RuntimeError"

    async def test_skipped_items(self, db):
        """Skipped items → unchanged_count incremented."""
        runner = BatchRunner()
        mock = MockBatchRunner(
            items=["new1", "skip1"],
            skip_items={"skip1"},
        )

        batch_log, result = await runner.run(db, mock)

        assert batch_log.status == "success"
        assert batch_log.unchanged_count == 1
        assert batch_log.new_count == 1

    async def test_exclusive_lock_prevents_concurrent(self, db):
        """Same batch_type+source running → BatchAlreadyRunningError."""
        # Create a running batch_log
        existing = BatchLog(
            source="test",
            batch_type="test_batch",
            feature_origin="F-TEST",
            status="running",
        )
        db.add(existing)
        await db.flush()

        runner = BatchRunner()
        mock = MockBatchRunner(items=["a"])

        with pytest.raises(BatchAlreadyRunningError) as exc_info:
            await runner.run(db, mock)

        assert "already running" in exc_info.value.message
        assert exc_info.value.details["batch_type"] == "test_batch"

    async def test_different_batch_type_not_blocked(self, db):
        """Different batch_type can run concurrently."""
        existing = BatchLog(
            source="test",
            batch_type="other_batch",
            feature_origin="F-OTHER",
            status="running",
        )
        db.add(existing)
        await db.flush()

        runner = BatchRunner()
        mock = MockBatchRunner(items=["a"], batch_type="test_batch")

        batch_log, result = await runner.run(db, mock)
        assert batch_log.status == "success"

    async def test_batch_log_persisted(self, db):
        """BatchLog is committed to DB and queryable."""
        runner = BatchRunner()
        mock = MockBatchRunner(items=["a"])

        batch_log, _ = await runner.run(db, mock)

        # Query back from DB
        from sqlalchemy import select
        stmt = select(BatchLog).where(BatchLog.id == batch_log.id)
        found = (await db.execute(stmt)).scalar_one()

        assert found.source == "test"
        assert found.batch_type == "test_batch"
        assert found.status == "success"
        assert found.total_fetched == 1

    async def test_hooks_called_on_empty_batch(self, db):
        """on_batch_start/end called even for empty batches."""
        runner = BatchRunner()
        mock = MockBatchRunner(items=[])

        await runner.run(db, mock)

        assert mock.started is True
        assert mock.ended is True
