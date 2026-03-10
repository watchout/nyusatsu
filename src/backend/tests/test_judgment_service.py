"""Tests for JudgmentService (F-003)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.company_profile import CompanyProfile
from app.services.judgment.judgment_service import JudgmentError, JudgmentService

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_case_card_data() -> dict:
    """CaseCard eligibility / schedule / business_content JSONB data."""
    return {
        "eligibility": {
            "unified_qualification": True,
            "grade": "C",
            "business_category": "物品の販売",
            "region": "関東・甲信越",
            "additional_requirements": [],
        },
        "schedule": {
            "submission_deadline": "2026-03-15T17:00:00+09:00",
        },
        "business_content": {
            "summary": "コピー用紙購入",
        },
        "submission_items": {
            "bid_time_items": [],
            "performance_time_items": [],
        },
        "risk_factors": [],
    }


@pytest.mark.anyio
class TestJudgmentService:
    async def test_eligible_judgment(self, db) -> None:
        """Full pipeline with eligible result."""
        await db.execute(delete(CompanyProfile))
        profile = CompanyProfile(
            unified_qualification=True,
            grade="C",
            business_categories=["物品の販売", "役務の提供"],
            regions=["関東・甲信越"],
        )
        db.add(profile)

        # Create case
        case = Case(
            source="test", source_id="j1", case_name="Eligible Case",
            current_lifecycle_stage="judging_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        # Create CaseCard
        card_data = _make_case_card_data()
        card = CaseCard(
            case_id=case.id,
            version=1,
            is_current=True,
            confidence_score=Decimal("0.85"),
            **card_data,
        )
        db.add(card)
        await db.flush()

        service = JudgmentService()
        result = await service.judge_case(db, case, card)

        assert result.verdict == "eligible"
        assert result.confidence >= Decimal("0.60")
        assert result.is_current is True

    async def test_ineligible_judgment(self, db) -> None:
        """Grade mismatch produces ineligible."""
        await db.execute(delete(CompanyProfile))
        profile = CompanyProfile(
            unified_qualification=True,
            grade="D",
            business_categories=["物品の販売"],
            regions=["関東・甲信越"],
        )
        db.add(profile)

        case = Case(
            source="test", source_id="j2", case_name="Ineligible Case",
            current_lifecycle_stage="judging_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        card_data = _make_case_card_data()
        card_data["eligibility"]["grade"] = "A"
        card = CaseCard(
            case_id=case.id,
            version=1,
            is_current=True,
            confidence_score=Decimal("0.85"),
            **card_data,
        )
        db.add(card)
        await db.flush()

        service = JudgmentService()
        result = await service.judge_case(db, case, card)

        assert result.verdict == "ineligible"

    async def test_uncertain_judgment(self, db) -> None:
        """Low confidence produces uncertain."""
        await db.execute(delete(CompanyProfile))
        profile = CompanyProfile(
            unified_qualification=True,
            grade="C",
            business_categories=["物品の販売"],
            regions=["関東・甲信越"],
        )
        db.add(profile)

        case = Case(
            source="test", source_id="j3", case_name="Uncertain Case",
            current_lifecycle_stage="judging_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        card_data = _make_case_card_data()
        card = CaseCard(
            case_id=case.id,
            version=1,
            is_current=True,
            confidence_score=Decimal("0.30"),
            **card_data,
        )
        db.add(card)
        await db.flush()

        service = JudgmentService()
        result = await service.judge_case(db, case, card)

        assert result.verdict == "uncertain"

    async def test_version_rotation(self, db) -> None:
        """Re-judging rotates to new version."""
        await db.execute(delete(CompanyProfile))
        profile = CompanyProfile(
            unified_qualification=True,
            grade="C",
            business_categories=["物品の販売"],
            regions=["関東・甲信越"],
        )
        db.add(profile)

        case = Case(
            source="test", source_id="j4", case_name="Rotation Case",
            current_lifecycle_stage="judging_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        card_data = _make_case_card_data()
        card = CaseCard(
            case_id=case.id,
            version=1,
            is_current=True,
            confidence_score=Decimal("0.85"),
            **card_data,
        )
        db.add(card)
        await db.flush()

        service = JudgmentService()

        # First judgment
        r1 = await service.judge_case(db, case, card)
        assert r1.version == 1
        assert r1.is_current is True

        # Second judgment (re-judge)
        r2 = await service.judge_case(db, case, card)
        assert r2.version == 2
        assert r2.is_current is True

        # Verify first version is no longer current
        await db.refresh(r1)
        assert r1.is_current is False

    async def test_no_profile_raises(self, db) -> None:
        """Missing company profile raises JudgmentError."""
        await db.execute(delete(CompanyProfile))
        case = Case(
            source="test", source_id="j5", case_name="No Profile",
            current_lifecycle_stage="judging_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        card_data = _make_case_card_data()
        card = CaseCard(
            case_id=case.id,
            version=1,
            is_current=True,
            confidence_score=Decimal("0.85"),
            **card_data,
        )
        db.add(card)
        await db.flush()

        service = JudgmentService()

        with pytest.raises(JudgmentError, match="No company profile"):
            await service.judge_case(db, case, card)
