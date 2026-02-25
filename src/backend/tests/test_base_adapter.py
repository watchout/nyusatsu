"""Tests for TASK-18: BaseSourceAdapter store logic."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.services.case_fetch.base_adapter import (
    BaseSourceAdapter,
    RawCase,
    StoreAction,
)


class _TestAdapter(BaseSourceAdapter):
    """Minimal adapter for testing store()."""

    @property
    def source_name(self) -> str:
        return "test_adapter"

    async def fetch(self) -> list[RawCase]:
        return []


def _make_case_data(**overrides) -> dict:
    """Create valid normalised case data."""
    base = {
        "source": "test_adapter",
        "source_id": "TEST-001",
        "case_name": "テスト案件",
        "issuing_org": "テスト省",
        "current_lifecycle_stage": "discovered",
    }
    base.update(overrides)
    return base


@pytest.mark.anyio
class TestBaseAdapterStore:
    """Test UPSERT logic via BaseSourceAdapter.store()."""

    async def test_insert_new_case(self, db: AsyncSession):
        """New (source, source_id) → INSERT."""
        adapter = _TestAdapter()
        data = _make_case_data(source_id="NEW-001")
        result = await adapter.store(db, data)

        assert result.action == StoreAction.INSERTED
        assert result.case_id is not None

        case = (
            await db.execute(
                select(Case).where(
                    Case.source == "test_adapter",
                    Case.source_id == "NEW-001",
                ),
            )
        ).scalar_one()
        assert case.case_name == "テスト案件"

    async def test_upsert_with_name_change(self, db: AsyncSession):
        """Same (source, source_id) + different case_name → UPDATE."""
        adapter = _TestAdapter()

        # Insert initial
        await adapter.store(
            db,
            _make_case_data(source_id="UPD-001", case_name="旧名称"),
        )

        # Update with new name
        result = await adapter.store(
            db,
            _make_case_data(source_id="UPD-001", case_name="新名称"),
        )

        assert result.action == StoreAction.UPDATED

        case = (
            await db.execute(
                select(Case).where(Case.source_id == "UPD-001"),
            )
        ).scalar_one()
        assert case.case_name == "新名称"

    async def test_skip_unchanged(self, db: AsyncSession):
        """Same (source, source_id) + same data → SKIP."""
        adapter = _TestAdapter()
        data = _make_case_data(source_id="SKIP-001")

        await adapter.store(db, data)
        result = await adapter.store(db, data)

        assert result.action == StoreAction.SKIPPED
