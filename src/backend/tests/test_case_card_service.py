"""Tests for CaseCardService (F-002 Chain-3).

Coverage:
- Extract and store case cards
- Retrieve current and historical cards
- Mark cards as reviewed
- Delete cards
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.services.case_card_service import CaseCardService


async def _create_test_case(db: AsyncSession, suffix: str = "001") -> Case:
    """Helper: Create a test case in 'reading_completed' stage."""
    case = Case(
        source="test",
        source_id=f"TEST-{suffix}",
        case_name=f"Test Case {suffix}",
        issuing_org="Test Org",
        current_lifecycle_stage="reading_completed",
    )
    db.add(case)
    await db.flush()
    return case


async def _create_test_card(
    db: AsyncSession,
    case: Case,
    *,
    version: int = 1,
    is_current: bool = True,
) -> CaseCard:
    """Helper: Create a test card."""
    card = CaseCard(
        case_id=case.id,
        version=version,
        is_current=is_current,
        eligibility={"qualification": "一般競争入札"},
        schedule={"deadline": "2026-04-01"},
        business_content={"title": "テスト業務"},
        submission_items=[{"name": "入札書"}],
        risk_factors=[],
        confidence_score=Decimal("0.90"),
        evidence={"qualification": {"quote": "一般競争入札"}},
    )
    db.add(card)
    await db.flush()
    return card


@pytest.mark.anyio
class TestCaseCardServiceGetCurrent:
    """get_current_card() — Retrieve current card."""

    async def test_get_current_card_returns_card(
        self,
        db: AsyncSession,
    ):
        """Returns the current card for a case."""
        case = await _create_test_case(db, "get-current-1")
        card = await _create_test_card(db, case, version=1, is_current=True)
        await db.commit()

        service = CaseCardService(db)
        result = await service.get_current_card(case.id)
        assert result is not None
        assert result.id == card.id
        assert result.version == 1
        assert result.is_current is True

    async def test_get_current_card_skips_non_current(
        self,
        db: AsyncSession,
    ):
        """Skips non-current versions."""
        case = await _create_test_case(db, "get-current-2")
        await _create_test_card(db, case, version=1, is_current=False)
        card_v2 = await _create_test_card(db, case, version=2, is_current=True)
        await db.commit()

        service = CaseCardService(db)
        result = await service.get_current_card(case.id)
        assert result is not None
        assert result.id == card_v2.id
        assert result.version == 2

    async def test_get_current_card_not_found(
        self,
        db: AsyncSession,
    ):
        """Returns None if no card exists."""
        fake_id = uuid.uuid4()
        service = CaseCardService(db)
        result = await service.get_current_card(fake_id)
        assert result is None


@pytest.mark.anyio
class TestCaseCardServiceGetAll:
    """get_all_cards() — Retrieve all versions."""

    async def test_get_all_cards_returns_all_versions(
        self,
        db: AsyncSession,
    ):
        """Returns all card versions ordered by version."""
        case = await _create_test_case(db, "get-all-1")
        card_v1 = await _create_test_card(db, case, version=1, is_current=False)
        card_v2 = await _create_test_card(db, case, version=2, is_current=True)
        await db.commit()

        service = CaseCardService(db)
        result = await service.get_all_cards(case.id)
        assert len(result) == 2
        assert result[0].id == card_v2.id  # Latest first
        assert result[1].id == card_v1.id

    async def test_get_all_cards_empty_list(
        self,
        db: AsyncSession,
    ):
        """Returns empty list if no cards exist."""
        case = await _create_test_case(db, "get-all-2")
        await db.commit()

        service = CaseCardService(db)
        result = await service.get_all_cards(case.id)
        assert result == []


@pytest.mark.anyio
class TestCaseCardServiceMarkReviewed:
    """mark_reviewed() — Mark card as reviewed."""

    async def test_mark_reviewed_sets_timestamp(
        self,
        db: AsyncSession,
    ):
        """Sets reviewed_at and reviewed_by."""
        case = await _create_test_case(db, "mark-reviewed-1")
        card = await _create_test_card(db, case, version=1, is_current=True)
        await db.commit()

        service = CaseCardService(db)
        before = datetime.now(UTC)
        result = await service.mark_reviewed(card.id, reviewed_by="test_user")
        after = datetime.now(UTC)

        assert result.reviewed_by == "test_user"
        assert result.reviewed_at is not None
        assert before <= result.reviewed_at <= after

    async def test_mark_reviewed_default_reviewer(
        self,
        db: AsyncSession,
    ):
        """Uses 'kaneko' as default reviewer."""
        case = await _create_test_case(db, "mark-reviewed-2")
        card = await _create_test_card(db, case, version=1, is_current=True)
        await db.commit()

        service = CaseCardService(db)
        result = await service.mark_reviewed(card.id)
        assert result.reviewed_by == "kaneko"

    async def test_mark_reviewed_card_not_found(
        self,
        db: AsyncSession,
    ):
        """Raises ValueError if card not found."""
        fake_id = uuid.uuid4()
        service = CaseCardService(db)
        with pytest.raises(ValueError, match="not found"):
            await service.mark_reviewed(fake_id)


@pytest.mark.anyio
class TestCaseCardServiceDelete:
    """delete_card() — Delete a card."""

    async def test_delete_card_removes_card(
        self,
        db: AsyncSession,
    ):
        """Removes the card from database."""
        case = await _create_test_case(db, "delete-1")
        card = await _create_test_card(db, case, version=1, is_current=True)
        await db.commit()

        service = CaseCardService(db)
        await service.delete_card(card.id)

        # Verify deletion
        result = await db.get(CaseCard, card.id)
        assert result is None

    async def test_delete_card_not_found(
        self,
        db: AsyncSession,
    ):
        """Raises ValueError if card not found."""
        fake_id = uuid.uuid4()
        service = CaseCardService(db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_card(fake_id)

    async def test_delete_card_preserves_other_versions(
        self,
        db: AsyncSession,
    ):
        """Deleting one version preserves others."""
        case = await _create_test_case(db, "delete-2")
        card_v1 = await _create_test_card(db, case, version=1, is_current=False)
        card_v2 = await _create_test_card(db, case, version=2, is_current=True)
        await db.commit()

        service = CaseCardService(db)
        await service.delete_card(card_v1.id)

        # v2 should still exist
        result = await db.get(CaseCard, card_v2.id)
        assert result is not None
        assert result.version == 2
