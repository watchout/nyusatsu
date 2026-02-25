"""JSON response parser for F-002 Stage 2.

Parses raw LLM JSON output into validated CaseCardExtraction.
"""

from __future__ import annotations

import json
import re

import structlog
from pydantic import ValidationError

from app.schemas.extraction import CaseCardExtraction

logger = structlog.get_logger()


class ParseError(Exception):
    """Raised when LLM response cannot be parsed as valid JSON."""


class ResponseParser:
    """Parse and validate LLM JSON output."""

    def parse(self, raw_text: str) -> CaseCardExtraction:
        """Parse raw LLM text into CaseCardExtraction.

        Handles:
        - JSON wrapped in markdown code blocks
        - Invalid assertion_type values (falls back to "inferred")

        Raises:
            ParseError: If the text cannot be parsed as valid JSON.
        """
        cleaned = self._extract_json(raw_text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise ParseError(f"Expected JSON object, got {type(data).__name__}")

        # Fix invalid assertion_type values before validation
        data = self._fix_assertion_types(data)

        try:
            return CaseCardExtraction.model_validate(data)
        except ValidationError as exc:
            raise ParseError(f"Validation error: {exc}") from exc

    @staticmethod
    def _extract_json(raw_text: str) -> str:
        """Extract JSON from potential markdown code blocks."""
        raw_text = raw_text.strip()

        # Try to extract from ```json ... ``` blocks
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw_text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If text starts with { or [, use as-is
        if raw_text.startswith("{") or raw_text.startswith("["):
            return raw_text

        # Last resort: find first { to last }
        first_brace = raw_text.find("{")
        last_brace = raw_text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            return raw_text[first_brace : last_brace + 1]

        return raw_text

    def _fix_assertion_types(self, data: dict) -> dict:
        """Fix invalid assertion_type values by replacing with 'inferred'."""
        valid_values = {"fact", "inferred", "caution"}

        def _fix_in_obj(obj: dict | list) -> dict | list:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "assertion_type" and isinstance(value, str):
                        if value not in valid_values:
                            logger.warning(
                                "invalid_assertion_type_fixed",
                                original=value,
                                fixed="inferred",
                            )
                            obj[key] = "inferred"
                    elif isinstance(value, (dict, list)):
                        _fix_in_obj(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        _fix_in_obj(item)
            return obj

        return _fix_in_obj(data)
