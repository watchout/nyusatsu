"""Fixture factories for Checklist model."""

from __future__ import annotations

import uuid


def make_checklist_data(
    case_id: uuid.UUID,
    case_card_id: uuid.UUID,
    eligibility_result_id: uuid.UUID,
    **overrides,
) -> dict:
    """Return a dict of valid Checklist fields for testing."""
    defaults = {
        "case_id": case_id,
        "case_card_id": case_card_id,
        "eligibility_result_id": eligibility_result_id,
        "checklist_items": [
            {"label": "入札書作成", "done": False, "category": "書類"},
            {"label": "仕様書確認", "done": False, "category": "確認"},
        ],
        "schedule_items": [
            {"date": "2026-03-10", "task": "入札書提出締切"},
        ],
    }
    defaults.update(overrides)
    return defaults
