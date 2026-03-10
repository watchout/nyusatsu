"""Reading batch runner — F-002 pipeline.

Processes cases in `reading_queued` stage through the full reading pipeline.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import BatchConfig, BatchItemResult, ItemStatus
from app.services.event_service import EventService
from app.services.lifecycle import LifecycleManager
from app.services.llm.base import LLMProvider
from app.services.reading.reading_service import ReadingError, ReadingService

logger = structlog.get_logger()


class ReadingBatch(BaseBatchRunner):
    """Batch runner for F-002 reading pipeline."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        reading_service: ReadingService | None = None,
    ) -> None:
        self._provider = provider
        self._reading_service = reading_service or ReadingService(provider)
        self._event_service = EventService(lifecycle=LifecycleManager())

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="system",
            batch_type="reading",
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
        """Process a single case through the reading pipeline."""
        case: Case = item

        try:
            # Transition: reading_queued → reading_in_progress
            await self._event_service.record_transition(
                db,
                case=case,
                to_stage="reading_in_progress",
                triggered_by="reading_batch",
                feature_origin="F-002",
                expected_lifecycle_stage="reading_queued",
            )

            # Run reading pipeline
            card = await self._reading_service.process_case(db, case)

            # Transition: reading_in_progress → reading_completed
            await self._event_service.record_transition(
                db,
                case=case,
                to_stage="reading_completed",
                triggered_by="reading_batch",
                feature_origin="F-002",
                expected_lifecycle_stage="reading_in_progress",
                payload={"case_card_id": str(card.id)},
            )

            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.SUCCESS,
            )

        except (ReadingError, Exception) as exc:
            logger.error(
                "reading_batch_item_failed",
                case_id=str(case.id),
                error=str(exc),
            )

            # Transition: reading_in_progress → reading_failed
            try:
                await self._event_service.record_transition(
                    db,
                    case=case,
                    to_stage="reading_failed",
                    triggered_by="reading_batch",
                    feature_origin="F-002",
                    payload={"error": str(exc)},
                )
            except Exception:
                logger.error(
                    "reading_batch_transition_failed",
                    case_id=str(case.id),
                )

            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.FAILED,
                error_message=str(exc),
            )
