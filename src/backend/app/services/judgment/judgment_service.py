"""Judgment service for F-003.

Orchestrates the judgment pipeline:
  1. Load CompanyProfile
  2. Parse CaseCard extraction
  3. Run JudgmentEngine
  4. Save EligibilityResult via VersionManager
"""

from __future__ import annotations

from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.company_profile import CompanyProfile
from app.models.eligibility_result import EligibilityResult
from app.schemas.extraction import CaseCardExtraction
from app.services.judgment.judgment_engine import JudgmentEngine
from app.services.version_manager import VersionManager

logger = structlog.get_logger()


class JudgmentError(Exception):
    """Raised when judgment processing fails."""


class JudgmentService:
    """Orchestrates F-003 judgment pipeline."""

    def __init__(self, *, engine: JudgmentEngine | None = None) -> None:
        self._engine = engine or JudgmentEngine()
        self._version_manager = VersionManager(EligibilityResult)

    async def judge_case(
        self,
        db: AsyncSession,
        case: Case,
        case_card: CaseCard,
    ) -> EligibilityResult:
        """Run judgment on a case and persist the result.

        Args:
            db: Database session (caller manages transaction).
            case: The case being judged.
            case_card: The current CaseCard with extraction data.

        Returns:
            The created EligibilityResult record.

        Raises:
            JudgmentError: If judgment cannot proceed.
        """
        # Load company profile
        profile = await self._load_profile(db)
        if profile is None:
            raise JudgmentError("No company profile found")

        # Parse extraction from CaseCard JSONB
        extraction = self._parse_extraction(case_card)

        # Get confidence score from case_card
        confidence_score = float(case_card.confidence_score or Decimal("1.0"))

        # Run judgment engine
        result = self._engine.judge(
            extraction, profile, confidence_score=confidence_score,
        )

        # Persist via VersionManager
        existing = await self._version_manager.get_current(db, case_id=case.id)
        if existing:
            eligibility = await self._version_manager.rotate(
                db, case_id=case.id,
                new_data={
                    "case_card_id": case_card.id,
                    "verdict": result.verdict,
                    "confidence": result.confidence,
                    "hard_fail_reasons": result.hard_fail_reasons,
                    "soft_gaps": result.soft_gaps,
                    "evidence_refs": result.evidence_refs,
                    "check_details": result.check_details,
                    "company_profile_snapshot": result.company_profile_snapshot,
                },
            )
        else:
            eligibility = await self._version_manager.create_initial(
                db,
                data={
                    "case_id": case.id,
                    "case_card_id": case_card.id,
                    "verdict": result.verdict,
                    "confidence": result.confidence,
                    "hard_fail_reasons": result.hard_fail_reasons,
                    "soft_gaps": result.soft_gaps,
                    "evidence_refs": result.evidence_refs,
                    "check_details": result.check_details,
                    "company_profile_snapshot": result.company_profile_snapshot,
                },
            )

        logger.info(
            "judgment_completed",
            case_id=str(case.id),
            verdict=result.verdict,
            confidence=str(result.confidence),
        )

        return eligibility

    async def _load_profile(self, db: AsyncSession) -> CompanyProfile | None:
        """Load the single company profile (Phase 1 assumption)."""
        stmt = select(CompanyProfile).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def _parse_extraction(self, case_card: CaseCard) -> CaseCardExtraction:
        """Parse CaseCard JSONB fields into CaseCardExtraction."""
        return CaseCardExtraction(
            eligibility=case_card.eligibility,
            schedule=case_card.schedule,
            business_content=case_card.business_content,
            submission_items=case_card.submission_items,
            risk_factors=case_card.risk_factors or [],
        )
