"""Cascade pipeline for F-002 → F-003 → F-004.

Processes a case through 3 stages:
  1. Reading (F-002): Document fetch + LLM extraction → CaseCard
  2. Judgment (F-003): Eligibility check → EligibilityResult
  3. Checklist (F-004): Checklist generation (only if eligible)

Partial failure aborts remaining stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.services.checklist_gen.checklist_service import ChecklistError, ChecklistService
from app.services.event_service import EventService
from app.services.judgment.judgment_service import JudgmentError, JudgmentService
from app.services.lifecycle import LifecycleManager
from app.services.llm.base import LLMProvider
from app.services.reading.reading_service import ReadingError, ReadingService
from app.services.version_manager import VersionManager

logger = structlog.get_logger()


@dataclass
class CascadeResult:
    """Result of cascade pipeline execution."""

    case_id: str
    reading_success: bool = False
    judgment_success: bool = False
    checklist_success: bool = False
    error: str | None = None
    verdict: str | None = None
    aborted_at: str | None = None  # "reading", "judgment", "checklist"


class CascadePipeline:
    """3-stage cascade: reading → judgment → checklist."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        reading_service: ReadingService | None = None,
        judgment_service: JudgmentService | None = None,
        checklist_service: ChecklistService | None = None,
    ) -> None:
        self._provider = provider
        self._reading_service = reading_service or ReadingService(provider)
        self._judgment_service = judgment_service or JudgmentService()
        self._checklist_service = checklist_service or ChecklistService()
        self._event_service = EventService(lifecycle=LifecycleManager())
        self._card_vm = VersionManager(CaseCard)

    async def process_case(self, db: AsyncSession, case: Case) -> CascadeResult:
        """Run the full cascade pipeline.

        Expects case in reading_queued stage.
        """
        result = CascadeResult(case_id=str(case.id))

        # Stage 1: Reading
        try:
            await self._event_service.record_transition(
                db, case=case, to_stage="reading_in_progress",
                triggered_by="cascade", feature_origin="F-002",
                expected_lifecycle_stage="reading_queued",
            )
            card = await self._reading_service.process_case(db, case)
            await self._event_service.record_transition(
                db, case=case, to_stage="reading_completed",
                triggered_by="cascade", feature_origin="F-002",
                expected_lifecycle_stage="reading_in_progress",
                payload={"case_card_id": str(card.id)},
            )
            result.reading_success = True
        except (ReadingError, Exception) as exc:
            result.error = str(exc)
            result.aborted_at = "reading"
            await self._safe_transition(
                db, case, "reading_failed", "F-002", str(exc),
            )
            logger.error("cascade_reading_failed", case_id=str(case.id), error=str(exc))
            return result

        # Stage 2: Judgment
        try:
            await self._event_service.record_transition(
                db, case=case, to_stage="judging_queued",
                triggered_by="cascade", feature_origin="F-002",
                expected_lifecycle_stage="reading_completed",
            )
            await self._event_service.record_transition(
                db, case=case, to_stage="judging_in_progress",
                triggered_by="cascade", feature_origin="F-003",
                expected_lifecycle_stage="judging_queued",
            )
            eligibility = await self._judgment_service.judge_case(db, case, card)
            await self._event_service.record_transition(
                db, case=case, to_stage="judging_completed",
                triggered_by="cascade", feature_origin="F-003",
                expected_lifecycle_stage="judging_in_progress",
                payload={"verdict": eligibility.verdict},
            )
            result.judgment_success = True
            result.verdict = eligibility.verdict
        except (JudgmentError, Exception) as exc:
            result.error = str(exc)
            result.aborted_at = "judgment"
            await self._safe_transition(
                db, case, "judging_failed", "F-003", str(exc),
            )
            logger.error("cascade_judgment_failed", case_id=str(case.id), error=str(exc))
            return result

        # Stage 3: Checklist (only if eligible)
        effective_verdict = eligibility.human_override or eligibility.verdict
        if effective_verdict != "eligible":
            logger.info(
                "cascade_checklist_skipped",
                case_id=str(case.id),
                verdict=effective_verdict,
            )
            return result

        try:
            await self._event_service.record_transition(
                db, case=case, to_stage="checklist_generating",
                triggered_by="cascade", feature_origin="F-003",
                expected_lifecycle_stage="judging_completed",
            )
            await self._checklist_service.generate_checklist(
                db, case, card, eligibility,
            )
            await self._event_service.record_transition(
                db, case=case, to_stage="checklist_active",
                triggered_by="cascade", feature_origin="F-004",
                expected_lifecycle_stage="checklist_generating",
            )
            result.checklist_success = True
        except (ChecklistError, Exception) as exc:
            result.error = str(exc)
            result.aborted_at = "checklist"
            # T15 fallback: checklist_generating → judging_completed
            await self._safe_transition(
                db, case, "judging_completed", "F-004", str(exc),
            )
            logger.error("cascade_checklist_failed", case_id=str(case.id), error=str(exc))

        return result

    async def _safe_transition(
        self,
        db: AsyncSession,
        case: Case,
        to_stage: str,
        feature_origin: str,
        error_msg: str,
    ) -> None:
        """Attempt a transition, silently catching errors."""
        try:
            await self._event_service.record_transition(
                db, case=case, to_stage=to_stage,
                triggered_by="cascade", feature_origin=feature_origin,
                payload={"error": error_msg},
            )
        except Exception:
            logger.error(
                "cascade_safe_transition_failed",
                case_id=str(case.id),
                to_stage=to_stage,
            )
