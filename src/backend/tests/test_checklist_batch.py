"""Tests for ChecklistBatch (F-004)."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.eligibility_result import EligibilityResult
from app.services.batch.checklist_batch import ChecklistBatch
from app.services.batch.types import ItemStatus
from app.services.checklist_gen.checklist_service import ChecklistError

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _card_data() -> dict:
    return {
        "eligibility": {
            "unified_qualification": True,
            "grade": "C",
            "business_category": "物品の販売",
            "region": "関東・甲信越",
            "additional_requirements": [],
        },
        "schedule": {},
        "business_content": {},
        "submission_items": {
            "bid_time_items": [{"name": "入札書", "assertion_type": "fact"}],
            "performance_time_items": [],
        },
        "risk_factors": [],
    }


@pytest.mark.anyio
class TestChecklistBatch:
    async def test_fetch_generating_cases(self, db) -> None:
        """fetch_items yields only checklist_generating cases."""
        gen = Case(
            source="test", source_id="cb1", case_name="Generating",
            current_lifecycle_stage="checklist_generating",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        other = Case(
            source="test", source_id="cb2", case_name="Other",
            current_lifecycle_stage="judging_completed",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add_all([gen, other])
        await db.flush()

        batch = ChecklistBatch()
        items = [item async for item in batch.fetch_items(db)]

        assert len(items) == 1
        assert items[0].source_id == "cb1"

    async def test_successful_processing(self, db) -> None:
        """Successful processing transitions to checklist_active."""
        case = Case(
            source="test", source_id="cb3", case_name="Success",
            current_lifecycle_stage="checklist_generating",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        card = CaseCard(
            case_id=case.id, version=1, is_current=True,
            confidence_score=Decimal("0.85"),
            **_card_data(),
        )
        db.add(card)
        await db.flush()

        elig = EligibilityResult(
            case_id=case.id, case_card_id=card.id,
            version=1, is_current=True,
            verdict="eligible", confidence=Decimal("0.85"),
            hard_fail_reasons=[], soft_gaps=[],
            check_details={"hard_checks": [], "soft_checks": []},
            company_profile_snapshot={"grade": "C"},
        )
        db.add(elig)
        await db.flush()

        batch = ChecklistBatch()
        result = await batch.process_item(db, case)

        assert result.status == ItemStatus.SUCCESS
        assert case.current_lifecycle_stage == "checklist_active"

    async def test_failed_falls_back_to_judging_completed(self, db) -> None:
        """Failed processing falls back to judging_completed (T15)."""
        case = Case(
            source="test", source_id="cb4", case_name="Fail",
            current_lifecycle_stage="checklist_generating",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        mock_service = AsyncMock()
        mock_service.generate_checklist.side_effect = ChecklistError("Test error")

        batch = ChecklistBatch(checklist_service=mock_service)
        result = await batch.process_item(db, case)

        assert result.status == ItemStatus.FAILED
        assert case.current_lifecycle_stage == "judging_completed"

    async def test_empty_queue(self, db) -> None:
        """Empty queue yields no items."""
        batch = ChecklistBatch()
        items = [item async for item in batch.fetch_items(db)]
        assert len(items) == 0

    async def test_config_values(self) -> None:
        """Config should match F-004 spec."""
        batch = ChecklistBatch()
        assert batch.config.source == "system"
        assert batch.config.batch_type == "checklist"
        assert batch.config.feature_origin == "F-004"
