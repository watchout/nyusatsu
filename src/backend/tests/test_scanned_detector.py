"""Tests for ScannedPdfDetector (F-002 Stage 1)."""

from pathlib import Path

from app.services.reading.scanned_detector import ScannedPdfDetector
from app.services.reading.text_extractor import PdfExtraction, PdfPage, TextExtractor

FIXTURES = Path(__file__).parent / "fixtures" / "reading"


class TestScannedPdfDetector:
    def test_normal_pdf_not_scanned(self) -> None:
        text = (FIXTURES / "pdf_text_medium.txt").read_text(encoding="utf-8")
        extraction = TextExtractor().extract_pdf(text)
        detector = ScannedPdfDetector()
        is_scanned, reason = detector.is_scanned(extraction)
        assert is_scanned is False
        assert reason is None

    def test_low_chars_detected(self) -> None:
        text = (FIXTURES / "pdf_scanned_01.txt").read_text(encoding="utf-8")
        extraction = TextExtractor().extract_pdf(text)
        detector = ScannedPdfDetector()
        is_scanned, reason = detector.is_scanned(extraction)
        assert is_scanned is True
        assert "low_char_count" in reason

    def test_high_symbol_ratio_detected(self) -> None:
        text = (FIXTURES / "pdf_scanned_garbled.txt").read_text(encoding="utf-8")
        extraction = TextExtractor().extract_pdf(text)
        detector = ScannedPdfDetector()
        is_scanned, reason = detector.is_scanned(extraction)
        assert is_scanned is True
        assert "high_symbol_ratio" in reason

    def test_empty_pages_detected(self) -> None:
        extraction = PdfExtraction(text="", pages=[])
        detector = ScannedPdfDetector()
        is_scanned, reason = detector.is_scanned(extraction)
        assert is_scanned is True
        assert reason == "no_pages"

    def test_borderline_not_detected(self) -> None:
        """Text with exactly threshold chars per page should not be flagged."""
        # 50 chars threshold — create page with exactly 50 chars
        page_text = "あ" * 50
        extraction = PdfExtraction(
            text=page_text,
            pages=[PdfPage(page_number=1, text=page_text, char_count=50)],
        )
        detector = ScannedPdfDetector()
        is_scanned, reason = detector.is_scanned(extraction)
        assert is_scanned is False
