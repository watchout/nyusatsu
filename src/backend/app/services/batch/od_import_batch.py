"""OD import batch runner — F-005 Layer 1.

Orchestrates the full OD import pipeline:
1. Download CSV from URL
2. Parse rows
3. Upsert into base_bids
4. Log summary

Implements BaseBatchRunner for use with BatchRunner.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import (
    BatchConfig,
    BatchItemResult,
    ItemStatus,
)
from app.services.od_import.importer import ODImporter, UpsertAction
from app.services.od_import.parser import ODParser, ParsedRow, ParseError

logger = structlog.get_logger()


class ODImportBatch(BaseBatchRunner):
    """Batch runner for OD CSV import into base_bids.

    This runner takes pre-parsed rows (ParsedRow | ParseError) as items.
    The download + parse step is done in on_batch_start() so that the
    BatchRunner can manage each row individually.

    Args:
        csv_text: Raw CSV text content to parse and import.
        sha256: Hash of the original downloaded file (for logging).
    """

    def __init__(self, csv_text: str, sha256: str = "") -> None:
        self._csv_text = csv_text
        self._sha256 = sha256
        self._parser = ODParser()
        self._importer = ODImporter()
        self._items: list[ParsedRow | ParseError] = []
        self._start_time: float = 0.0

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="open_data",
            batch_type="od_import",
            feature_origin="F-005",
        )

    async def on_batch_start(self) -> None:
        """Parse CSV into rows before processing."""
        self._start_time = time.monotonic()
        self._items = list(self._parser.parse_text(self._csv_text))

        logger.info(
            "od_import_parsed",
            total_rows=len(self._items),
            parse_errors=sum(
                1 for item in self._items if isinstance(item, ParseError)
            ),
        )

    async def fetch_items(
        self, db: AsyncSession,
    ) -> AsyncIterator[ParsedRow | ParseError]:
        """Yield parsed rows (and parse errors as items)."""
        for item in self._items:
            yield item

    async def process_item(
        self, db: AsyncSession, item: Any,
    ) -> BatchItemResult:
        """Process a single parsed row or parse error."""
        if isinstance(item, ParseError):
            return BatchItemResult(
                item_id=item.source_id or f"row-{item.row_number}",
                status=ItemStatus.FAILED,
                error_message=f"Parse error at row {item.row_number}: {item.message}",
                error_details={
                    "row_number": item.row_number,
                    "raw": item.raw,
                },
            )

        # item is ParsedRow
        result = await self._importer.upsert_row(db, item.data)

        if result.action == UpsertAction.INSERTED:
            return BatchItemResult(
                item_id=result.source_id,
                status=ItemStatus.SUCCESS,
            )
        elif result.action == UpsertAction.UPDATED:
            return BatchItemResult(
                item_id=result.source_id,
                status=ItemStatus.SUCCESS,
            )
        else:  # SKIPPED
            return BatchItemResult(
                item_id=result.source_id,
                status=ItemStatus.SKIPPED,
            )

    async def on_batch_end(self) -> None:
        """Log import summary."""
        duration = time.monotonic() - self._start_time if self._start_time else 0
        logger.info(
            "od_import_summary",
            total_rows=len(self._items),
            file_hash_sha256=self._sha256,
            duration_sec=round(duration, 2),
        )
