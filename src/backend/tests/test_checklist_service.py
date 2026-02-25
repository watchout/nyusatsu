"""Tests for ChecklistService (F-004)."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.company_profile import CompanyProfile
from app.models.eligibility_result import EligibilityResult
from app.services.checklist_gen.checklist_service import ChecklistError, ChecklistService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _card_data() -> dict:
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
            "bid_time_items": [
                {"name": "入札書", "assertion_type": "fact"},
            ],
            "performance_time_items": [],
        },
        "risk_factors": [],
    }


async def _setup_eligible(db) -> tuple[Case, CaseCard, EligibilityResult]:
    """Create a Case + CaseCard + eligible EligibilityResult."""
    case = Case(
        source="test", source_id=f"cl{uuid4().hex[:6]}", case_name="Checklist Case",
        current_lifecycle_stage="checklist_generating",
        first_seen_at=_NOW, issuing_org="テスト機関",
    )
    db.add(case)
    await db.flush()

    card = CaseCard(
        case_id=case.id, version=1, is_current=True,
        confidence_score=Decimal("0.85"),
        deadline_at=datetime(2026, 3, 15, 17, 0, tzinfo=timezone.utc),
        **_card_data(),
    )
    db.add(card)
    await db.flush()

    elig = EligibilityResult(
        case_id=case.id, case_card_id=card.id,
        version=1, is_current=True,
        verdict="eligible",
        confidence=Decimal("0.85"),
        hard_fail_reasons=[],
        soft_gaps=[],
        check_details={"hard_checks": [], "soft_checks": []},
        company_profile_snapshot={"grade": "C"},
    )
    db.add(elig)
    await db.flush()

    return case, card, elig


@pytest.mark.anyio
class TestChecklistService:
    async def test_eligible_generates_checklist(self, db) -> None:
        """Eligible case generates a checklist."""
        case, card, elig = await _setup_eligible(db)

        service = ChecklistService()
        checklist = await service.generate_checklist(db, case, card, elig)

        assert checklist.is_current is True
        assert checklist.status == "active"
        assert len(checklist.checklist_items) >= 1
        assert checklist.progress["total"] >= 1

    async def test_ineligible_skips(self, db) -> None:
        """Ineligible case raises ChecklistError."""
        case, card, elig = await _setup_eligible(db)
        elig.verdict = "ineligible"
        await db.flush()

        service = ChecklistService()

        with pytest.raises(ChecklistError, match="verdict=ineligible"):
            await service.generate_checklist(db, case, card, elig)

    async def test_uncertain_skips(self, db) -> None:
        """Uncertain case raises ChecklistError."""
        case, card, elig = await _setup_eligible(db)
        elig.verdict = "uncertain"
        await db.flush()

        service = ChecklistService()

        with pytest.raises(ChecklistError, match="verdict=uncertain"):
            await service.generate_checklist(db, case, card, elig)

    async def test_override_eligible_generates(self, db) -> None:
        """Human override to eligible generates checklist even if verdict=ineligible."""
        case, card, elig = await _setup_eligible(db)
        elig.verdict = "ineligible"
        elig.human_override = "eligible"
        await db.flush()

        service = ChecklistService()
        checklist = await service.generate_checklist(db, case, card, elig)

        assert checklist.is_current is True

    async def test_progress_calculation(self, db) -> None:
        """Progress should reflect item counts."""
        case, card, elig = await _setup_eligible(db)

        service = ChecklistService()
        checklist = await service.generate_checklist(db, case, card, elig)

        assert checklist.progress["total"] > 0
        assert checklist.progress["done"] == 0
        assert checklist.progress["rate"] == 0.0

    async def test_version_rotation(self, db) -> None:
        """Re-generating rotates to new version."""
        case, card, elig = await _setup_eligible(db)

        service = ChecklistService()

        c1 = await service.generate_checklist(db, case, card, elig)
        assert c1.version == 1

        c2 = await service.generate_checklist(db, case, card, elig)
        assert c2.version == 2
        assert c2.is_current is True

        await db.refresh(c1)
        assert c1.is_current is False
