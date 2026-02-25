"""Tests for evidence schema (Wave 0 contract validation)."""

import pytest
from pydantic import ValidationError

from app.schemas.evidence import (
    AssertionType,
    EvidenceRef,
    HtmlEvidence,
    PdfEvidence,
)


class TestAssertionType:
    def test_enum_values(self) -> None:
        assert AssertionType.FACT == "fact"
        assert AssertionType.INFERRED == "inferred"
        assert AssertionType.CAUTION == "caution"

    def test_enum_count(self) -> None:
        assert len(AssertionType) == 3


class TestPdfEvidence:
    def test_valid(self) -> None:
        ev = PdfEvidence(
            page=3,
            section="第2条 参加資格",
            quote="全省庁統一資格を有する者であること",
            assertion_type=AssertionType.FACT,
        )
        assert ev.source_type == "pdf"
        assert ev.page == 3
        assert ev.assertion_type == AssertionType.FACT

    def test_page_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            PdfEvidence(
                page=0,
                section="sec",
                quote="text",
                assertion_type=AssertionType.FACT,
            )


class TestHtmlEvidence:
    def test_valid(self) -> None:
        ev = HtmlEvidence(
            selector="#section-eligibility",
            heading_path="入札公告 > 参加資格",
            quote="全省庁統一資格を有する者であること",
            assertion_type=AssertionType.FACT,
        )
        assert ev.source_type == "html"
        assert ev.selector == "#section-eligibility"
        assert ev.heading_path == "入札公告 > 参加資格"

    def test_selector_optional(self) -> None:
        ev = HtmlEvidence(
            heading_path="入札公告 > 参加資格",
            quote="テスト",
            assertion_type=AssertionType.INFERRED,
        )
        assert ev.selector is None


class TestEvidenceRefUnion:
    def test_pdf_variant(self) -> None:
        data = {
            "source_type": "pdf",
            "page": 1,
            "section": "sec",
            "quote": "text",
            "assertion_type": "fact",
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(EvidenceRef)
        ev = adapter.validate_python(data)
        assert isinstance(ev, PdfEvidence)

    def test_html_variant(self) -> None:
        data = {
            "source_type": "html",
            "heading_path": "path",
            "quote": "text",
            "assertion_type": "caution",
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(EvidenceRef)
        ev = adapter.validate_python(data)
        assert isinstance(ev, HtmlEvidence)
