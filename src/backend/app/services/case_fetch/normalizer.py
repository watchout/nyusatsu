"""Case normalizer — F-001.

Converts RawCase → dict[str, Any] ready for Case(**data).
Handles:
- Full-width ↔ half-width character normalisation
- Required field validation
- Diff detection between old and new data
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from app.services.case_fetch.base_adapter import RawCase


@dataclass
class NormalizeResult:
    """Result of normalisation."""

    data: dict[str, Any]
    """Normalised dict ready for Case(**data)."""

    warnings: list[str]
    """Non-fatal issues found during normalisation."""


class CaseNormalizer:
    """Normalise raw case data for storage.

    Usage::

        normalizer = CaseNormalizer()
        result = normalizer.normalise(raw_case)
        if not result.warnings:
            store(result.data)
    """

    def normalise(self, raw: RawCase) -> NormalizeResult:
        """Convert RawCase → normalised dict.

        Args:
            raw: RawCase from a source adapter.

        Returns:
            NormalizeResult with data and any warnings.

        Raises:
            ValueError: If required fields are missing.
        """
        warnings: list[str] = []

        # Required fields validation
        if not raw.source:
            raise ValueError("source is required")
        if not raw.source_id:
            raise ValueError("source_id is required")
        if not raw.case_name:
            raise ValueError("case_name is required")
        if not raw.issuing_org:
            raise ValueError("issuing_org is required")

        data: dict[str, Any] = {
            "source": raw.source,
            "source_id": raw.source_id,
            "case_name": self._normalize_text(raw.case_name),
            "issuing_org": self._normalize_text(raw.issuing_org),
            "current_lifecycle_stage": "discovered",
        }

        # Optional fields — mapped to Case model columns
        if raw.bid_type:
            data["bid_type"] = self._normalize_text(raw.bid_type)
        if raw.region:
            data["region"] = self._normalize_text(raw.region)
        if raw.grade:
            data["grade"] = self._normalize_text(raw.grade)
        if raw.deadline:
            # Case model uses submission_deadline (TIMESTAMP)
            from datetime import datetime, timezone
            data["submission_deadline"] = datetime.combine(
                raw.deadline, datetime.min.time(), tzinfo=timezone.utc,
            )
        if raw.opening_date:
            from datetime import datetime, timezone
            data["opening_date"] = datetime.combine(
                raw.opening_date, datetime.min.time(), tzinfo=timezone.utc,
            )
        if raw.detail_url:
            data["detail_url"] = raw.detail_url

        return NormalizeResult(data=data, warnings=warnings)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalise text: NFKC (full-width → half-width), strip whitespace."""
        normalised = unicodedata.normalize("NFKC", text)
        # Collapse whitespace
        return " ".join(normalised.split())

    @staticmethod
    def detect_diff(
        old: dict[str, Any], new: dict[str, Any],
    ) -> dict[str, tuple[Any, Any]]:
        """Detect differences between old and new case data.

        Args:
            old: Existing case data.
            new: New case data.

        Returns:
            Dict of {field_name: (old_value, new_value)} for changed fields.
        """
        changes: dict[str, tuple[Any, Any]] = {}

        for key in new:
            if key in ("source", "source_id"):
                continue
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                changes[key] = (old_val, new_val)

        return changes
