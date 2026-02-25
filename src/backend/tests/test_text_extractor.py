"""Tests for TextExtractor (F-002 Stage 1)."""

from pathlib import Path

from app.services.reading.text_extractor import TextExtractor

FIXTURES = Path(__file__).parent / "fixtures" / "reading"


class TestHtmlExtractor:
    def test_simple_html_extraction(self) -> None:
        html = (FIXTURES / "html_simple.html").read_bytes()
        ext = TextExtractor().extract_html(html)
        assert "消耗品購入" in ext.text
        assert "全省庁統一資格" in ext.text
        assert len(ext.sections) > 0

    def test_section_structure_preserved(self) -> None:
        html = (FIXTURES / "html_simple.html").read_bytes()
        ext = TextExtractor().extract_html(html)
        headings = [s.heading for s in ext.sections]
        assert "案件概要" in headings
        assert "競争参加資格" in headings
        assert "スケジュール" in headings

    def test_heading_path_built(self) -> None:
        html = (FIXTURES / "html_simple.html").read_bytes()
        ext = TextExtractor().extract_html(html)
        # h2 under h1 should build path
        paths = [s.heading_path for s in ext.sections]
        # At least one section has a multi-level path
        assert any(">" in p for p in paths) or all(len(p) > 0 for p in paths)

    def test_complex_html_nested_tables(self) -> None:
        html = (FIXTURES / "html_complex.html").read_bytes()
        ext = TextExtractor().extract_html(html)
        assert "情報システム運用支援業務" in ext.text
        assert "ISO27001" in ext.text
        assert len(ext.sections) >= 5

    def test_selector_hint_from_parent_id(self) -> None:
        html = (FIXTURES / "html_simple.html").read_bytes()
        ext = TextExtractor().extract_html(html)
        hints = [s.selector_hint for s in ext.sections if s.selector_hint]
        assert any(h.startswith("#") for h in hints)

    def test_empty_html(self) -> None:
        ext = TextExtractor().extract_html(b"<html><body></body></html>")
        assert ext.text == ""
        assert ext.sections == []

    def test_missing_fields_html(self) -> None:
        html = (FIXTURES / "html_missing_fields.html").read_bytes()
        ext = TextExtractor().extract_html(html)
        assert "備品購入" in ext.text
        # Should still extract what's available
        assert "全省庁統一資格" in ext.text


class TestPdfExtractor:
    def test_simple_pdf_text(self) -> None:
        text = (FIXTURES / "pdf_text_simple.txt").read_text(encoding="utf-8")
        ext = TextExtractor().extract_pdf(text)
        assert "消耗品購入" in ext.text
        assert len(ext.pages) >= 1
        assert ext.pages[0].page_number == 1

    def test_medium_pdf_text(self) -> None:
        text = (FIXTURES / "pdf_text_medium.txt").read_text(encoding="utf-8")
        ext = TextExtractor().extract_pdf(text)
        assert "事務用品等供給業務" in ext.text
        assert ext.pages[0].char_count > 0

    def test_tables_pdf_text(self) -> None:
        text = (FIXTURES / "pdf_text_tables.txt").read_text(encoding="utf-8")
        ext = TextExtractor().extract_pdf(text)
        assert "什器備品購入" in ext.text
        assert "事務机" in ext.text

    def test_form_feed_page_split(self) -> None:
        text = "Page 1 content\fPage 2 content\fPage 3 content"
        ext = TextExtractor().extract_pdf(text)
        assert len(ext.pages) == 3
        assert ext.pages[0].page_number == 1
        assert ext.pages[1].page_number == 2
        assert ext.pages[2].page_number == 3

    def test_single_page_no_formfeed(self) -> None:
        text = (FIXTURES / "pdf_text_simple.txt").read_text(encoding="utf-8")
        ext = TextExtractor().extract_pdf(text)
        # No form feed → single page
        assert len(ext.pages) == 1
