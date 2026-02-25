"""Fixture factories for Case model."""

from __future__ import annotations

import uuid


def make_case_data(**overrides) -> dict:
    """Return a dict of valid Case fields for testing."""
    defaults = {
        "source": "chotatku_portal",
        "source_id": f"fixture-{uuid.uuid4().hex[:8]}",
        "case_name": "テスト案件：物品の調達",
        "issuing_org": "テスト省大臣官房会計課",
        "category": "物品の販売",
        "region": "関東・甲信越",
        "grade": "D",
    }
    defaults.update(overrides)
    return defaults
