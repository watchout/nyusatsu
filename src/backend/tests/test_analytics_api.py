"""Tests for Analytics API — TASK-37.

Tests GET /api/v1/analytics/price-summary.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.models.bid_detail import BidDetail


async def _create_bid(
    db: AsyncSession,
    *,
    case_name: str = "テスト業務",
    issuing_org: str = "○○省",
    category: str = "役務の提供",
    winning_amount: int = 1_000_000,
    opening_date: date | None = None,
    num_participants: int = 3,
) -> BaseBid:
    bid = BaseBid(
        id=uuid.uuid4(),
        source_id=f"BID-{uuid.uuid4().hex[:8]}",
        case_name=case_name,
        issuing_org=issuing_org,
        category=category,
        winning_amount=winning_amount,
        opening_date=opening_date or date(2025, 6, 15),
    )
    db.add(bid)
    await db.flush()

    detail = BidDetail(
        id=uuid.uuid4(),
        base_bid_id=bid.id,
        num_participants=num_participants,
    )
    db.add(detail)
    await db.flush()
    return bid


@pytest.mark.anyio
class TestPriceSummary:
    """GET /api/v1/analytics/price-summary."""

    async def test_empty_returns_zero_records(self, client: AsyncClient) -> None:
        """No bid data returns total_records=0."""
        resp = await client.get("/api/v1/analytics/price-summary")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["total_records"] == 0

    async def test_with_bids(self, client: AsyncClient, db: AsyncSession) -> None:
        """Returns price distribution from bid data."""
        await _create_bid(db, winning_amount=500_000)
        await _create_bid(db, winning_amount=1_500_000)
        await _create_bid(db, winning_amount=2_000_000)

        resp = await client.get("/api/v1/analytics/price-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_records"] == 3
        assert data["amount_stats"]["min"] is not None
        assert data["amount_stats"]["max"] is not None

    async def test_filter_by_category(self, client: AsyncClient, db: AsyncSession) -> None:
        """Category filter narrows results."""
        await _create_bid(db, category="役務の提供", winning_amount=1_000_000)
        await _create_bid(db, category="物品の販売", winning_amount=2_000_000)

        resp = await client.get("/api/v1/analytics/price-summary?category=役務の提供")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_records"] == 1
