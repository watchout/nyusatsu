"""OD CSV parser — F-005 Layer 1.

Reads a CSV file (UTF-8 / UTF-8 BOM) from the procurement portal,
normalises amounts and dates, and yields (row_dict, error) tuples.

The column mapping is kept in ``COLUMN_MAP`` so it can be adjusted
when the portal changes its schema without touching the rest of the
pipeline.

All original columns are preserved in ``raw_data`` (JSONB) so that
schema changes never lose data.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Column mapping: CSV header → BaseBid field
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    "案件番号": "source_id",
    "案件名称": "case_name",
    "発注機関": "issuing_org",
    "発注機関コード": "issuing_org_code",
    "入札方式": "bid_type",
    "分類": "category",
    "落札金額": "winning_amount",
    "落札者": "winning_bidder",
    "開札日": "opening_date",
    "契約日": "contract_date",
    "公告URL": "detail_url",
}


@dataclass
class ParsedRow:
    """Result of parsing one CSV row."""

    data: dict[str, Any]
    """Normalised dict ready for BaseBid(**data)."""

    raw: dict[str, str]
    """Original CSV row as-is (all string values)."""


@dataclass
class ParseError:
    """Error encountered while parsing a CSV row."""

    row_number: int
    source_id: str | None
    message: str
    raw: dict[str, str]


class ODParser:
    """Parse OD CSV into normalised row dicts.

    Usage::

        parser = ODParser()
        for row_or_error in parser.parse(path_or_text):
            if isinstance(row_or_error, ParseError):
                log_error(row_or_error)
            else:
                upsert(row_or_error.data)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_file(self, path: Path) -> Iterator[ParsedRow | ParseError]:
        """Parse a CSV file on disk."""
        text = path.read_text(encoding="utf-8-sig")  # handles BOM
        yield from self._parse_text(text)

    def parse_text(self, text: str) -> Iterator[ParsedRow | ParseError]:
        """Parse CSV content from a string."""
        yield from self._parse_text(text)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _parse_text(self, text: str) -> Iterator[ParsedRow | ParseError]:
        """Core parsing logic shared by file / text entry points."""
        # Strip BOM if present in text input
        if text.startswith("\ufeff"):
            text = text[1:]

        reader = csv.DictReader(io.StringIO(text))

        for row_num, raw_row in enumerate(reader, start=2):  # row 1 = header
            # Skip completely empty rows.
            # DictReader may produce list values for rows with extra commas;
            # only check str values for emptiness.
            str_values = [
                v for v in raw_row.values() if isinstance(v, str)
            ]
            if not str_values or all(v.strip() == "" for v in str_values):
                continue

            source_id = (raw_row.get("案件番号") or "").strip() or None

            try:
                parsed = self._normalise(raw_row)
            except _RowParseError as exc:
                yield ParseError(
                    row_number=row_num,
                    source_id=source_id,
                    message=str(exc),
                    raw=dict(raw_row),
                )
                continue

            yield ParsedRow(data=parsed, raw=dict(raw_row))

    def _normalise(self, raw: dict[str, str]) -> dict[str, Any]:
        """Map CSV columns → BaseBid fields with type conversion."""
        data: dict[str, Any] = {}

        for csv_col, field_name in COLUMN_MAP.items():
            value = (raw.get(csv_col) or "").strip()

            if field_name == "source_id":
                if not value:
                    raise _RowParseError("source_id (案件番号) is empty")  # noqa: B904
                data[field_name] = value

            elif field_name == "case_name":
                if not value:
                    raise _RowParseError("case_name (案件名称) is empty")  # noqa: B904
                data[field_name] = value

            elif field_name == "issuing_org":
                if not value:
                    raise _RowParseError("issuing_org (発注機関) is empty")  # noqa: B904
                data[field_name] = value

            elif field_name == "winning_amount":
                data[field_name] = self._parse_amount(value)

            elif field_name in ("opening_date", "contract_date"):
                data[field_name] = self._parse_date(value, field_name)

            else:
                data[field_name] = value or None

        # Preserve all original data in raw_data JSONB
        data["raw_data"] = dict(raw)

        return data

    # ------------------------------------------------------------------
    # Type conversions
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_amount(value: str) -> int | None:
        """Parse yen amount string → int, stripping commas and ￥."""
        if not value:
            return None
        cleaned = value.replace(",", "").replace("￥", "").replace("¥", "").strip()
        if not cleaned:
            return None
        try:
            amount = int(cleaned)
        except ValueError:
            raise _RowParseError(f"Invalid amount: {value!r}")  # noqa: B904
        if amount < 0:
            raise _RowParseError(f"Negative amount: {value!r}")  # noqa: B904
        return amount

    @staticmethod
    def _parse_date(value: str, field_name: str) -> date | None:
        """Parse date string (YYYY-MM-DD or YYYY/MM/DD) → date."""
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise _RowParseError(f"Invalid date for {field_name}: {value!r}")  # noqa: B904


class _RowParseError(Exception):
    """Internal: signals a row-level parse failure."""
