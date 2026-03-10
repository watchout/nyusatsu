"""Tests for ReadingService (F-002 Stage 3).

Uses MockProvider for LLM and patches DocumentFetcher to avoid network calls.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.case import Case
from app.models.case_card import CaseCard
from app.services.llm.mock import MockProvider
from app.services.reading.document_fetcher import FetchResult
from app.services.reading.reading_service import ReadingError, ReadingService


def _make_mock_case(**overrides) -> Case:
    """Create a mock Case object."""
    case = MagicMock(spec=Case)
    case.id = overrides.get("id", uuid4())
    case.notice_url = overrides.get("notice_url", "https://example.com/notice.html")
    case.spec_url = overrides.get("spec_url")
    return case


def _make_extraction_json() -> str:
    return json.dumps({
        "eligibility": {
            "unified_qualification": True,
            "grade": "C",
            "business_category": "物品の販売",
            "region": "関東・甲信越",
        },
        "schedule": {
            "submission_deadline": "2026-03-15T17:00:00+09:00",
        },
        "business_content": {
            "summary": "コピー用紙購入",
            "business_type": "物品の販売",
        },
        "submission_items": {
            "bid_time_items": [
                {"name": "入札書", "assertion_type": "fact"},
            ],
        },
        "risk_factors": [],
    }, ensure_ascii=False)


def _make_mock_fetcher(
    *,
    notice_content: bytes = b"<html><body>test</body></html>",
    spec_content: bytes | None = None,
) -> AsyncMock:
    """Create a mock DocumentFetcher."""
    fetcher = AsyncMock()
    fetcher.fetch_notice_html.return_value = FetchResult(
        content=notice_content,
        content_type="text/html",
        url="https://example.com/notice.html",
        status_code=200,
    )
    if spec_content:
        fetcher.fetch_spec_pdf.return_value = FetchResult(
            content=spec_content,
            content_type="application/pdf",
            url="https://example.com/spec.pdf",
            status_code=200,
        )
    else:
        fetcher.fetch_spec_pdf.return_value = None
    return fetcher


def _make_mock_file_store(hash_value: str = "abc123") -> MagicMock:
    """Create a mock FileStore with sync compute_hash and async save methods."""
    store = MagicMock()
    store.compute_hash.return_value = hash_value
    store.save_notice = AsyncMock()
    store.save_spec = AsyncMock()
    return store


def _build_service(
    provider: MockProvider,
    fetcher: AsyncMock,
    file_store: MagicMock,
    version_manager: AsyncMock,
) -> ReadingService:
    """Build a ReadingService with all dependencies injected."""
    with patch.object(ReadingService, "__init__", lambda self, *a, **kw: None):
        from app.services.reading.evidence_mapper import EvidenceMapper
        from app.services.reading.llm_extractor import LLMExtractor
        from app.services.reading.quality_checker import QualityChecker
        from app.services.reading.scanned_detector import ScannedPdfDetector
        from app.services.reading.text_extractor import TextExtractor

        service = ReadingService.__new__(ReadingService)
        service._provider = provider
        service._fetcher = fetcher
        service._text_extractor = TextExtractor()
        service._scanned_detector = ScannedPdfDetector()
        service._file_store = file_store
        service._llm_extractor = LLMExtractor(provider)
        service._evidence_mapper = EvidenceMapper()
        service._quality_checker = QualityChecker()
        service._version_manager = version_manager
        return service


@pytest.mark.anyio
class TestReadingService:
    async def test_full_pipeline_notice_only(self, db) -> None:
        """Full pipeline with notice HTML only (no spec PDF)."""
        case = _make_mock_case()
        provider = MockProvider(default_content=_make_extraction_json())
        fetcher = _make_mock_fetcher()
        file_store = _make_mock_file_store()

        mock_card = MagicMock(spec=CaseCard)
        mock_card.id = uuid4()
        vm = AsyncMock()
        vm.get_current.return_value = None
        vm.create_initial.return_value = mock_card

        service = _build_service(provider, fetcher, file_store, vm)
        card = await service.process_case(db, case)

        assert card is mock_card
        vm.create_initial.assert_called_once()
        fetcher.fetch_notice_html.assert_called_once()
        assert provider.call_count == 1

    async def test_no_notice_url_raises(self, db) -> None:
        """Missing notice_url should raise ReadingError."""
        case = _make_mock_case(notice_url=None)
        provider = MockProvider()
        service = ReadingService(provider)

        with pytest.raises(ReadingError, match="no notice_url"):
            await service.process_case(db, case)

    async def test_scanned_pdf_raises(self, db) -> None:
        """Scanned PDF should raise ReadingError."""
        case = _make_mock_case(spec_url="https://example.com/spec.pdf")
        provider = MockProvider(default_content=_make_extraction_json())

        scanned_content = b"   \n  \n"
        fetcher = _make_mock_fetcher(spec_content=scanned_content)
        file_store = _make_mock_file_store()

        vm = AsyncMock()
        vm.get_current.return_value = None

        service = _build_service(provider, fetcher, file_store, vm)

        with pytest.raises(ReadingError, match="Scanned PDF"):
            await service.process_case(db, case)

    async def test_cache_hit_skips_llm(self, db) -> None:
        """Soft scope with matching hash should skip LLM call."""
        case = _make_mock_case()
        provider = MockProvider(default_content=_make_extraction_json())
        fetcher = _make_mock_fetcher()
        file_store = _make_mock_file_store(hash_value="cached_hash")

        existing_card = MagicMock(spec=CaseCard)
        existing_card.file_hash = "cached_hash"
        vm = AsyncMock()
        vm.get_current.return_value = existing_card

        service = _build_service(provider, fetcher, file_store, vm)
        card = await service.process_case(db, case, scope="soft")

        assert card is existing_card
        assert provider.call_count == 0  # LLM not called

    async def test_force_scope_ignores_cache(self, db) -> None:
        """Force scope should re-extract even with matching hash."""
        case = _make_mock_case()
        provider = MockProvider(default_content=_make_extraction_json())
        fetcher = _make_mock_fetcher()
        file_store = _make_mock_file_store(hash_value="cached_hash")

        existing_card = MagicMock(spec=CaseCard)
        existing_card.file_hash = "cached_hash"
        new_card = MagicMock(spec=CaseCard)
        new_card.id = uuid4()
        vm = AsyncMock()
        vm.get_current.return_value = existing_card
        vm.rotate.return_value = new_card

        service = _build_service(provider, fetcher, file_store, vm)
        card = await service.process_case(db, case, scope="force")

        assert card is new_card
        assert provider.call_count == 1
        vm.rotate.assert_called_once()
