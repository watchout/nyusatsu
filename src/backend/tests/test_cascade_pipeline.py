"""Tests for CascadePipeline (Wave 6).

Tests happy path, partial failure, and ineligible/uncertain skip scenarios.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.company_profile import CompanyProfile
from app.models.eligibility_result import EligibilityResult
from app.services.cascade.cascade_pipeline import CascadePipeline
from app.services.checklist_gen.checklist_service import ChecklistError
from app.services.judgment.judgment_service import JudgmentError
from app.services.llm.mock import MockProvider
from app.services.reading.reading_service import ReadingError

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _mock_card():
    card = MagicMock(spec=CaseCard)
    card.id = uuid4()
    card.confidence_score = Decimal("0.85")
    card.submission_items = {"bid_time_items": [], "performance_time_items": []}
    card.business_content = {}
    card.risk_factors = []
    card.assertion_counts = {}
    card.schedule = {}
    card.deadline_at = None
    return card


def _mock_elig(verdict: str = "eligible"):
    elig = MagicMock(spec=EligibilityResult)
    elig.id = uuid4()
    elig.verdict = verdict
    elig.human_override = None
    elig.check_details = {"hard_checks": [], "soft_checks": []}
    elig.soft_gaps = []
    return elig


@pytest.mark.anyio
class TestCascadePipeline:
    async def test_eligible_full_run(self, db) -> None:
        """Eligible case runs through all 3 stages."""
        await db.execute(delete(CompanyProfile))
        profile = CompanyProfile(
            unified_qualification=True, grade="C",
            business_categories=["物品の販売"], regions=["関東・甲信越"],
        )
        db.add(profile)

        case = Case(
            source="test", source_id="cas1", case_name="Eligible Cascade",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
            notice_url="https://example.com/notice.html",
        )
        db.add(case)
        await db.flush()

        mock_card = _mock_card()
        mock_reading = AsyncMock()
        mock_reading.process_case.return_value = mock_card

        mock_elig = _mock_elig("eligible")
        mock_judgment = AsyncMock()
        mock_judgment.judge_case.return_value = mock_elig

        mock_checklist_svc = AsyncMock()
        mock_checklist_svc.generate_checklist.return_value = MagicMock(id=uuid4())

        provider = MockProvider()
        pipeline = CascadePipeline(
            provider,
            reading_service=mock_reading,
            judgment_service=mock_judgment,
            checklist_service=mock_checklist_svc,
        )

        result = await pipeline.process_case(db, case)

        assert result.reading_success is True
        assert result.judgment_success is True
        assert result.checklist_success is True
        assert result.verdict == "eligible"
        assert result.aborted_at is None

    async def test_ineligible_skips_checklist(self, db) -> None:
        """Ineligible case skips checklist stage."""
        case = Case(
            source="test", source_id="cas2", case_name="Ineligible Cascade",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_reading = AsyncMock()
        mock_reading.process_case.return_value = _mock_card()

        mock_judgment = AsyncMock()
        mock_judgment.judge_case.return_value = _mock_elig("ineligible")

        provider = MockProvider()
        pipeline = CascadePipeline(
            provider,
            reading_service=mock_reading,
            judgment_service=mock_judgment,
        )

        result = await pipeline.process_case(db, case)

        assert result.reading_success is True
        assert result.judgment_success is True
        assert result.checklist_success is False
        assert result.verdict == "ineligible"

    async def test_uncertain_skips_checklist(self, db) -> None:
        """Uncertain case skips checklist stage."""
        case = Case(
            source="test", source_id="cas3", case_name="Uncertain Cascade",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_reading = AsyncMock()
        mock_reading.process_case.return_value = _mock_card()

        mock_judgment = AsyncMock()
        mock_judgment.judge_case.return_value = _mock_elig("uncertain")

        provider = MockProvider()
        pipeline = CascadePipeline(
            provider,
            reading_service=mock_reading,
            judgment_service=mock_judgment,
        )

        result = await pipeline.process_case(db, case)

        assert result.reading_success is True
        assert result.judgment_success is True
        assert result.checklist_success is False
        assert result.verdict == "uncertain"

    async def test_reading_failure_aborts(self, db) -> None:
        """Reading failure aborts the entire cascade."""
        case = Case(
            source="test", source_id="cas4", case_name="Reading Fail",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_reading = AsyncMock()
        mock_reading.process_case.side_effect = ReadingError("Fetch failed")

        mock_judgment = AsyncMock()

        provider = MockProvider()
        pipeline = CascadePipeline(
            provider,
            reading_service=mock_reading,
            judgment_service=mock_judgment,
        )

        result = await pipeline.process_case(db, case)

        assert result.reading_success is False
        assert result.judgment_success is False
        assert result.aborted_at == "reading"
        mock_judgment.judge_case.assert_not_called()

    async def test_judgment_failure_aborts(self, db) -> None:
        """Judgment failure aborts checklist."""
        case = Case(
            source="test", source_id="cas5", case_name="Judgment Fail",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_reading = AsyncMock()
        mock_reading.process_case.return_value = _mock_card()

        mock_judgment = AsyncMock()
        mock_judgment.judge_case.side_effect = JudgmentError("No profile")

        mock_checklist = AsyncMock()

        provider = MockProvider()
        pipeline = CascadePipeline(
            provider,
            reading_service=mock_reading,
            judgment_service=mock_judgment,
            checklist_service=mock_checklist,
        )

        result = await pipeline.process_case(db, case)

        assert result.reading_success is True
        assert result.judgment_success is False
        assert result.aborted_at == "judgment"
        mock_checklist.generate_checklist.assert_not_called()

    async def test_checklist_failure_fallback(self, db) -> None:
        """Checklist failure falls back to judging_completed."""
        case = Case(
            source="test", source_id="cas6", case_name="Checklist Fail",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_reading = AsyncMock()
        mock_reading.process_case.return_value = _mock_card()

        mock_judgment = AsyncMock()
        mock_judgment.judge_case.return_value = _mock_elig("eligible")

        mock_checklist = AsyncMock()
        mock_checklist.generate_checklist.side_effect = ChecklistError("Build failed")

        provider = MockProvider()
        pipeline = CascadePipeline(
            provider,
            reading_service=mock_reading,
            judgment_service=mock_judgment,
            checklist_service=mock_checklist,
        )

        result = await pipeline.process_case(db, case)

        assert result.reading_success is True
        assert result.judgment_success is True
        assert result.checklist_success is False
        assert result.aborted_at == "checklist"
        # Case should be at judging_completed (T15 fallback)
        assert case.current_lifecycle_stage == "judging_completed"

    async def test_reading_queued_required(self, db) -> None:
        """Non reading_queued state causes transition failure."""
        case = Case(
            source="test", source_id="cas7", case_name="Wrong Stage",
            current_lifecycle_stage="discovered",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_reading = AsyncMock()
        provider = MockProvider()
        pipeline = CascadePipeline(provider, reading_service=mock_reading)

        result = await pipeline.process_case(db, case)

        # Should fail at reading transition (discovered → reading_in_progress is invalid)
        assert result.reading_success is False
        assert result.aborted_at == "reading"

    async def test_events_recorded(self, db) -> None:
        """Successful cascade records transition events."""
        case = Case(
            source="test", source_id="cas8", case_name="Events",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_reading = AsyncMock()
        mock_reading.process_case.return_value = _mock_card()

        mock_judgment = AsyncMock()
        mock_judgment.judge_case.return_value = _mock_elig("ineligible")

        provider = MockProvider()
        pipeline = CascadePipeline(
            provider,
            reading_service=mock_reading,
            judgment_service=mock_judgment,
        )

        result = await pipeline.process_case(db, case)

        assert result.reading_success is True
        assert result.judgment_success is True
        # Case should be at judging_completed (final stage for ineligible)
        assert case.current_lifecycle_stage == "judging_completed"
