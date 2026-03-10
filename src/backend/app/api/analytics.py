"""Price Analytics API endpoint — SSOT-3 §4-9.

GET /api/v1/analytics/price-summary — price analysis with filters.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analytics import (
    AmountStats,
    ParticipantsStats,
    PeriodRange,
    PriceSummaryResponse,
    TrendByQuarter,
)
from app.schemas.envelope import SuccessResponse
from app.services.analytics.price_service import PriceAnalyticsService, PriceFilter

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_svc = PriceAnalyticsService()


@router.get("/price-summary", response_model=SuccessResponse)
async def get_price_summary(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    keyword: str | None = Query(None, description="Case name keyword"),  # noqa: B008
    issuing_org: str | None = Query(None, description="Issuing org filter"),  # noqa: B008
    category: str | None = Query(None, description="Category filter"),  # noqa: B008
    period_months: int = Query(36, ge=1, le=120, description="Period in months"),  # noqa: B008
) -> SuccessResponse:
    """価格分析サマリ (§4-9)."""
    today = date.today()
    # Approximate months → days (30.44 days/month)
    date_from = today - timedelta(days=int(period_months * 30.44))

    pf = PriceFilter(
        keywords=keyword.split() if keyword else None,
        issuing_org=issuing_org,
        category=category,
        date_from=date_from,
        date_to=today,
    )

    result = await _svc.analyse(db, pf)
    dist = result.price_distribution
    parts = result.participant_stats

    response_data = PriceSummaryResponse(
        total_records=dist.count,
        period=PeriodRange(
            from_date=date_from.isoformat(),
            to_date=today.isoformat(),
        ),
        amount_stats=AmountStats(
            median=dist.median,
            q1=dist.q1,
            q3=dist.q3,
            mean=dist.mean,
            min=dist.min_amount,
            max=dist.max_amount,
        ),
        participants_stats=ParticipantsStats(
            median=None,  # PriceAnalyticsService doesn't compute median participants
            mean=parts.avg_participants,
            single_bid_rate=parts.single_bidder_rate,
        ),
        winning_rate_by_amount=[],  # Phase2: requires more complex analysis
        trend_by_quarter=[
            TrendByQuarter(
                quarter=t.quarter,
                median_amount=t.avg_amount,
                avg_participants=t.avg_participants,
            )
            for t in result.quarterly_trends
        ],
    )

    return SuccessResponse(data=response_data.model_dump(mode="json"))
