"""Cascade batch runner — full pipeline F-002 → F-003 → F-004.

Processes cases in `reading_queued` stage through the complete cascade.
Integrates with CircuitBreaker: 3 consecutive LLM failures → skip remaining.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CASCADE_FAILURE_THRESHOLD
from app.models.case import Case
from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import BatchConfig, BatchItemResult, ItemStatus
from app.services.cascade.cascade_pipeline import CascadePipeline
from app.services.llm.base import LLMProvider

logger = structlog.get_logger()


class CascadeBatch(BaseBatchRunner):
    """Batch runner for full cascade pipeline."""

    def __init__(self, provider: LLMProvider, **kwargs: Any) -> None:
        self._provider = provider
        self._pipeline = CascadePipeline(provider, **kwargs)
        self._consecutive_failures = 0

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="system",
            batch_type="cascade_pipeline",
            feature_origin="F-002",
        )

    async def fetch_items(self, db: AsyncSession) -> AsyncIterator[Any]:
        """Yield cases in reading_queued stage."""
        stmt = select(Case).where(
            Case.current_lifecycle_stage == "reading_queued",
        )
        result = await db.execute(stmt)
        for case in result.scalars():
            yield case

    async def process_item(self, db: AsyncSession, item: Any) -> BatchItemResult:
        """Process a single case through the full cascade."""
        case: Case = item

        # Circuit breaker check
        if self._consecutive_failures >= CASCADE_FAILURE_THRESHOLD:
            logger.warning(
                "cascade_circuit_breaker_open",
                case_id=str(case.id),
                consecutive_failures=self._consecutive_failures,
            )
            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.SKIPPED,
                error_message="Circuit breaker open: too many consecutive failures",
            )

        try:
            cascade_result = await self._pipeline.process_case(db, case)

            if cascade_result.aborted_at:
                self._consecutive_failures += 1
                return BatchItemResult(
                    item_id=str(case.id),
                    status=ItemStatus.FAILED,
                    error_message=cascade_result.error,
                )

            # Success: reset circuit breaker
            self._consecutive_failures = 0
            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.SUCCESS,
            )

        except Exception as exc:
            self._consecutive_failures += 1
            logger.error(
                "cascade_batch_item_failed",
                case_id=str(case.id),
                error=str(exc),
            )
            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.FAILED,
                error_message=str(exc),
            )
