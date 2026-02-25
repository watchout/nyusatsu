"""Scanned PDF detection for F-002 Stage 1.

Detects scanned/image-heavy PDFs that cannot be reliably text-extracted.
Per F-002 §3-B-1a:
- chars_per_page < SCANNED_PDF_CHAR_THRESHOLD (50) → scanned
- symbol_ratio > 60% → garbled OCR (treated as scanned)
"""

from __future__ import annotations

import re

from app.core.constants import SCANNED_PDF_CHAR_THRESHOLD
from app.services.reading.text_extractor import PdfExtraction


_SYMBOL_PATTERN = re.compile(
    r"[^\w\s\u3000-\u9fff\uf900-\ufaff\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]",
    re.UNICODE,
)


class ScannedPdfDetector:
    """Detect scanned PDFs from extraction results."""

    def __init__(
        self,
        char_threshold: int = SCANNED_PDF_CHAR_THRESHOLD,
        symbol_ratio_threshold: float = 0.60,
    ) -> None:
        self._char_threshold = char_threshold
        self._symbol_ratio_threshold = symbol_ratio_threshold

    def is_scanned(self, extraction: PdfExtraction) -> tuple[bool, str | None]:
        """Check if the PDF extraction appears to be from a scanned document.

        Returns:
            (is_scanned, reason) — reason is None if not scanned.
        """
        if not extraction.pages:
            return True, "no_pages"

        # Check 1: Average chars per page
        total_chars = sum(p.char_count for p in extraction.pages)
        avg_chars = total_chars / len(extraction.pages)

        if avg_chars < self._char_threshold:
            return True, f"low_char_count ({avg_chars:.0f} chars/page < {self._char_threshold})"

        # Check 2: Symbol ratio (garbled OCR)
        full_text = extraction.text
        if full_text:
            symbols = len(_SYMBOL_PATTERN.findall(full_text))
            ratio = symbols / len(full_text)
            if ratio > self._symbol_ratio_threshold:
                return True, f"high_symbol_ratio ({ratio:.1%} > {self._symbol_ratio_threshold:.0%})"

        return False, None
