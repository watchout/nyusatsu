"""Tests for LLMExtractor (F-002 Stage 2)."""

import json

import pytest

from app.schemas.extraction import CaseCardExtraction
from app.services.llm.mock import MockProvider
from app.services.reading.llm_extractor import ExtractionResult, LLMExtractor
from app.services.reading.section_chunker import SectionChunker


def _make_extraction_json(**overrides) -> str:
    """Build a valid extraction JSON string."""
    data = {
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
        },
        "submission_items": {
            "bid_time_items": [
                {"name": "入札書", "assertion_type": "fact"},
            ],
        },
        "risk_factors": [],
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


@pytest.mark.anyio
class TestLLMExtractor:
    async def test_single_extraction_success(self) -> None:
        provider = MockProvider(default_content=_make_extraction_json())
        extractor = LLMExtractor(provider)

        result = await extractor.extract("入札公告テキスト")

        assert isinstance(result, ExtractionResult)
        assert isinstance(result.extraction, CaseCardExtraction)
        assert result.extraction.eligibility.grade == "C"
        assert result.was_chunked is False
        assert result.token_usage["input"] > 0
        assert provider.call_count == 1

    async def test_single_with_spec_text(self) -> None:
        provider = MockProvider(default_content=_make_extraction_json())
        extractor = LLMExtractor(provider)

        result = await extractor.extract("公告テキスト", spec_text="仕様書テキスト")

        assert result.was_chunked is False
        assert provider.call_count == 1

    async def test_chunked_extraction(self) -> None:
        """Long text triggers chunked extraction."""
        chunk1_data = {
            "eligibility": {
                "unified_qualification": True,
                "grade": "B",
            },
            "schedule": None,
            "business_content": None,
            "submission_items": None,
            "risk_factors": [],
        }
        chunk2_data = {
            "eligibility": None,
            "schedule": {
                "submission_deadline": "2026-04-01T17:00:00+09:00",
            },
            "business_content": {
                "summary": "テスト業務",
            },
            "submission_items": None,
            "risk_factors": [],
        }

        provider = MockProvider()
        provider.queue_response(json.dumps(chunk1_data, ensure_ascii=False))
        provider.queue_response(json.dumps(chunk2_data, ensure_ascii=False))
        # Use low threshold to force chunking
        chunker = SectionChunker(token_threshold=100)
        extractor = LLMExtractor(provider, chunker=chunker)

        long_text = "■第1章 概要\n" + "あ" * 300 + "\n■第2章 詳細\n" + "い" * 300
        result = await extractor.extract(long_text)

        assert result.was_chunked is True
        assert result.extraction.eligibility.grade == "B"
        assert result.extraction.schedule.submission_deadline == "2026-04-01T17:00:00+09:00"
        assert result.extraction.business_content.summary == "テスト業務"
        assert provider.call_count == 2

    async def test_merge_deduplicates_items(self) -> None:
        """Merge should not duplicate items with same name."""
        chunk1_data = {
            "submission_items": {
                "bid_time_items": [
                    {"name": "入札書", "assertion_type": "fact"},
                    {"name": "資格審査結果通知書", "assertion_type": "fact"},
                ],
            },
        }
        chunk2_data = {
            "submission_items": {
                "bid_time_items": [
                    {"name": "入札書", "assertion_type": "fact"},  # Duplicate
                    {"name": "委任状", "assertion_type": "inferred"},
                ],
            },
        }

        provider = MockProvider()
        provider.queue_response(json.dumps(chunk1_data, ensure_ascii=False))
        provider.queue_response(json.dumps(chunk2_data, ensure_ascii=False))
        chunker = SectionChunker(token_threshold=100)
        extractor = LLMExtractor(provider, chunker=chunker)

        long_text = "■第1節\n" + "あ" * 300 + "\n■第2節\n" + "い" * 300
        result = await extractor.extract(long_text)

        names = [i.name for i in result.extraction.submission_items.bid_time_items]
        assert names == ["入札書", "資格審査結果通知書", "委任状"]

    async def test_token_usage_accumulated(self) -> None:
        """Token usage should be summed across chunks."""
        provider = MockProvider(
            default_content=_make_extraction_json(),
            default_token_usage={"input": 200, "output": 100},
        )
        chunker = SectionChunker(token_threshold=100)
        extractor = LLMExtractor(provider, chunker=chunker)

        long_text = "■第1章\n" + "あ" * 300 + "\n■第2章\n" + "い" * 300
        result = await extractor.extract(long_text)

        assert result.was_chunked is True
        assert result.token_usage["input"] == 200 * provider.call_count
        assert result.token_usage["output"] == 100 * provider.call_count

    async def test_model_from_response(self) -> None:
        provider = MockProvider(default_content=_make_extraction_json())
        extractor = LLMExtractor(provider)

        result = await extractor.extract("テスト")
        assert result.llm_model == "mock-model"
