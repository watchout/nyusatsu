"""Tests for Wave 7: Eligibility API endpoints (F-003)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.eligibility_result import EligibilityResult


async def _create_case(db: AsyncSession, suffix: str = "001") -> Case:
    case = Case(
        source="test",
        source_id=f"ELIG-{suffix}",
        case_name=f"Eligibility Test Case {suffix}",
        issuing_org="Test Org",
        current_lifecycle_stage="judging_completed",
    )
    db.add(case)
    await db.flush()
    return case


async def _create_card(db: AsyncSession, case: Case) -> CaseCard:
    card = CaseCard(
        case_id=case.id,
        version=1,
        is_current=True,
        eligibility={"qualification": "一般競争入札"},
        confidence_score=Decimal("0.85"),
    )
    db.add(card)
    await db.flush()
    return card


async def _create_eligibility(
    db: AsyncSession,
    case: Case,
    card: CaseCard,
    *,
    version: int = 1,
    is_current: bool = True,
    verdict: str = "eligible",
) -> EligibilityResult:
    elig = EligibilityResult(
        case_id=case.id,
        case_card_id=card.id,
        version=version,
        is_current=is_current,
        verdict=verdict,
        confidence=Decimal("0.90"),
        hard_fail_reasons=[],
        soft_gaps=[],
        check_details={"hard": [], "soft": []},
        company_profile_snapshot={"name": "テスト株式会社"},
    )
    db.add(elig)
    await db.flush()
    return elig


@pytest.mark.anyio
class TestGetCurrentEligibility:
    """GET /api/v1/cases/{case_id}/eligibility."""

    async def test_returns_current_eligibility(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """Returns the current eligibility result."""
        case = await _create_case(db, "current-e-1")
        card = await _create_card(db, case)
        elig = await _create_eligibility(db, case, card)

        resp = await client.get(f"/api/v1/cases/{case.id}/eligibility")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == str(elig.id)
        assert data["verdict"] == "eligible"
        assert data["confidence"] == 0.90

    async def test_not_found_returns_404(self, client: AsyncClient):
        """Non-existent case_id → 404."""
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/cases/{fake_id}/eligibility")
        assert resp.status_code == 404


@pytest.mark.anyio
class TestGetAllEligibilities:
    """GET /api/v1/cases/{case_id}/eligibilities."""

    async def test_returns_all_versions(self, client: AsyncClient, db: AsyncSession):
        """Returns all eligibility versions for a case."""
        case = await _create_case(db, "all-elig-1")
        card = await _create_card(db, case)
        await _create_eligibility(db, case, card, version=1, is_current=False)
        await _create_eligibility(db, case, card, version=2, is_current=True)

        resp = await client.get(f"/api/v1/cases/{case.id}/eligibilities")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
