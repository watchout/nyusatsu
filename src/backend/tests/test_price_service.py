"""Tests for TASK-21: Price analytics service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.models.bid_detail import BidDetail
from app.services.analytics.price_service import (
    PriceAnalyticsService,
    PriceFilter,
)


async def _seed_bids(db: AsyncSession) -> list[BaseBid]:
    """Seed test data: 5 base_bids with bid_details."""
    bids = []
    data_set = [
        {
            "source_id": "PRICE-001",
            "case_name": "サーバー保守業務",
            "issuing_org": "防衛省",
            "category": "役務",
            "winning_amount": 15_000_000,
            "opening_date": date(2025, 1, 15),
            "detail_url": "https://example.go.jp/1",
        },
        {
            "source_id": "PRICE-002",
            "case_name": "ネットワーク構築業務",
            "issuing_org": "総務省",
            "category": "役務",
            "winning_amount": 28_000_000,
            "opening_date": date(2025, 2, 20),
            "detail_url": "https://example.go.jp/2",
        },
        {
            "source_id": "PRICE-003",
            "case_name": "事務用品購入",
            "issuing_org": "防衛省",
            "category": "物品",
            "winning_amount": 500_000,
            "opening_date": date(2025, 4, 10),
            "detail_url": "https://example.go.jp/3",
        },
        {
            "source_id": "PRICE-004",
            "case_name": "清掃業務委託",
            "issuing_org": "厚生労働省",
            "category": "役務",
            "winning_amount": 8_500_000,
            "opening_date": date(2025, 5, 1),
            "detail_url": "https://example.go.jp/4",
        },
        {
            "source_id": "PRICE-005",
            "case_name": "サーバー移行業務",
            "issuing_org": "防衛省",
            "category": "役務",
            "winning_amount": 45_000_000,
            "opening_date": date(2025, 7, 1),
            "detail_url": "https://example.go.jp/5",
        },
    ]

    details_data = [
        {"num_participants": 5, "budget_amount": 20_000_000, "winning_rate": Decimal("0.7500")},
        {"num_participants": 3, "budget_amount": 35_000_000, "winning_rate": Decimal("0.8000")},
        {"num_participants": 1, "budget_amount": None, "winning_rate": None},
        {"num_participants": 4, "budget_amount": 10_000_000, "winning_rate": Decimal("0.8500")},
        {"num_participants": 2, "budget_amount": 50_000_000, "winning_rate": Decimal("0.9000")},
    ]

    for bid_data, det_data in zip(data_set, details_data, strict=False):
        bid = BaseBid(**bid_data)
        db.add(bid)
        await db.flush()

        detail = BidDetail(base_bid_id=bid.id, **det_data)
        db.add(detail)
        bids.append(bid)

    await db.flush()
    return bids


@pytest.mark.anyio
class TestPriceAnalyticsService:
    """Test price analysis aggregation."""

    async def test_full_analysis(self, db: AsyncSession):
        """Full analysis with no filter → aggregates all bids."""
        await _seed_bids(db)
        svc = PriceAnalyticsService()
        result = await svc.analyse(db)

        dist = result.price_distribution
        assert dist.count == 5
        assert dist.min_amount is not None
        assert dist.max_amount is not None
        assert dist.median is not None

    async def test_keyword_filter(self, db: AsyncSession):
        """Keyword filter → OR partial match on case_name."""
        await _seed_bids(db)
        svc = PriceAnalyticsService()
        result = await svc.analyse(
            db,
            PriceFilter(keywords=["サーバー"]),
        )

        # "サーバー保守業務" and "サーバー移行業務"
        dist = result.price_distribution
        assert dist.count == 2

    async def test_org_filter(self, db: AsyncSession):
        """Org filter → exact match."""
        await _seed_bids(db)
        svc = PriceAnalyticsService()
        result = await svc.analyse(
            db,
            PriceFilter(issuing_org="防衛省"),
        )

        dist = result.price_distribution
        assert dist.count == 3  # PRICE-001, 003, 005

    async def test_category_filter(self, db: AsyncSession):
        """Category filter."""
        await _seed_bids(db)
        svc = PriceAnalyticsService()
        result = await svc.analyse(
            db,
            PriceFilter(category="物品"),
        )

        dist = result.price_distribution
        assert dist.count == 1

    async def test_date_range_filter(self, db: AsyncSession):
        """Date range filter."""
        await _seed_bids(db)
        svc = PriceAnalyticsService()
        result = await svc.analyse(
            db,
            PriceFilter(
                date_from=date(2025, 4, 1),
                date_to=date(2025, 6, 30),
            ),
        )

        dist = result.price_distribution
        assert dist.count == 2  # PRICE-003 (Apr), PRICE-004 (May)

    async def test_participant_stats(self, db: AsyncSession):
        """Participant stats include single-bidder rate."""
        await _seed_bids(db)
        svc = PriceAnalyticsService()
        result = await svc.analyse(db)

        stats = result.participant_stats
        assert stats.total_bids == 5
        assert stats.single_bidder_count == 1  # PRICE-003
        assert stats.single_bidder_rate is not None
        assert stats.avg_participants is not None

    async def test_empty_data(self, db: AsyncSession):
        """No data → zero counts."""
        svc = PriceAnalyticsService()
        result = await svc.analyse(db)

        assert result.price_distribution.count == 0
        assert result.participant_stats.total_bids == 0
        assert result.quarterly_trends == []
