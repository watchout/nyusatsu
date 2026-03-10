"""Case scorer — F-001 TASK-19.

4-factor scoring model:
1. competition (30pts) — fewer participants = higher score (from F-005 bid_details)
2. scale (25pts) — winning_amount bracket match (from F-005 base_bids)
3. deadline (25pts) — closer deadline = higher urgency score
4. domain_fit (20pts) — keyword match against company profile

When F-005 data is unavailable, default mid-range values are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.models.bid_detail import BidDetail
from app.models.case import Case

logger = structlog.get_logger()


@dataclass
class ScoreBreakdown:
    """Breakdown of the 4-factor score."""

    competition: int = 0
    """Competition factor (0-30). Fewer participants = higher."""

    scale: int = 0
    """Scale factor (0-25). Amount bracket match."""

    deadline: int = 0
    """Deadline factor (0-25). Closer = higher urgency."""

    domain_fit: int = 0
    """Domain fit factor (0-20). Keyword match."""

    @property
    def total(self) -> int:
        """Total score (0-100)."""
        return self.competition + self.scale + self.deadline + self.domain_fit


# Default scores when data is unavailable
_DEFAULT_COMPETITION = 15  # mid-range
_DEFAULT_SCALE = 13        # mid-range
_DEFAULT_DOMAIN_FIT = 10   # mid-range


class CaseScorer:
    """Score cases using the 4-factor model.

    Args:
        target_keywords: Keywords indicating domain fit
            (from company profile or config).
    """

    def __init__(
        self,
        target_keywords: list[str] | None = None,
    ) -> None:
        self._target_keywords = target_keywords or []

    async def score(
        self, db: AsyncSession, case: Case,
    ) -> ScoreBreakdown:
        """Score a single case.

        Args:
            db: Async DB session.
            case: Case to score.

        Returns:
            ScoreBreakdown with per-factor scores.
        """
        competition = await self._score_competition(db, case)
        scale = await self._score_scale(db, case)
        deadline = self._score_deadline(case)
        domain_fit = self._score_domain_fit(case)

        breakdown = ScoreBreakdown(
            competition=competition,
            scale=scale,
            deadline=deadline,
            domain_fit=domain_fit,
        )

        logger.debug(
            "case_scored",
            case_id=str(case.id),
            total=breakdown.total,
            competition=competition,
            scale=scale,
            deadline=deadline,
            domain_fit=domain_fit,
        )

        return breakdown

    # ------------------------------------------------------------------
    # Factor scoring
    # ------------------------------------------------------------------

    async def _score_competition(
        self, db: AsyncSession, case: Case,
    ) -> int:
        """Score based on avg participant count for similar org.

        Fewer avg participants = less competition = higher score.
        """
        if not case.issuing_org:
            return _DEFAULT_COMPETITION

        # Query avg participants for cases from same org
        stmt = (
            select(func.avg(BidDetail.num_participants))
            .select_from(BaseBid)
            .join(BidDetail, BidDetail.base_bid_id == BaseBid.id)
            .where(
                BaseBid.issuing_org == case.issuing_org,
                BidDetail.num_participants.isnot(None),
            )
        )
        avg_p = (await db.execute(stmt)).scalar_one_or_none()

        if avg_p is None:
            return _DEFAULT_COMPETITION

        avg_p = float(avg_p)
        # Scale: 1 participant → 30, 10+ participants → 0
        if avg_p <= 1:
            return 30
        if avg_p >= 10:
            return 0
        return max(0, int(30 - (avg_p - 1) * (30 / 9)))

    async def _score_scale(
        self, db: AsyncSession, case: Case,
    ) -> int:
        """Score based on typical winning amount for similar org.

        Mid-range amounts score highest (sweet spot).
        """
        if not case.issuing_org:
            return _DEFAULT_SCALE

        # Query median winning amount for same org
        stmt = (
            select(func.percentile_cont(0.5).within_group(BaseBid.winning_amount))
            .where(
                BaseBid.issuing_org == case.issuing_org,
                BaseBid.winning_amount.isnot(None),
                BaseBid.winning_amount > 0,
            )
        )
        median = (await db.execute(stmt)).scalar_one_or_none()

        if median is None:
            return _DEFAULT_SCALE

        median = float(median)
        # Sweet spot: 5M-50M → max score, outside → lower
        if 5_000_000 <= median <= 50_000_000:
            return 25
        elif 1_000_000 <= median < 5_000_000 or 50_000_000 < median <= 100_000_000:
            return 18
        elif median > 100_000_000:
            return 8
        else:  # < 1M
            return 10

    @staticmethod
    def _score_deadline(case: Case) -> int:
        """Score based on deadline proximity.

        Closer deadline = more urgent = higher score.
        """
        if not case.submission_deadline:
            return 13  # mid-range default

        now = datetime.now(UTC)
        diff = (case.submission_deadline - now).days

        if diff < 0:
            return 0  # Already passed
        if diff <= 7:
            return 25  # Very urgent
        if diff <= 14:
            return 20
        if diff <= 30:
            return 15
        if diff <= 60:
            return 10
        return 5  # Far future

    def _score_domain_fit(self, case: Case) -> int:
        """Score based on keyword match with target keywords."""
        if not self._target_keywords:
            return _DEFAULT_DOMAIN_FIT

        case_text = (case.case_name or "").lower()
        matches = sum(
            1 for kw in self._target_keywords
            if kw.lower() in case_text
        )

        if matches == 0:
            return 0
        if matches == 1:
            return 10
        if matches == 2:
            return 16
        return 20  # 3+
