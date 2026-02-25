"""Judgment batch runner — F-003 pipeline.

Processes cases in `judging_queued` stage through the judgment pipeline.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import BatchConfig, BatchItemResult, ItemStatus
from app.services.event_service import EventService
from app.services.judgment.judgment_service import JudgmentError, JudgmentService
from app.services.lifecycle import LifecycleManager
from app.services.version_manager import VersionManager

logger = structlog.get_logger()


class JudgmentBatch(BaseBatchRunner):
    """Batch runner for F-003 judgment pipeline."""

    def __init__(
        self,
        *,
        judgment_service: JudgmentService | None = None,
    ) -> None:
        self._judgment_service = judgment_service or JudgmentService()
        self._event_service = EventService(lifecycle=LifecycleManager())
        self._card_vm = VersionManager(CaseCard)

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="system",
            batch_type="judging",
            feature_origin="F-003",
        )

    async def fetch_items(self, db: AsyncSession) -> AsyncIterator[Any]:
        """Yield cases in judging_queued stage."""
        stmt = select(Case).where(
            Case.current_lifecycle_stage == "judging_queued",
        )
        result = await db.execute(stmt)
        for case in result.scalars():
            yield case

    async def process_item(self, db: AsyncSession, item: Any) -> BatchItemResult:
        """Process a single case through the judgment pipeline."""
        case: Case = item

        try:
            # Get current CaseCard
            card = await self._card_vm.get_current(db, case_id=case.id)
            if not card:
                raise JudgmentError("No CaseCard found for case")

            # Transition: judging_queued → judging_in_progress
            await self._event_service.record_transition(
                db,
                case=case,
                to_stage="judging_in_progress",
                triggered_by="judgment_batch",
                feature_origin="F-003",
                expected_lifecycle_stage="judging_queued",
            )

            # Run judgment pipeline
            eligibility = await self._judgment_service.judge_case(db, case, card)

            # Transition: judging_in_progress → judging_completed
            await self._event_service.record_transition(
                db,
                case=case,
                to_stage="judging_completed",
                triggered_by="judgment_batch",
                feature_origin="F-003",
                expected_lifecycle_stage="judging_in_progress",
                payload={
                    "eligibility_result_id": str(eligibility.id),
                    "verdict": eligibility.verdict,
                },
            )

            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.SUCCESS,
            )

        except (JudgmentError, Exception) as exc:
            logger.error(
                "judgment_batch_item_failed",
                case_id=str(case.id),
                error=str(exc),
            )

            # Transition: → judging_failed
            try:
                await self._event_service.record_transition(
                    db,
                    case=case,
                    to_stage="judging_failed",
                    triggered_by="judgment_batch",
                    feature_origin="F-003",
                    payload={"error": str(exc)},
                )
            except Exception:
                logger.error(
                    "judgment_batch_transition_failed",
                    case_id=str(case.id),
                )

            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.FAILED,
                error_message=str(exc),
            )
