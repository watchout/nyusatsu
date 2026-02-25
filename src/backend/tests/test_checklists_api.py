"""Tests for Wave 7: Checklist API endpoints (F-004)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.checklist import Checklist
from app.models.eligibility_result import EligibilityResult


async def _setup_checklist(
    db: AsyncSession,
    suffix: str = "001",
    *,
    checklist_items: list | None = None,
) -> tuple[Case, Checklist]:
    """Create a Case → CaseCard → EligibilityResult → Checklist chain."""
    case = Case(
        source="test",
        source_id=f"CL-{suffix}",
        case_name=f"Checklist Test Case {suffix}",
        issuing_org="Test Org",
        current_lifecycle_stage="checklist_active",
    )
    db.add(case)
    await db.flush()

    card = CaseCard(
        case_id=case.id,
        version=1,
        is_current=True,
        eligibility={"qualification": "一般競争入札"},
        confidence_score=Decimal("0.85"),
    )
    db.add(card)
    await db.flush()

    elig = EligibilityResult(
        case_id=case.id,
        case_card_id=card.id,
        version=1,
        is_current=True,
        verdict="eligible",
        confidence=Decimal("0.90"),
        hard_fail_reasons=[],
        soft_gaps=[],
        check_details={"hard": [], "soft": []},
        company_profile_snapshot={"name": "テスト株式会社"},
    )
    db.add(elig)
    await db.flush()

    items = checklist_items or [
        {"name": "入札書", "category": "bid_time", "source": "spec", "is_checked": False},
        {"name": "封筒", "category": "bid_time", "source": "fixed", "is_checked": False},
        {"name": "納品実績書", "category": "performance_time", "source": "spec", "is_checked": True},
    ]
    checklist = Checklist(
        case_id=case.id,
        case_card_id=card.id,
        eligibility_result_id=elig.id,
        version=1,
        is_current=True,
        checklist_items=items,
        schedule_items=[{"stage": "提出期限", "date": "2026-03-01"}],
        warnings=["リスク: 短納期"],
        progress={"total": 3, "done": 1, "rate": 0.33},
    )
    db.add(checklist)
    await db.flush()
    return case, checklist


@pytest.mark.anyio
class TestGetCurrentChecklist:
    """GET /api/v1/cases/{case_id}/checklist."""

    async def test_returns_current_checklist(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """Returns the current checklist with items and progress."""
        case, cl = await _setup_checklist(db, "current-cl-1")

        resp = await client.get(f"/api/v1/cases/{case.id}/checklist")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == str(cl.id)
        assert len(data["checklist_items"]) == 3
        assert data["progress"]["total"] == 3
        assert data["progress"]["done"] == 1

    async def test_not_found_returns_404(self, client: AsyncClient):
        """Non-existent case_id → 404."""
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/cases/{fake_id}/checklist")
        assert resp.status_code == 404


@pytest.mark.anyio
class TestGetAllChecklists:
    """GET /api/v1/cases/{case_id}/checklists."""

    async def test_returns_all_versions(self, client: AsyncClient, db: AsyncSession):
        """Returns all checklist versions."""
        case, _ = await _setup_checklist(db, "all-cl-1")
        # The _setup_checklist already creates version 1
        resp = await client.get(f"/api/v1/cases/{case.id}/checklists")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1


@pytest.mark.anyio
class TestToggleCheckItem:
    """PATCH /api/v1/checklists/{checklist_id}/items/{item_index}."""

    async def test_check_item(self, client: AsyncClient, db: AsyncSession):
        """Toggle an item to checked."""
        case, cl = await _setup_checklist(db, "toggle-1")

        resp = await client.patch(
            f"/api/v1/checklists/{cl.id}/items/0",
            json={"is_checked": True},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["checklist_items"][0]["is_checked"] is True
        # Progress should update: 2 done out of 3
        assert data["progress"]["done"] == 2
        assert data["progress"]["total"] == 3

    async def test_uncheck_item(self, client: AsyncClient, db: AsyncSession):
        """Toggle item 2 (already checked) to unchecked."""
        case, cl = await _setup_checklist(db, "toggle-2")

        resp = await client.patch(
            f"/api/v1/checklists/{cl.id}/items/2",
            json={"is_checked": False},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["checklist_items"][2]["is_checked"] is False
        assert data["progress"]["done"] == 0

    async def test_invalid_index_returns_404(self, client: AsyncClient, db: AsyncSession):
        """Out-of-range index → 404."""
        case, cl = await _setup_checklist(db, "toggle-3")

        resp = await client.patch(
            f"/api/v1/checklists/{cl.id}/items/99",
            json={"is_checked": True},
        )
        assert resp.status_code == 404

    async def test_checklist_not_found_returns_404(self, client: AsyncClient):
        """Non-existent checklist_id → 404."""
        fake_id = uuid.uuid4()
        resp = await client.patch(
            f"/api/v1/checklists/{fake_id}/items/0",
            json={"is_checked": True},
        )
        assert resp.status_code == 404


@pytest.mark.anyio
class TestAddManualItem:
    """POST /api/v1/checklists/{checklist_id}/items."""

    async def test_add_item(self, client: AsyncClient, db: AsyncSession):
        """Add a manual item to the checklist."""
        case, cl = await _setup_checklist(db, "add-item-1")

        resp = await client.post(
            f"/api/v1/checklists/{cl.id}/items",
            json={"name": "会社概要書", "category": "bid_time"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["checklist_items"]) == 4
        new_item = data["checklist_items"][-1]
        assert new_item["name"] == "会社概要書"
        assert new_item["source"] == "manual"
        assert new_item["is_checked"] is False
        # Progress recalculated
        assert data["progress"]["total"] == 4
