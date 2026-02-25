"""Fixture factories for EligibilityResult model."""

from __future__ import annotations

import uuid
from decimal import Decimal


def make_eligibility_data(
    case_id: uuid.UUID,
    case_card_id: uuid.UUID,
    **overrides,
) -> dict:
    """Return a dict of valid EligibilityResult fields for testing."""
    defaults = {
        "case_id": case_id,
        "case_card_id": case_card_id,
        "verdict": "eligible",
        "confidence": Decimal("0.92"),
        "check_details": {
            "qualification_check": {"result": "pass"},
            "grade_check": {"result": "pass"},
        },
        "company_profile_snapshot": {
            "grade": "D",
            "unified_qualification": True,
            "business_categories": ["物品の販売"],
        },
    }
    defaults.update(overrides)
    return defaults
