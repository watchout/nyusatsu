"""Price analytics service — F-005 TASK-21.

Aggregates base_bids + bid_details to provide price analysis:
- Price distribution (min, Q1, median, Q3, max)
- Participant count analysis
- Single-bidder rate (1社入札率)
- Winning rate distribution
- Quarterly trend analysis
- IQR-based outlier exclusion

Filters: keyword (OR partial match), issuing_org, category, period.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.models.bid_detail import BidDetail

logger = structlog.get_logger()


@dataclass
class PriceFilter:
    """Filter criteria for price analysis."""

    keywords: list[str] | None = None
    """OR partial match on case_name."""

    issuing_org: str | None = None
    """Exact match on issuing_org."""

    category: str | None = None
    """Exact match on category."""

    date_from: date | None = None
    """Opening date lower bound (inclusive)."""

    date_to: date | None = None
    """Opening date upper bound (inclusive)."""


@dataclass
class PriceDistribution:
    """Price distribution statistics."""

    count: int = 0
    min_amount: int | None = None
    q1: int | None = None
    median: int | None = None
    q3: int | None = None
    max_amount: int | None = None
    mean: int | None = None


@dataclass
class ParticipantStats:
    """Participant count statistics."""

    total_bids: int = 0
    avg_participants: float | None = None
    single_bidder_count: int = 0
    single_bidder_rate: float | None = None


@dataclass
class QuarterlyTrend:
    """Quarterly aggregation."""

    quarter: str  # e.g. "2025-Q1"
    count: int = 0
    avg_amount: int | None = None
    avg_participants: float | None = None


@dataclass
class PriceAnalysisResult:
    """Complete price analysis result."""

    filter_applied: PriceFilter = field(default_factory=PriceFilter)
    price_distribution: PriceDistribution = field(default_factory=PriceDistribution)
    participant_stats: ParticipantStats = field(default_factory=ParticipantStats)
    quarterly_trends: list[QuarterlyTrend] = field(default_factory=list)


class PriceAnalyticsService:
    """Service for bid price analysis.

    Usage::

        svc = PriceAnalyticsService()
        result = await svc.analyse(db, PriceFilter(keywords=["保守"]))
    """

    async def analyse(
        self, db: AsyncSession, filter_: PriceFilter | None = None,
    ) -> PriceAnalysisResult:
        """Run full price analysis with the given filter.

        Args:
            db: Async DB session.
            filter_: Optional filter criteria.

        Returns:
            PriceAnalysisResult with distribution, participants, and trends.
        """
        flt = filter_ or PriceFilter()
        result = PriceAnalysisResult(filter_applied=flt)

        result.price_distribution = await self._price_distribution(db, flt)
        result.participant_stats = await self._participant_stats(db, flt)
        result.quarterly_trends = await self._quarterly_trends(db, flt)

        return result

    # ------------------------------------------------------------------
    # Internal queries
    # ------------------------------------------------------------------

    def _base_query_filter(self, flt: PriceFilter) -> list:
        """Build WHERE conditions from filter."""
        conditions = []

        if flt.keywords:
            keyword_conditions = [
                BaseBid.case_name.ilike(f"%{kw}%") for kw in flt.keywords
            ]
            from sqlalchemy import or_
            conditions.append(or_(*keyword_conditions))

        if flt.issuing_org:
            conditions.append(BaseBid.issuing_org == flt.issuing_org)

        if flt.category:
            conditions.append(BaseBid.category == flt.category)

        if flt.date_from:
            conditions.append(BaseBid.opening_date >= flt.date_from)

        if flt.date_to:
            conditions.append(BaseBid.opening_date <= flt.date_to)

        return conditions

    async def _price_distribution(
        self, db: AsyncSession, flt: PriceFilter,
    ) -> PriceDistribution:
        """Calculate price distribution with IQR outlier exclusion."""
        conditions = self._base_query_filter(flt)
        conditions.append(BaseBid.winning_amount.isnot(None))
        conditions.append(BaseBid.winning_amount > 0)

        # First pass: get Q1 and Q3 for IQR
        iqr_stmt = select(
            func.count(BaseBid.winning_amount).label("cnt"),
            func.percentile_cont(0.25).within_group(
                BaseBid.winning_amount,
            ).label("q1"),
            func.percentile_cont(0.75).within_group(
                BaseBid.winning_amount,
            ).label("q3"),
        ).where(*conditions)

        iqr_row = (await db.execute(iqr_stmt)).one()

        if iqr_row.cnt == 0:
            return PriceDistribution()

        q1 = int(iqr_row.q1) if iqr_row.q1 is not None else 0
        q3 = int(iqr_row.q3) if iqr_row.q3 is not None else 0
        iqr = q3 - q1

        # Second pass: with IQR filter (only if enough data)
        iqr_conditions = list(conditions)
        if iqr > 0 and iqr_row.cnt >= 4:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            iqr_conditions.append(BaseBid.winning_amount >= lower)
            iqr_conditions.append(BaseBid.winning_amount <= upper)

        dist_stmt = select(
            func.count(BaseBid.winning_amount).label("cnt"),
            func.min(BaseBid.winning_amount).label("min_amt"),
            func.percentile_cont(0.25).within_group(
                BaseBid.winning_amount,
            ).label("q1"),
            func.percentile_cont(0.5).within_group(
                BaseBid.winning_amount,
            ).label("median"),
            func.percentile_cont(0.75).within_group(
                BaseBid.winning_amount,
            ).label("q3"),
            func.max(BaseBid.winning_amount).label("max_amt"),
            func.avg(BaseBid.winning_amount).label("mean"),
        ).where(*iqr_conditions)

        row = (await db.execute(dist_stmt)).one()

        return PriceDistribution(
            count=row.cnt,
            min_amount=int(row.min_amt) if row.min_amt is not None else None,
            q1=int(row.q1) if row.q1 is not None else None,
            median=int(row.median) if row.median is not None else None,
            q3=int(row.q3) if row.q3 is not None else None,
            max_amount=int(row.max_amt) if row.max_amt is not None else None,
            mean=int(row.mean) if row.mean is not None else None,
        )

    async def _participant_stats(
        self, db: AsyncSession, flt: PriceFilter,
    ) -> ParticipantStats:
        """Calculate participant statistics."""
        conditions = self._base_query_filter(flt)

        stmt = (
            select(
                func.count(BidDetail.id).label("total"),
                func.avg(BidDetail.num_participants).label("avg_p"),
                func.sum(
                    case(
                        (BidDetail.num_participants == 1, 1),
                        else_=0,
                    ),
                ).label("single_count"),
            )
            .select_from(BaseBid)
            .join(BidDetail, BidDetail.base_bid_id == BaseBid.id)
            .where(
                BidDetail.num_participants.isnot(None),
                *conditions,
            )
        )

        row = (await db.execute(stmt)).one()
        total = row.total or 0
        single = row.single_count or 0

        return ParticipantStats(
            total_bids=total,
            avg_participants=round(float(row.avg_p), 2) if row.avg_p else None,
            single_bidder_count=single,
            single_bidder_rate=round(single / total, 4) if total > 0 else None,
        )

    async def _quarterly_trends(
        self, db: AsyncSession, flt: PriceFilter,
    ) -> list[QuarterlyTrend]:
        """Calculate quarterly trends."""
        conditions = self._base_query_filter(flt)
        conditions.append(BaseBid.opening_date.isnot(None))
        conditions.append(BaseBid.winning_amount.isnot(None))
        conditions.append(BaseBid.winning_amount > 0)

        # Use date_trunc for quarterly grouping
        quarter_expr = func.date_trunc("quarter", BaseBid.opening_date)

        stmt = (
            select(
                quarter_expr.label("quarter"),
                func.count(BaseBid.id).label("cnt"),
                func.avg(BaseBid.winning_amount).label("avg_amt"),
            )
            .where(*conditions)
            .group_by(quarter_expr)
            .order_by(quarter_expr)
        )

        rows = (await db.execute(stmt)).all()
        trends = []

        for row in rows:
            q_date = row.quarter
            if q_date is None:
                continue
            month = q_date.month
            quarter_num = (month - 1) // 3 + 1
            quarter_label = f"{q_date.year}-Q{quarter_num}"

            trends.append(
                QuarterlyTrend(
                    quarter=quarter_label,
                    count=row.cnt,
                    avg_amount=int(row.avg_amt) if row.avg_amt else None,
                ),
            )

        return trends
