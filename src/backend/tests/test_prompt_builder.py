"""Tests for PromptBuilder (F-002 Stage 2)."""

from app.services.reading.prompt_builder import (
    EXTRACTION_SYSTEM_PROMPT,
    PromptBuilder,
)


class TestPromptBuilder:
    def test_system_prompt_has_five_categories(self) -> None:
        assert "eligibility" in EXTRACTION_SYSTEM_PROMPT
        assert "schedule" in EXTRACTION_SYSTEM_PROMPT
        assert "business_content" in EXTRACTION_SYSTEM_PROMPT
        assert "submission_items" in EXTRACTION_SYSTEM_PROMPT
        assert "risk_factors" in EXTRACTION_SYSTEM_PROMPT

    def test_system_prompt_has_assertion_type_rules(self) -> None:
        assert "fact" in EXTRACTION_SYSTEM_PROMPT
        assert "inferred" in EXTRACTION_SYSTEM_PROMPT
        assert "caution" in EXTRACTION_SYSTEM_PROMPT

    def test_full_extraction_prompt(self) -> None:
        builder = PromptBuilder()
        request = builder.build_extraction_prompt(
            notice_text="入札公告テキスト",
            spec_text="仕様書テキスト",
        )
        assert request.system == EXTRACTION_SYSTEM_PROMPT
        assert len(request.messages) == 1
        user_msg = request.messages[0]["content"]
        assert "入札公告テキスト" in user_msg
        assert "仕様書テキスト" in user_msg
        assert request.metadata["prompt_type"] == "full_extraction"

    def test_notice_only_prompt(self) -> None:
        builder = PromptBuilder()
        request = builder.build_extraction_prompt(
            notice_text="入札公告テキスト",
            spec_text=None,
        )
        user_msg = request.messages[0]["content"]
        assert "入札公告テキスト" in user_msg
        assert "仕様書" not in user_msg

    def test_chunk_prompt_includes_index(self) -> None:
        builder = PromptBuilder()
        request = builder.build_chunk_prompt(
            chunk_text="チャンクテキスト",
            chunk_index=2,
            total_chunks=3,
        )
        assert "2/3" in request.system
        assert request.messages[0]["content"] == "チャンクテキスト"
        assert request.metadata["prompt_type"] == "chunk_extraction"
        assert request.metadata["chunk_index"] == 2
        assert request.metadata["total_chunks"] == 3
