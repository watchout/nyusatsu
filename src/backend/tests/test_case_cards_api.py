"""Tests for Wave 7: Case Card API endpoints (F-002)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard


async def _create_case(db: AsyncSession, suffix: str = "001") -> Case:
    case = Case(
        source="test",
        source_id=f"CARD-{suffix}",
        case_name=f"Card Test Case {suffix}",
        issuing_org="Test Org",
        current_lifecycle_stage="reading_completed",
    )
    db.add(case)
    await db.flush()
    return case


async def _create_card(
    db: AsyncSession,
    case: Case,
    *,
    version: int = 1,
    is_current: bool = True,
) -> CaseCard:
    card = CaseCard(
        case_id=case.id,
        version=version,
        is_current=is_current,
        eligibility={"qualification": "一般競争入札"},
        schedule={"deadline": "2026-03-01"},
        business_content={"title": "テスト業務"},
        submission_items=[{"name": "入札書"}],
        risk_factors=[],
        confidence_score=Decimal("0.85"),
        evidence={"qualification": {"quote": "一般競争入札"}},
    )
    db.add(card)
    await db.flush()
    return card


@pytest.mark.anyio
class TestGetCurrentCard:
    """GET /api/v1/cases/{case_id}/card."""

    async def test_returns_current_card(self, client: AsyncClient, db: AsyncSession):
        """Returns the current (is_current=True) card."""
        case = await _create_case(db, "current-1")
        card = await _create_card(db, case, version=1, is_current=True)

        resp = await client.get(f"/api/v1/cases/{case.id}/card")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == str(card.id)
        assert data["case_id"] == str(case.id)
        assert data["version"] == 1
        assert data["is_current"] is True
        assert data["confidence_score"] == 0.85

    async def test_not_found_returns_404(self, client: AsyncClient):
        """Non-existent case_id → 404."""
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/cases/{fake_id}/card")
        assert resp.status_code == 404


@pytest.mark.anyio
class TestGetAllCards:
    """GET /api/v1/cases/{case_id}/cards."""

    async def test_returns_all_versions(self, client: AsyncClient, db: AsyncSession):
        """Returns all card versions for a case."""
        case = await _create_case(db, "all-cards-1")
        await _create_card(db, case, version=1, is_current=False)
        await _create_card(db, case, version=2, is_current=True)

        resp = await client.get(f"/api/v1/cases/{case.id}/cards")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2

    async def test_empty_returns_empty_list(self, client: AsyncClient, db: AsyncSession):
        """Case with no cards returns empty list."""
        case = await _create_case(db, "all-cards-2")
        resp = await client.get(f"/api/v1/cases/{case.id}/cards")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == []
