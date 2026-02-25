"""Tests for TASK-14: Batch type definitions."""

from __future__ import annotations

from app.services.batch.types import (
    BatchConfig,
    BatchResult,
    BatchStatus,
    ItemStatus,
)


class TestBatchConfig:
    """BatchConfig immutability and fields."""

    def test_frozen(self):
        cfg = BatchConfig(source="njss", batch_type="case_fetch", feature_origin="F-001")
        assert cfg.source == "njss"
        assert cfg.batch_type == "case_fetch"
        assert cfg.feature_origin == "F-001"


class TestBatchResult:
    """Batch result status auto-determination per §2-5."""

    def test_empty_batch_is_success(self):
        """0-item batch → success per §2-5."""
        result = BatchResult()
        assert result.status == BatchStatus.SUCCESS
        assert result.total_fetched == 0

    def test_all_success(self):
        """All items succeeded → success."""
        result = BatchResult()
        result.record_success("item-1")
        result.record_success("item-2", is_new=False)
        assert result.status == BatchStatus.SUCCESS
        assert result.new_count == 1
        assert result.updated_count == 1
        assert result.error_count == 0
        assert result.success_count == 2

    def test_partial_failure(self):
        """Some success + some failure → partial."""
        result = BatchResult()
        result.record_success("item-1")
        result.record_failure("item-2", "timeout")
        assert result.status == BatchStatus.PARTIAL
        assert result.success_count == 1
        assert result.error_count == 1

    def test_all_failed(self):
        """All items failed → failed."""
        result = BatchResult()
        result.record_failure("item-1", "error A")
        result.record_failure("item-2", "error B")
        assert result.status == BatchStatus.FAILED
        assert result.error_count == 2
        assert result.success_count == 0

    def test_skipped_items(self):
        """Skipped items counted as unchanged."""
        result = BatchResult()
        result.record_success("item-1")
        result.record_skipped("item-2")
        assert result.unchanged_count == 1
        assert result.total_fetched == 2
        assert result.status == BatchStatus.SUCCESS

    def test_items_list_populated(self):
        """Items list records all results."""
        result = BatchResult()
        result.record_success("a")
        result.record_failure("b", "err")
        result.record_skipped("c")
        assert len(result.items) == 3
        assert result.items[0].status == ItemStatus.SUCCESS
        assert result.items[1].status == ItemStatus.FAILED
        assert result.items[1].error_message == "err"
        assert result.items[2].status == ItemStatus.SKIPPED

    def test_failure_with_details(self):
        """Failure records error_details."""
        result = BatchResult()
        result.record_failure("x", "crash", {"code": 500})
        assert result.items[0].error_details == {"code": 500}
