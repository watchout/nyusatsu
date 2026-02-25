"""Fixture factories for BatchLog model."""

from __future__ import annotations


def make_batch_log_data(**overrides) -> dict:
    """Return a dict of valid BatchLog fields for testing."""
    defaults = {
        "source": "chotatku_portal",
        "feature_origin": "F-001",
        "batch_type": "case_fetch",
    }
    defaults.update(overrides)
    return defaults
