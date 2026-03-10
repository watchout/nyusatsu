"""Tests for JudgmentBatch (F-003)."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.company_profile import CompanyProfile
from app.services.batch.judgment_batch import JudgmentBatch
from app.services.batch.types import ItemStatus
from app.services.judgment.judgment_service import JudgmentError

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
        "submission_items": {"bid_time_items": [], "performance_time_items": []},
        "risk_factors": [],
    }


@pytest.mark.anyio
class TestJudgmentBatch:
    async def test_fetch_judging_queued_cases(self, db) -> None:
        """fetch_items should yield only judging_queued cases."""
        queued = Case(
            source="test", source_id="jb1", case_name="Queued",
            current_lifecycle_stage="judging_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        other = Case(
            source="test", source_id="jb2", case_name="Other",
            current_lifecycle_stage="reading_completed",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add_all([queued, other])
        await db.flush()

        batch = JudgmentBatch()

        items = []
        async for item in batch.fetch_items(db):
            items.append(item)

        assert len(items) == 1
        assert items[0].source_id == "jb1"

    async def test_successful_processing(self, db) -> None:
        """Successful processing should return SUCCESS status."""
        await db.execute(delete(CompanyProfile))
        profile = CompanyProfile(
            unified_qualification=True,
            grade="C",
            business_categories=["物品の販売"],
            regions=["関東・甲信越"],
        )
        db.add(profile)

        case = Case(
            source="test", source_id="jb3", case_name="Success",
            current_lifecycle_stage="judging_queued",
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

        batch = JudgmentBatch()
        result = await batch.process_item(db, case)

        assert result.status == ItemStatus.SUCCESS
        assert case.current_lifecycle_stage == "judging_completed"

    async def test_failed_processing(self, db) -> None:
        """Failed processing should return FAILED status."""
        case = Case(
            source="test", source_id="jb4", case_name="Fail",
            current_lifecycle_stage="judging_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        # No CaseCard → judgment will fail
        mock_service = AsyncMock()
        mock_service.judge_case.side_effect = JudgmentError("No CaseCard found")

        batch = JudgmentBatch(judgment_service=mock_service)
        result = await batch.process_item(db, case)

        assert result.status == ItemStatus.FAILED
        assert "No CaseCard" in result.error_message

    async def test_empty_queue(self, db) -> None:
        """Empty queue should yield no items."""
        batch = JudgmentBatch()

        items = []
        async for item in batch.fetch_items(db):
            items.append(item)

        assert len(items) == 0

    async def test_config_values(self) -> None:
        """Config should match F-003 batch specification."""
        batch = JudgmentBatch()

        assert batch.config.source == "system"
        assert batch.config.batch_type == "judging"
        assert batch.config.feature_origin == "F-003"
