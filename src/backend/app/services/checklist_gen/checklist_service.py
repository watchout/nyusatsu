"""Checklist service for F-004.

Orchestrates checklist generation:
  1. Trigger check (verdict or human override)
  2. Build checklist items
  3. Calculate reverse schedule
  4. Persist Checklist via VersionManager
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.checklist import Checklist
from app.models.eligibility_result import EligibilityResult
from app.services.checklist_gen.checklist_builder import ChecklistBuilder
from app.services.checklist_gen.schedule_calculator import ScheduleCalculator
from app.services.version_manager import VersionManager

logger = structlog.get_logger()


class ChecklistError(Exception):
    """Raised when checklist generation fails."""


class ChecklistService:
    """Orchestrates F-004 checklist generation pipeline."""

    def __init__(
        self,
        *,
        builder: ChecklistBuilder | None = None,
        calculator: ScheduleCalculator | None = None,
    ) -> None:
        self._builder = builder or ChecklistBuilder()
        self._calculator = calculator or ScheduleCalculator()
        self._version_manager = VersionManager(Checklist)

    async def generate_checklist(
        self,
        db: AsyncSession,
        case: Case,
        case_card: CaseCard,
        eligibility_result: EligibilityResult,
    ) -> Checklist:
        """Generate a checklist for a case.

        Only generates if verdict is "eligible" or human_override is "eligible".
        Otherwise raises ChecklistError.
        """
        # Trigger check
        effective_verdict = (
            eligibility_result.human_override
            or eligibility_result.verdict
        )
        if effective_verdict != "eligible":
            raise ChecklistError(
                f"Cannot generate checklist: verdict={effective_verdict}",
            )

        # Build extraction dict from CaseCard
        extraction = {
            "submission_items": case_card.submission_items,
            "business_content": case_card.business_content,
        }

        # Build checklist items
        build_result = self._builder.build(
            extraction,
            eligibility_check_details=eligibility_result.check_details,
            risk_factors=case_card.risk_factors,
            soft_gaps=eligibility_result.soft_gaps,
            assertion_counts=case_card.assertion_counts,
        )

        # Calculate schedule
        schedule_items = self._calculator.calculate(
            case_card.deadline_at,
            quote_deadline=self._get_quote_deadline(case_card),
        )

        # Compute progress
        total = len(build_result.checklist_items)
        done = sum(1 for i in build_result.checklist_items if i.get("is_checked"))
        progress = {
            "total": total,
            "done": done,
            "rate": round(done / total, 2) if total > 0 else 0.0,
        }

        # Persist via VersionManager
        existing = await self._version_manager.get_current(db, case_id=case.id)
        data = {
            "case_card_id": case_card.id,
            "eligibility_result_id": eligibility_result.id,
            "checklist_items": build_result.checklist_items,
            "schedule_items": schedule_items,
            "warnings": build_result.warnings,
            "progress": progress,
            "status": "active",
        }

        if existing:
            checklist = await self._version_manager.rotate(
                db, case_id=case.id, new_data=data,
            )
        else:
            data["case_id"] = case.id
            checklist = await self._version_manager.create_initial(db, data=data)

        logger.info(
            "checklist_generated",
            case_id=str(case.id),
            total_items=total,
            warnings=len(build_result.warnings),
        )

        return checklist

    @staticmethod
    def _get_quote_deadline(case_card: CaseCard) -> str | None:
        schedule = case_card.schedule
        if isinstance(schedule, dict):
            return schedule.get("quote_deadline")
        return None
