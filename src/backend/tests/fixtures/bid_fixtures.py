"""Fixture factories for BaseBid and BidDetail models."""

from __future__ import annotations

import uuid
from decimal import Decimal


def make_base_bid_data(**overrides) -> dict:
    """Return a dict of valid BaseBid fields for testing."""
    defaults = {
        "source_id": f"od-{uuid.uuid4().hex[:8]}",
        "case_name": "テスト落札案件",
        "issuing_org": "テスト省",
        "winning_amount": 500_000,
        "winning_bidder": "テスト株式会社",
    }
    defaults.update(overrides)
    return defaults


def make_bid_detail_data(base_bid_id: uuid.UUID, **overrides) -> dict:
    """Return a dict of valid BidDetail fields for testing."""
    defaults = {
        "base_bid_id": base_bid_id,
        "num_participants": 3,
        "budget_amount": 600_000,
        "winning_rate": Decimal("0.8333"),
    }
    defaults.update(overrides)
    return defaults
