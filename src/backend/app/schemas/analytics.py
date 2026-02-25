"""Price analytics response schemas — SSOT-3 §4-9.

Pydantic models for GET /analytics/price-summary.
"""

from __future__ import annotations

from pydantic import BaseModel


class AmountStats(BaseModel):
    """Price distribution statistics."""

    median: int | None = None
    q1: int | None = None
    q3: int | None = None
    mean: int | None = None
    min: int | None = None
    max: int | None = None


class ParticipantsStats(BaseModel):
    """Participant count statistics."""

    median: float | None = None
    mean: float | None = None
    single_bid_rate: float | None = None


class WinningRateByAmount(BaseModel):
    """Winning rate for a price range."""

    range: str
    win_rate: float


class TrendByQuarter(BaseModel):
    """Quarterly trend data point."""

    quarter: str
    median_amount: int | None = None
    avg_participants: float | None = None


class PeriodRange(BaseModel):
    """Analysis period."""

    from_date: str
    to_date: str


class PriceSummaryResponse(BaseModel):
    """GET /analytics/price-summary response (§4-9)."""

    total_records: int
    period: PeriodRange
    amount_stats: AmountStats
    participants_stats: ParticipantsStats
    winning_rate_by_amount: list[WinningRateByAmount]
    trend_by_quarter: list[TrendByQuarter]
