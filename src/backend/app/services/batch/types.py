"""Batch type definitions — SSOT-5 §2.

BatchConfig: Describes a batch job's identity and constraints.
BatchItemResult: Outcome of processing a single item.
BatchResult: Aggregate outcome of the entire batch run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ItemStatus(StrEnum):
    """Outcome of a single batch item."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class BatchStatus(StrEnum):
    """Aggregate batch outcome per §2-5.

    - success: all items succeeded (or 0 items)
    - partial: some succeeded, some failed
    - failed: all items failed
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True)
class BatchConfig:
    """Configuration for a batch job.

    Attributes:
        source: Data source identifier (e.g. "njss", "open_data").
        batch_type: Batch type (e.g. "case_fetch", "od_import").
        feature_origin: Feature reference (e.g. "F-001", "F-005").
    """

    source: str
    batch_type: str
    feature_origin: str


@dataclass
class BatchItemResult:
    """Outcome of processing a single item.

    Attributes:
        item_id: Identifier for the processed item.
        status: success / failed / skipped.
        error_message: Human-readable error description (if failed).
        error_details: Structured error data for batch_logs.error_details.
    """

    item_id: str
    status: ItemStatus
    error_message: str | None = None
    error_details: dict[str, Any] | None = None


@dataclass
class BatchResult:
    """Aggregate result of a batch run per §2-5.

    The ``status`` property auto-computes based on item counts.
    """

    total_fetched: int = 0
    new_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    error_count: int = 0
    items: list[BatchItemResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        """Items that completed successfully (new + updated)."""
        return self.new_count + self.updated_count

    @property
    def status(self) -> BatchStatus:
        """Auto-determine batch status per §2-5.

        | Condition              | Status  |
        |------------------------|---------|
        | All success (or 0)     | success |
        | Some success + errors  | partial |
        | All failed             | failed  |
        """
        if self.total_fetched == 0:
            return BatchStatus.SUCCESS
        if self.error_count == 0:
            return BatchStatus.SUCCESS
        if self.error_count >= self.total_fetched:
            return BatchStatus.FAILED
        return BatchStatus.PARTIAL

    def record_success(
        self, item_id: str, *, is_new: bool = True,
    ) -> None:
        """Record a successful item processing."""
        self.total_fetched += 1
        if is_new:
            self.new_count += 1
        else:
            self.updated_count += 1
        self.items.append(
            BatchItemResult(item_id=item_id, status=ItemStatus.SUCCESS),
        )

    def record_failure(
        self,
        item_id: str,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ) -> None:
        """Record a failed item processing."""
        self.total_fetched += 1
        self.error_count += 1
        self.items.append(
            BatchItemResult(
                item_id=item_id,
                status=ItemStatus.FAILED,
                error_message=error_message,
                error_details=error_details,
            ),
        )

    def record_skipped(self, item_id: str) -> None:
        """Record a skipped (unchanged) item."""
        self.total_fetched += 1
        self.unchanged_count += 1
        self.items.append(
            BatchItemResult(item_id=item_id, status=ItemStatus.SKIPPED),
        )
