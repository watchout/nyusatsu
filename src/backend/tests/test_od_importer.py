"""Tests for TASK-16: OD data importer (base_bids UPSERT)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.services.od_import.importer import ODImporter, UpsertAction


def _make_row(**overrides) -> dict:
    """Create a valid parsed row dict."""
    base = {
        "source_id": "OD-TEST-001",
        "case_name": "テスト案件",
        "issuing_org": "テスト省",
        "issuing_org_code": "999",
        "bid_type": "一般競争入札",
        "category": "役務",
        "winning_amount": 10_000_000,
        "winning_bidder": "テスト株式会社",
        "opening_date": date(2025, 4, 1),
        "contract_date": date(2025, 4, 15),
        "detail_url": "https://example.go.jp/detail/test",
        "raw_data": {"案件番号": "OD-TEST-001"},
    }
    base.update(overrides)
    return base


@pytest.mark.anyio
class TestODImporter:
    """Test OD import upsert logic."""

    async def test_insert_new_row(self, db: AsyncSession):
        """New source_id → INSERT."""
        importer = ODImporter()
        data = _make_row(source_id="OD-NEW-001")
        result = await importer.upsert_row(db, data)

        assert result.action == UpsertAction.INSERTED
        assert result.base_bid_id is not None

        # Verify in DB
        bid = (
            await db.execute(
                select(BaseBid).where(BaseBid.source_id == "OD-NEW-001"),
            )
        ).scalar_one()
        assert bid.case_name == "テスト案件"
        assert bid.winning_amount == 10_000_000

    async def test_upsert_newer_date(self, db: AsyncSession):
        """Existing source_id + newer opening_date → UPDATE."""
        importer = ODImporter()

        # Insert initial
        await importer.upsert_row(
            db,
            _make_row(
                source_id="OD-UPD-001",
                opening_date=date(2025, 4, 1),
                case_name="旧案件名",
            ),
        )

        # Update with newer date
        result = await importer.upsert_row(
            db,
            _make_row(
                source_id="OD-UPD-001",
                opening_date=date(2025, 4, 2),
                case_name="新案件名",
            ),
        )

        assert result.action == UpsertAction.UPDATED

        # Verify updated
        bid = (
            await db.execute(
                select(BaseBid).where(BaseBid.source_id == "OD-UPD-001"),
            )
        ).scalar_one()
        assert bid.case_name == "新案件名"
        assert bid.opening_date == date(2025, 4, 2)

    async def test_skip_same_date(self, db: AsyncSession):
        """Existing source_id + same opening_date → SKIP."""
        importer = ODImporter()
        data = _make_row(
            source_id="OD-SKIP-001",
            opening_date=date(2025, 4, 1),
        )

        # Insert initial
        await importer.upsert_row(db, data)

        # Same date → skip
        result = await importer.upsert_row(db, data)

        assert result.action == UpsertAction.SKIPPED

    async def test_upsert_null_dates(self, db: AsyncSession):
        """Existing with no date + new with no date → UPDATE (no date comparison)."""
        importer = ODImporter()

        # Insert with no date
        await importer.upsert_row(
            db,
            _make_row(
                source_id="OD-NODATE-001",
                opening_date=None,
                case_name="元の名前",
            ),
        )

        # Update with no date — new_date is None, so condition new_date and old_date fails → UPDATE
        result = await importer.upsert_row(
            db,
            _make_row(
                source_id="OD-NODATE-001",
                opening_date=None,
                case_name="更新後の名前",
            ),
        )

        assert result.action == UpsertAction.UPDATED

        bid = (
            await db.execute(
                select(BaseBid).where(BaseBid.source_id == "OD-NODATE-001"),
            )
        ).scalar_one()
        assert bid.case_name == "更新後の名前"
