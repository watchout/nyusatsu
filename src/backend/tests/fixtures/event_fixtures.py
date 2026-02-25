"""Fixture factories for CaseEvent model."""

from __future__ import annotations

import uuid


def make_event_data(case_id: uuid.UUID, **overrides) -> dict:
    """Return a dict of valid CaseEvent fields for testing."""
    defaults = {
        "case_id": case_id,
        "event_type": "case_discovered",
        "to_status": "discovered",
        "triggered_by": "batch",
        "feature_origin": "F-001",
    }
    defaults.update(overrides)
    return defaults
