"""Text extraction from HTML and PDF for F-002 Stage 1.

Extracts structured text with section/page information for evidence mapping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag


@dataclass
class HtmlSection:
    """A section extracted from an HTML document."""

    heading: str
    heading_path: str  # e.g. "入札公告 > 参加資格"
    content: str
    selector_hint: str | None = None


@dataclass
class HtmlExtraction:
    """Result of extracting text from HTML."""

    text: str
    sections: list[HtmlSection] = field(default_factory=list)


@dataclass
class PdfPage:
    """A single page from a PDF extraction."""

    page_number: int  # 1-indexed
    text: str
    char_count: int


@dataclass
class PdfExtraction:
    """Result of extracting text from PDF."""

    text: str
    pages: list[PdfPage] = field(default_factory=list)


class TextExtractor:
    """Extract structured text from HTML and PDF content."""

    _HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def extract_html(self, html_bytes: bytes) -> HtmlExtraction:
        """Extract text and section structure from HTML.

        Args:
            html_bytes: Raw HTML content.

        Returns:
            HtmlExtraction with full text and section breakdown.
        """
        soup = BeautifulSoup(html_bytes, "html.parser")

        # Remove script/style
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        full_text = soup.get_text(separator="\n", strip=True)
        sections = self._extract_html_sections(soup)

        return HtmlExtraction(text=full_text, sections=sections)

    def extract_pdf(self, pdf_text: str) -> PdfExtraction:
        """Extract structured text from pre-extracted PDF text.

        For Phase 4 we work with pre-extracted text (pdfplumber output).
        Page boundaries are detected by form-feed characters or page markers.

        Args:
            pdf_text: Pre-extracted text from PDF.

        Returns:
            PdfExtraction with full text and per-page breakdown.
        """
        # Split by form-feed or treat as single page
        raw_pages = pdf_text.split("\f") if "\f" in pdf_text else [pdf_text]

        pages = []
        for i, page_text in enumerate(raw_pages, start=1):
            stripped = page_text.strip()
            if stripped:
                pages.append(PdfPage(
                    page_number=i,
                    text=stripped,
                    char_count=len(stripped),
                ))

        combined = "\n".join(p.text for p in pages)
        return PdfExtraction(text=combined, pages=pages)

    def _extract_html_sections(self, soup: BeautifulSoup) -> list[HtmlSection]:
        """Walk headings to build section list with heading paths."""
        sections: list[HtmlSection] = []
        heading_stack: list[tuple[int, str]] = []  # (level, text)

        for element in soup.find_all(self._HEADING_TAGS):
            if not isinstance(element, Tag):
                continue

            level = int(element.name[1])
            heading_text = element.get_text(strip=True)
            if not heading_text:
                continue

            # Pop stack to same or lower level
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading_text))

            # Build heading path
            heading_path = " > ".join(h[1] for _, h in enumerate(heading_stack))

            # Gather content until next heading
            content_parts: list[str] = []
            sibling = element.next_sibling
            while sibling:
                if isinstance(sibling, Tag) and sibling.name in self._HEADING_TAGS:
                    break
                text = sibling.get_text(strip=True) if isinstance(sibling, Tag) else str(sibling).strip()
                if text:
                    content_parts.append(text)
                sibling = sibling.next_sibling

            content = "\n".join(content_parts)

            # Build selector hint from id or class
            parent = element.parent
            selector_hint = None
            if parent and isinstance(parent, Tag):
                parent_id = parent.get("id")
                if parent_id:
                    selector_hint = f"#{parent_id}"

            sections.append(HtmlSection(
                heading=heading_text,
                heading_path=heading_path,
                content=content,
                selector_hint=selector_hint,
            ))

        return sections
