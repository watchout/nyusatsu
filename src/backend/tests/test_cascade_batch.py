"""Tests for CascadeBatch (Wave 6)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.case import Case
from app.services.batch.cascade_batch import CascadeBatch
from app.services.batch.types import ItemStatus
from app.services.cascade.cascade_pipeline import CascadeResult
from app.services.llm.mock import MockProvider

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.anyio
class TestCascadeBatch:
    async def test_fetch_reading_queued(self, db) -> None:
        """Fetches only reading_queued cases."""
        queued = Case(
            source="test", source_id="cb1", case_name="Queued",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        other = Case(
            source="test", source_id="cb2", case_name="Other",
            current_lifecycle_stage="discovered",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add_all([queued, other])
        await db.flush()

        provider = MockProvider()
        batch = CascadeBatch(provider)
        items = [item async for item in batch.fetch_items(db)]

        assert len(items) == 1
        assert items[0].source_id == "cb1"

    async def test_successful_processing(self, db) -> None:
        """Successful cascade returns SUCCESS."""
        case = Case(
            source="test", source_id="cb3", case_name="Success",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        provider = MockProvider()
        mock_pipeline = AsyncMock()
        mock_pipeline.process_case.return_value = CascadeResult(
            case_id=str(case.id),
            reading_success=True,
            judgment_success=True,
            checklist_success=True,
        )

        batch = CascadeBatch(provider)
        batch._pipeline = mock_pipeline

        result = await batch.process_item(db, case)
        assert result.status == ItemStatus.SUCCESS

    async def test_partial_failure(self, db) -> None:
        """Partial failure returns FAILED and increments circuit breaker."""
        case = Case(
            source="test", source_id="cb4", case_name="Partial",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        provider = MockProvider()
        mock_pipeline = AsyncMock()
        mock_pipeline.process_case.return_value = CascadeResult(
            case_id=str(case.id),
            reading_success=True,
            judgment_success=False,
            aborted_at="judgment",
            error="No profile",
        )

        batch = CascadeBatch(provider)
        batch._pipeline = mock_pipeline

        result = await batch.process_item(db, case)
        assert result.status == ItemStatus.FAILED
        assert batch._consecutive_failures == 1

    async def test_circuit_breaker_skips(self, db) -> None:
        """Circuit breaker skips after 3 consecutive failures."""
        provider = MockProvider()
        batch = CascadeBatch(provider)
        batch._consecutive_failures = 3  # Already at threshold

        case = Case(
            source="test", source_id="cb5", case_name="Skipped",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        result = await batch.process_item(db, case)
        assert result.status == ItemStatus.SKIPPED
        assert "Circuit breaker" in result.error_message

    async def test_success_resets_circuit_breaker(self, db) -> None:
        """Successful processing resets consecutive failure count."""
        provider = MockProvider()
        mock_pipeline = AsyncMock()
        mock_pipeline.process_case.return_value = CascadeResult(
            case_id="test", reading_success=True,
            judgment_success=True, checklist_success=True,
        )

        batch = CascadeBatch(provider)
        batch._pipeline = mock_pipeline
        batch._consecutive_failures = 2

        case = Case(
            source="test", source_id="cb6", case_name="Reset",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add(case)
        await db.flush()

        result = await batch.process_item(db, case)
        assert result.status == ItemStatus.SUCCESS
        assert batch._consecutive_failures == 0

    async def test_empty_queue(self, db) -> None:
        """Empty queue yields no items."""
        provider = MockProvider()
        batch = CascadeBatch(provider)
        items = [item async for item in batch.fetch_items(db)]
        assert len(items) == 0

    async def test_config_values(self) -> None:
        """Config matches cascade spec."""
        provider = MockProvider()
        batch = CascadeBatch(provider)
        assert batch.config.source == "system"
        assert batch.config.batch_type == "cascade_pipeline"
        assert batch.config.feature_origin == "F-002"
