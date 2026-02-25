"""Section-aware text chunker for F-002 Stage 2.

Splits long documents into chunks that respect section boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.constants import CHUNK_SPLIT_TOKEN_THRESHOLD

# Rough token estimate: 1 CJK char ≈ 1.5 tokens, 1 ASCII word ≈ 1 token.
# We use a conservative factor of ~1.5 chars per token for Japanese text.
_CHARS_PER_TOKEN = 1.5

# Section boundary patterns (Japanese government documents)
_SECTION_PATTERN = re.compile(
    r"(?:^|\n)"
    r"(?:"
    r"第[一二三四五六七八九十\d]+[条章節項]"  # 第一条, 第2章 etc.
    r"|[１-９\d]+[\.\s．]"  # 1. 2. etc.
    r"|■|●|◆|【"  # Markers
    r"|[（\(][一二三四五六七八九十\d]+[）\)]"  # (一), (1) etc.
    r")",
)


@dataclass(frozen=True)
class TextChunk:
    """A section of text with metadata."""

    text: str
    start_section: str | None
    chunk_index: int
    total_chunks: int


class SectionChunker:
    """Split long text into section-aware chunks."""

    def __init__(
        self,
        *,
        token_threshold: int = CHUNK_SPLIT_TOKEN_THRESHOLD,
    ) -> None:
        self._token_threshold = token_threshold

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if not text:
            return 0
        return max(1, int(len(text) / _CHARS_PER_TOKEN))

    def needs_splitting(self, text: str) -> bool:
        """Check if text exceeds the token threshold."""
        return self.estimate_tokens(text) > self._token_threshold

    def split(self, text: str) -> list[TextChunk]:
        """Split text into chunks respecting section boundaries.

        If text is within threshold, returns a single chunk.
        """
        if not text:
            return []

        if not self.needs_splitting(text):
            return [
                TextChunk(
                    text=text,
                    start_section=None,
                    chunk_index=1,
                    total_chunks=1,
                ),
            ]

        # Find section boundaries
        sections = self._find_sections(text)
        if not sections:
            # No sections found — split by character count
            return self._split_by_size(text)

        return self._merge_sections_into_chunks(text, sections)

    def _find_sections(self, text: str) -> list[tuple[int, str]]:
        """Find section start positions and their header text."""
        sections: list[tuple[int, str]] = []
        for match in _SECTION_PATTERN.finditer(text):
            start = match.start()
            # Extract a short header (up to 80 chars from match start)
            end = min(start + 80, len(text))
            line_end = text.find("\n", start + 1, end)
            if line_end == -1:
                line_end = end
            header = text[start:line_end].strip()
            sections.append((start, header))
        return sections

    def _merge_sections_into_chunks(
        self,
        text: str,
        sections: list[tuple[int, str]],
    ) -> list[TextChunk]:
        """Merge consecutive sections into chunks within token threshold."""
        char_limit = int(self._token_threshold * _CHARS_PER_TOKEN)
        chunks: list[TextChunk] = []
        chunk_start = 0
        chunk_header = sections[0][1] if sections else None

        for i in range(1, len(sections)):
            section_start, section_header = sections[i]
            if section_start - chunk_start > char_limit:
                # Current chunk is big enough, finalize it
                chunks.append(
                    TextChunk(
                        text=text[chunk_start:section_start],
                        start_section=chunk_header,
                        chunk_index=0,  # Will be set later
                        total_chunks=0,
                    ),
                )
                chunk_start = section_start
                chunk_header = section_header

        # Last chunk
        if chunk_start < len(text):
            chunks.append(
                TextChunk(
                    text=text[chunk_start:],
                    start_section=chunk_header,
                    chunk_index=0,
                    total_chunks=0,
                ),
            )

        # Assign indices
        total = len(chunks)
        return [
            TextChunk(
                text=c.text,
                start_section=c.start_section,
                chunk_index=i + 1,
                total_chunks=total,
            )
            for i, c in enumerate(chunks)
        ]

    def _split_by_size(self, text: str) -> list[TextChunk]:
        """Fallback: split text into equal-sized chunks."""
        char_limit = int(self._token_threshold * _CHARS_PER_TOKEN)
        chunks: list[TextChunk] = []
        start = 0
        while start < len(text):
            end = min(start + char_limit, len(text))
            # Try to split at a newline near the boundary
            if end < len(text):
                newline_pos = text.rfind("\n", start + char_limit // 2, end)
                if newline_pos > start:
                    end = newline_pos + 1
            chunks.append(
                TextChunk(
                    text=text[start:end],
                    start_section=None,
                    chunk_index=0,
                    total_chunks=0,
                ),
            )
            start = end

        total = len(chunks)
        return [
            TextChunk(
                text=c.text,
                start_section=c.start_section,
                chunk_index=i + 1,
                total_chunks=total,
            )
            for i, c in enumerate(chunks)
        ]
