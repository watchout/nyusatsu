"""Fixture factories for CaseCard model."""

from __future__ import annotations

import uuid


def make_case_card_data(case_id: uuid.UUID, **overrides) -> dict:
    """Return a dict of valid CaseCard fields for testing."""
    defaults = {
        "case_id": case_id,
        "status": "completed",
        "extraction_method": "text",
        "is_scanned": False,
        "eligibility": {"qualification": "全省庁統一資格", "grade": "D"},
        "schedule": {"submission_deadline": "2026-03-15T17:00:00+09:00"},
        "business_content": {"summary": "テスト業務"},
    }
    defaults.update(overrides)
    return defaults
