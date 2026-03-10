"""Checklist batch runner — F-004 pipeline.

Processes cases in `checklist_generating` stage.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.eligibility_result import EligibilityResult
from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import BatchConfig, BatchItemResult, ItemStatus
from app.services.checklist_gen.checklist_service import ChecklistError, ChecklistService
from app.services.event_service import EventService
from app.services.lifecycle import LifecycleManager
from app.services.version_manager import VersionManager

logger = structlog.get_logger()


class ChecklistBatch(BaseBatchRunner):
    """Batch runner for F-004 checklist generation pipeline."""

    def __init__(
        self,
        *,
        checklist_service: ChecklistService | None = None,
    ) -> None:
        self._checklist_service = checklist_service or ChecklistService()
        self._event_service = EventService(lifecycle=LifecycleManager())
        self._card_vm = VersionManager(CaseCard)
        self._elig_vm = VersionManager(EligibilityResult)

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="system",
            batch_type="checklist",
            feature_origin="F-004",
        )

    async def fetch_items(self, db: AsyncSession) -> AsyncIterator[Any]:
        """Yield cases in checklist_generating stage."""
        stmt = select(Case).where(
            Case.current_lifecycle_stage == "checklist_generating",
        )
        result = await db.execute(stmt)
        for case in result.scalars():
            yield case

    async def process_item(self, db: AsyncSession, item: Any) -> BatchItemResult:
        """Process a single case through the checklist pipeline."""
        case: Case = item

        try:
            # Get current CaseCard and EligibilityResult
            card = await self._card_vm.get_current(db, case_id=case.id)
            if not card:
                raise ChecklistError("No CaseCard found for case")

            elig = await self._elig_vm.get_current(db, case_id=case.id)
            if not elig:
                raise ChecklistError("No EligibilityResult found for case")

            # Generate checklist
            checklist = await self._checklist_service.generate_checklist(
                db, case, card, elig,
            )

            # Transition: checklist_generating → checklist_active
            await self._event_service.record_transition(
                db,
                case=case,
                to_stage="checklist_active",
                triggered_by="checklist_batch",
                feature_origin="F-004",
                expected_lifecycle_stage="checklist_generating",
                payload={"checklist_id": str(checklist.id)},
            )

            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.SUCCESS,
            )

        except (ChecklistError, Exception) as exc:
            logger.error(
                "checklist_batch_item_failed",
                case_id=str(case.id),
                error=str(exc),
            )

            # Transition: checklist_generating → judging_completed (T15 fallback)
            try:
                await self._event_service.record_transition(
                    db,
                    case=case,
                    to_stage="judging_completed",
                    triggered_by="checklist_batch",
                    feature_origin="F-004",
                    payload={"error": str(exc)},
                )
            except Exception:
                logger.error(
                    "checklist_batch_transition_failed",
                    case_id=str(case.id),
                )

            return BatchItemResult(
                item_id=str(case.id),
                status=ItemStatus.FAILED,
                error_message=str(exc),
            )
