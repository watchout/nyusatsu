"""Tests for TASK-19: Case scorer (4-factor model)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.models.bid_detail import BidDetail
from app.models.case import Case
from app.services.case_fetch.scorer import CaseScorer, ScoreBreakdown


async def _create_case(
    db: AsyncSession,
    suffix: str = "001",
    issuing_org: str = "防衛省",
    case_name: str = "テスト案件",
    deadline_days: int | None = 10,
) -> Case:
    """Create a test case."""
    deadline = (
        datetime.now(timezone.utc) + timedelta(days=deadline_days)
        if deadline_days is not None
        else None
    )
    case = Case(
        source="test",
        source_id=f"SCORE-{suffix}",
        case_name=case_name,
        issuing_org=issuing_org,
        submission_deadline=deadline,
    )
    db.add(case)
    await db.flush()
    return case


async def _seed_bid_data(
    db: AsyncSession,
    org: str = "防衛省",
    num_participants: int = 5,
    winning_amount: int = 20_000_000,
) -> None:
    """Seed F-005 bid data for scoring reference."""
    bid = BaseBid(
        source_id=f"BID-{org}-{num_participants}",
        case_name="参照データ",
        issuing_org=org,
        winning_amount=winning_amount,
        opening_date=date(2025, 1, 1),
    )
    db.add(bid)
    await db.flush()

    detail = BidDetail(
        base_bid_id=bid.id,
        num_participants=num_participants,
        budget_amount=winning_amount + 5_000_000,
    )
    db.add(detail)
    await db.flush()


@pytest.mark.anyio
class TestCaseScorer:
    """Test 4-factor scoring."""

    async def test_score_with_all_data(self, db: AsyncSession):
        """All F-005 data available → specific scores."""
        await _seed_bid_data(db, org="防衛省", num_participants=3, winning_amount=20_000_000)
        case = await _create_case(db, "all-data", issuing_org="防衛省", deadline_days=10)

        scorer = CaseScorer(target_keywords=["テスト"])
        breakdown = await scorer.score(db, case)

        assert 0 <= breakdown.competition <= 30
        assert 0 <= breakdown.scale <= 25
        assert 0 <= breakdown.deadline <= 25
        assert 0 <= breakdown.domain_fit <= 20
        assert 0 <= breakdown.total <= 100

    async def test_score_without_data(self, db: AsyncSession):
        """No F-005 data → default mid-range scores."""
        case = await _create_case(db, "no-data", issuing_org="データなし省")

        scorer = CaseScorer()
        breakdown = await scorer.score(db, case)

        # Defaults should give mid-range
        assert breakdown.competition == 15  # default
        assert breakdown.scale == 13  # default
        assert breakdown.total > 0

    async def test_competition_low_participants(self, db: AsyncSession):
        """Few avg participants → high competition score."""
        await _seed_bid_data(db, org="少数省", num_participants=2)
        case = await _create_case(db, "low-comp", issuing_org="少数省")

        scorer = CaseScorer()
        breakdown = await scorer.score(db, case)

        assert breakdown.competition > 20  # Should be high

    async def test_competition_many_participants(self, db: AsyncSession):
        """Many avg participants → low competition score."""
        await _seed_bid_data(db, org="多数省", num_participants=10)
        case = await _create_case(db, "high-comp", issuing_org="多数省")

        scorer = CaseScorer()
        breakdown = await scorer.score(db, case)

        assert breakdown.competition <= 5  # Should be low

    async def test_deadline_urgent(self, db: AsyncSession):
        """Deadline within 7 days → max urgency score."""
        case = await _create_case(db, "urgent", deadline_days=3)

        scorer = CaseScorer()
        breakdown = await scorer.score(db, case)

        assert breakdown.deadline == 25

    async def test_deadline_far(self, db: AsyncSession):
        """Deadline > 60 days → low urgency score."""
        case = await _create_case(db, "far", deadline_days=90)

        scorer = CaseScorer()
        breakdown = await scorer.score(db, case)

        assert breakdown.deadline == 5

    async def test_domain_fit_keywords(self, db: AsyncSession):
        """Keyword match → domain fit score."""
        case = await _create_case(
            db, "fit", case_name="サーバー保守業務",
        )

        scorer_match = CaseScorer(target_keywords=["サーバー", "保守"])
        breakdown = await scorer_match.score(db, case)
        assert breakdown.domain_fit == 16  # 2 matches

        scorer_no_match = CaseScorer(target_keywords=["建設", "土木"])
        breakdown2 = await scorer_no_match.score(db, case)
        assert breakdown2.domain_fit == 0  # 0 matches

    async def test_score_breakdown_total(self, db: AsyncSession):
        """Total is sum of all factors."""
        breakdown = ScoreBreakdown(
            competition=20, scale=15, deadline=10, domain_fit=12,
        )
        assert breakdown.total == 57
