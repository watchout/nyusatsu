"""Tests for SQLAlchemy ORM models.

Covers: model creation, relationships, constraints, CaseEvent INSERT-ONLY,
        LifecycleStage enum, version/is_current pattern, CRUDBase.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BaseBid,
    BatchLog,
    BidDetail,
    Case,
    CaseCard,
    CaseEvent,
    Checklist,
    CompanyProfile,
    EligibilityResult,
    LifecycleStage,
)
from app.services.crud import CRUDBase

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case(**overrides) -> dict:
    defaults = {
        "source": "test_source",
        "source_id": f"test-{uuid.uuid4().hex[:8]}",
        "case_name": "テスト案件",
        "issuing_org": "テスト省",
    }
    defaults.update(overrides)
    return defaults


def _make_case_card(case_id: uuid.UUID, **overrides) -> dict:
    defaults = {
        "case_id": case_id,
        "status": "completed",
        "extraction_method": "text",
    }
    defaults.update(overrides)
    return defaults


def _make_eligibility(case_id: uuid.UUID, case_card_id: uuid.UUID, **overrides) -> dict:
    defaults = {
        "case_id": case_id,
        "case_card_id": case_card_id,
        "verdict": "eligible",
        "confidence": Decimal("0.95"),
        "check_details": {"items": []},
        "company_profile_snapshot": {"grade": "D"},
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# LifecycleStage enum
# ---------------------------------------------------------------------------

class TestLifecycleStage:
    def test_count(self):
        assert len(LifecycleStage) == 17

    def test_all_values(self):
        expected = {
            "discovered", "scored", "under_review", "planned", "skipped",
            "reading_queued", "reading_in_progress", "reading_completed", "reading_failed",
            "judging_queued", "judging_in_progress", "judging_completed", "judging_failed",
            "checklist_generating", "checklist_active", "checklist_completed",
            "archived",
        }
        assert {s.value for s in LifecycleStage} == expected

    def test_str_value(self):
        assert LifecycleStage.discovered == "discovered"
        assert LifecycleStage.archived.value == "archived"


# ---------------------------------------------------------------------------
# Basic model creation
# ---------------------------------------------------------------------------

class TestCaseModel:
    async def test_create_case(self, db: AsyncSession):
        case = Case(**_make_case())
        db.add(case)
        await db.flush()

        assert case.id is not None
        assert case.status == "new"
        assert case.current_lifecycle_stage == "discovered"

    async def test_case_unique_source(self, db: AsyncSession):
        data = _make_case(source="dup_test", source_id="same-id")
        db.add(Case(**data))
        await db.flush()

        db.add(Case(**data))
        with pytest.raises(Exception):  # IntegrityError  # noqa: B017
            await db.flush()


class TestCompanyProfile:
    async def test_seed_data_exists(self, db: AsyncSession):
        result = await db.execute(select(CompanyProfile))
        profile = result.scalars().first()
        assert profile is not None
        assert profile.grade == "D"
        assert profile.unified_qualification is True


class TestBatchLog:
    async def test_create_batch_log(self, db: AsyncSession):
        log = BatchLog(
            source="test_source",
            feature_origin="F-001",
            batch_type="case_fetch",
        )
        db.add(log)
        await db.flush()

        assert log.id is not None
        assert log.status == "running"
        assert log.total_fetched == 0


class TestBaseBidAndDetail:
    async def test_create_base_bid_with_detail(self, db: AsyncSession):
        bid = BaseBid(
            source_id=f"od-{uuid.uuid4().hex[:8]}",
            case_name="テスト落札",
            issuing_org="テスト省",
            winning_amount=1_000_000,
        )
        db.add(bid)
        await db.flush()

        detail = BidDetail(
            base_bid_id=bid.id,
            num_participants=5,
            budget_amount=1_200_000,
            winning_rate=Decimal("0.8333"),
        )
        db.add(detail)
        await db.flush()

        assert detail.id is not None
        assert detail.base_bid_id == bid.id


# ---------------------------------------------------------------------------
# Version + is_current pattern
# ---------------------------------------------------------------------------

class TestVersionPattern:
    async def test_case_card_versioning(self, db: AsyncSession):
        case = Case(**_make_case())
        db.add(case)
        await db.flush()

        card_v1 = CaseCard(**_make_case_card(case.id, version=1, is_current=True))
        db.add(card_v1)
        await db.flush()

        # Simulate re-read: v1 → is_current=false, v2 → is_current=true
        card_v1.is_current = False
        card_v2 = CaseCard(**_make_case_card(case.id, version=2, is_current=True))
        db.add(card_v2)
        await db.flush()

        assert card_v1.is_current is False
        assert card_v2.is_current is True
        assert card_v2.version == 2

    async def test_eligibility_versioning(self, db: AsyncSession):
        case = Case(**_make_case())
        db.add(case)
        await db.flush()

        card = CaseCard(**_make_case_card(case.id))
        db.add(card)
        await db.flush()

        er = EligibilityResult(**_make_eligibility(case.id, card.id))
        db.add(er)
        await db.flush()

        assert er.verdict == "eligible"
        assert er.confidence == Decimal("0.95")
        assert er.version == 1


# ---------------------------------------------------------------------------
# CaseEvent INSERT-ONLY enforcement
# ---------------------------------------------------------------------------

class TestCaseEventInsertOnly:
    async def test_create_event(self, db: AsyncSession):
        case = Case(**_make_case())
        db.add(case)
        await db.flush()

        evt = CaseEvent(
            case_id=case.id,
            event_type="case_discovered",
            to_status="discovered",
            triggered_by="batch",
            feature_origin="F-001",
        )
        db.add(evt)
        await db.flush()

        assert evt.id is not None
        assert evt.actor_id == "system"

    async def test_update_raises(self, db: AsyncSession):
        case = Case(**_make_case())
        db.add(case)
        await db.flush()

        evt = CaseEvent(
            case_id=case.id,
            event_type="case_discovered",
            to_status="discovered",
            triggered_by="batch",
            feature_origin="F-001",
        )
        db.add(evt)
        await db.flush()

        evt.event_type = "modified"
        with pytest.raises(RuntimeError, match="INSERT-ONLY.*UPDATE"):
            await db.flush()

    async def test_delete_raises(self, db: AsyncSession):
        case = Case(**_make_case())
        db.add(case)
        await db.flush()

        evt = CaseEvent(
            case_id=case.id,
            event_type="case_discovered",
            to_status="discovered",
            triggered_by="batch",
            feature_origin="F-001",
        )
        db.add(evt)
        await db.flush()

        await db.delete(evt)
        with pytest.raises(RuntimeError, match="INSERT-ONLY.*DELETE"):
            await db.flush()


# ---------------------------------------------------------------------------
# Checklist (3 FK chain)
# ---------------------------------------------------------------------------

class TestChecklist:
    async def test_create_full_chain(self, db: AsyncSession):
        case = Case(**_make_case())
        db.add(case)
        await db.flush()

        card = CaseCard(**_make_case_card(case.id))
        db.add(card)
        await db.flush()

        er = EligibilityResult(**_make_eligibility(case.id, card.id))
        db.add(er)
        await db.flush()

        cl = Checklist(
            case_id=case.id,
            case_card_id=card.id,
            eligibility_result_id=er.id,
            checklist_items=[{"label": "必要書類", "done": False}],
            schedule_items=[{"date": "2026-03-01", "task": "提出"}],
        )
        db.add(cl)
        await db.flush()

        assert cl.id is not None
        assert cl.status == "draft"
        assert cl.version == 1


# ---------------------------------------------------------------------------
# CRUDBase
# ---------------------------------------------------------------------------

class TestCRUDBase:
    async def test_crud_create_and_get(self, db: AsyncSession):
        crud = CRUDBase[Case](Case)
        case = await crud.create(db, obj_in=_make_case())
        assert case.id is not None

        fetched = await crud.get(db, id=case.id)
        assert fetched is not None
        assert fetched.case_name == "テスト案件"

    async def test_crud_get_multi(self, db: AsyncSession):
        crud = CRUDBase[Case](Case)
        for i in range(3):
            await crud.create(db, obj_in=_make_case(source_id=f"multi-{i}"))

        cases = await crud.get_multi(db, limit=10)
        assert len(cases) >= 3

    async def test_crud_update(self, db: AsyncSession):
        crud = CRUDBase[Case](Case)
        case = await crud.create(db, obj_in=_make_case())

        updated = await crud.update(db, db_obj=case, obj_in={"status": "reviewed"})
        assert updated.status == "reviewed"

    async def test_crud_count(self, db: AsyncSession):
        crud = CRUDBase[BatchLog](BatchLog)
        initial = await crud.count(db)

        await crud.create(db, obj_in={
            "source": "count_test",
            "feature_origin": "F-001",
            "batch_type": "case_fetch",
        })
        assert await crud.count(db) == initial + 1
