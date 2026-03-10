"""Tests for ReadingBatch (F-002 Stage 3)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.case import Case
from app.models.case_card import CaseCard
from app.services.batch.reading_batch import ReadingBatch
from app.services.batch.types import ItemStatus
from app.services.llm.mock import MockProvider
from app.services.reading.reading_service import ReadingError

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.anyio
class TestReadingBatch:
    async def test_fetch_reading_queued_cases(self, db) -> None:
        """fetch_items should yield only reading_queued cases."""
        queued = Case(
            source="test", source_id="q1", case_name="Queued Case",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        other = Case(
            source="test", source_id="o1", case_name="Other Case",
            current_lifecycle_stage="discovered",
            first_seen_at=_NOW, issuing_org="テスト機関",
        )
        db.add_all([queued, other])
        await db.flush()

        provider = MockProvider()
        batch = ReadingBatch(provider)

        items = []
        async for item in batch.fetch_items(db):
            items.append(item)

        assert len(items) == 1
        assert items[0].source_id == "q1"

    async def test_successful_processing(self, db) -> None:
        """Successful processing should return SUCCESS status."""
        case = Case(
            source="test", source_id="s1", case_name="Success Case",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
            notice_url="https://example.com/notice.html",
        )
        db.add(case)
        await db.flush()

        mock_card = MagicMock(spec=CaseCard)
        mock_card.id = uuid4()

        mock_reading_svc = AsyncMock()
        mock_reading_svc.process_case.return_value = mock_card

        provider = MockProvider()
        batch = ReadingBatch(provider, reading_service=mock_reading_svc)

        result = await batch.process_item(db, case)

        assert result.status == ItemStatus.SUCCESS
        mock_reading_svc.process_case.assert_called_once()
        assert case.current_lifecycle_stage == "reading_completed"

    async def test_failed_processing(self, db) -> None:
        """Failed processing should return FAILED status."""
        case = Case(
            source="test", source_id="f1", case_name="Fail Case",
            current_lifecycle_stage="reading_queued",
            first_seen_at=_NOW, issuing_org="テスト機関",
            notice_url="https://example.com/notice.html",
        )
        db.add(case)
        await db.flush()

        mock_reading_svc = AsyncMock()
        mock_reading_svc.process_case.side_effect = ReadingError("Test error")

        provider = MockProvider()
        batch = ReadingBatch(provider, reading_service=mock_reading_svc)

        result = await batch.process_item(db, case)

        assert result.status == ItemStatus.FAILED
        assert "Test error" in result.error_message
        assert case.current_lifecycle_stage == "reading_failed"

    async def test_empty_queue(self, db) -> None:
        """Empty queue should yield no items."""
        provider = MockProvider()
        batch = ReadingBatch(provider)

        items = []
        async for item in batch.fetch_items(db):
            items.append(item)

        assert len(items) == 0

    async def test_config_values(self) -> None:
        """Config should match F-002 batch specification."""
        provider = MockProvider()
        batch = ReadingBatch(provider)

        assert batch.config.source == "system"
        assert batch.config.batch_type == "reading"
        assert batch.config.feature_origin == "F-002"
