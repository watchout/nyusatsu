"""Tests for SectionChunker (F-002 Stage 2)."""

from app.services.reading.section_chunker import SectionChunker


class TestSectionChunker:
    def test_short_text_no_split(self) -> None:
        chunker = SectionChunker(token_threshold=5000)
        text = "短いテキスト"
        assert not chunker.needs_splitting(text)
        chunks = chunker.split(text)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_index == 1
        assert chunks[0].total_chunks == 1

    def test_long_text_splits(self) -> None:
        # Create text longer than threshold (5000 tokens ≈ 7500 chars)
        chunker = SectionChunker(token_threshold=100)
        text = "■第1章 概要\n" + "あ" * 200 + "\n■第2章 詳細\n" + "い" * 200
        assert chunker.needs_splitting(text)
        chunks = chunker.split(text)
        assert len(chunks) >= 2
        # Verify indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i + 1
            assert chunk.total_chunks == len(chunks)

    def test_section_boundaries_preserved(self) -> None:
        chunker = SectionChunker(token_threshold=50)
        text = (
            "第一条 本規約\n" + "あ" * 100 + "\n"
            "第二条 適用範囲\n" + "い" * 100 + "\n"
            "第三条 定義\n" + "う" * 100
        )
        chunks = chunker.split(text)
        # At least some chunks should start with section headers
        headers = [c.start_section for c in chunks if c.start_section]
        assert len(headers) > 0

    def test_token_estimation(self) -> None:
        chunker = SectionChunker()
        # 150 chars / 1.5 = 100 tokens
        text = "あ" * 150
        tokens = chunker.estimate_tokens(text)
        assert tokens == 100

    def test_empty_text_returns_empty(self) -> None:
        chunker = SectionChunker()
        assert chunker.split("") == []

    def test_threshold_boundary(self) -> None:
        """Text at exactly threshold should not be split."""
        # 5000 tokens * 1.5 chars/token = 7500 chars
        chunker = SectionChunker(token_threshold=5000)
        text = "あ" * 7500  # Exactly 5000 tokens
        assert not chunker.needs_splitting(text)
        chunks = chunker.split(text)
        assert len(chunks) == 1

    def test_no_sections_fallback_split(self) -> None:
        """Text without section markers should still split by size."""
        chunker = SectionChunker(token_threshold=50)
        # No section markers, just plain text
        text = "テスト" * 500
        chunks = chunker.split(text)
        assert len(chunks) >= 2
