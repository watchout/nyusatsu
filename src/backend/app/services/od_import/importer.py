"""OD data importer — F-005 Layer 1.

Takes parsed rows from ODParser and upserts them into base_bids.
Deduplication is based on source_id (UNIQUE constraint).

Strategy:
- If source_id does not exist → INSERT (new)
- If source_id exists and opening_date is newer → UPDATE (updated)
- If source_id exists and opening_date is same/older → SKIP (unchanged)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid

logger = structlog.get_logger()


class UpsertAction(StrEnum):
    """Result of a single-row upsert operation."""

    INSERTED = "inserted"
    UPDATED = "updated"
    SKIPPED = "skipped"


@dataclass
class UpsertResult:
    """Outcome of upserting a single row."""

    source_id: str
    action: UpsertAction
    base_bid_id: str | None = None
    error: str | None = None


class ODImporter:
    """Upsert parsed OD rows into base_bids.

    Usage::

        importer = ODImporter()
        result = await importer.upsert_row(db, parsed_data)
    """

    async def upsert_row(
        self, db: AsyncSession, data: dict[str, Any],
    ) -> UpsertResult:
        """Insert or update a single base_bid row.

        Args:
            db: Async DB session.
            data: Normalised dict from ODParser (keys match BaseBid columns).

        Returns:
            UpsertResult with the action taken.
        """
        source_id = data["source_id"]

        # Check existing
        stmt = select(BaseBid).where(BaseBid.source_id == source_id)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing is None:
            # INSERT new row
            bid = BaseBid(**data)
            db.add(bid)
            await db.flush()

            logger.debug(
                "od_row_inserted",
                source_id=source_id,
                base_bid_id=str(bid.id),
            )
            return UpsertResult(
                source_id=source_id,
                action=UpsertAction.INSERTED,
                base_bid_id=str(bid.id),
            )

        # Compare opening_date — update only if newer
        new_date = data.get("opening_date")
        old_date = existing.opening_date

        if new_date and old_date and new_date <= old_date:
            # No update needed
            return UpsertResult(
                source_id=source_id,
                action=UpsertAction.SKIPPED,
                base_bid_id=str(existing.id),
            )

        # UPDATE existing row
        for key, value in data.items():
            if key == "source_id":
                continue  # Don't update the unique key
            setattr(existing, key, value)

        await db.flush()

        logger.debug(
            "od_row_updated",
            source_id=source_id,
            base_bid_id=str(existing.id),
        )
        return UpsertResult(
            source_id=source_id,
            action=UpsertAction.UPDATED,
            base_bid_id=str(existing.id),
        )
