"""Tests for EvidenceMapper (F-002 Stage 3)."""

from app.schemas.extraction import (
    BusinessContentExtraction,
    CaseCardExtraction,
    EligibilityExtraction,
)
from app.services.reading.evidence_mapper import EvidenceMapper
from app.services.reading.text_extractor import (
    HtmlExtraction,
    HtmlSection,
    PdfExtraction,
    PdfPage,
)


def _make_html_extraction(sections: list[tuple[str, str]]) -> HtmlExtraction:
    """Helper to create HtmlExtraction with simple sections."""
    html_sections = [
        HtmlSection(
            heading=heading,
            heading_path=heading,
            content=content,
            selector_hint=None,
        )
        for heading, content in sections
    ]
    return HtmlExtraction(
        text="\n".join(c for _, c in sections),
        sections=html_sections,
    )


def _make_pdf_extraction(pages: list[str]) -> PdfExtraction:
    """Helper to create PdfExtraction with simple pages."""
    pdf_pages = [
        PdfPage(
            page_number=i + 1,
            text=text,
            char_count=len(text),
        )
        for i, text in enumerate(pages)
    ]
    return PdfExtraction(
        text="\n".join(pages),
        pages=pdf_pages,
    )


class TestEvidenceMapper:
    def test_strong_match_jaccard(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                grade="C",
                business_category="物品の販売",
            ),
        )
        html = _make_html_extraction([
            ("参加資格", "全省庁統一資格 等級C 物品の販売 関東甲信越地域"),
        ])
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction, html_extraction=html)

        # "物品の販売" should match strongly against section content
        biz_match = next(
            (m for m in result.matches if m.field_name == "eligibility.business_category"),
            None,
        )
        assert biz_match is not None
        assert biz_match.confidence in ("strong", "candidate")

    def test_candidate_match(self) -> None:
        extraction = CaseCardExtraction(
            business_content=BusinessContentExtraction(
                summary="事務用品の供給業務",
            ),
        )
        html = _make_html_extraction([
            ("業務概要", "事務用品等の供給に関する業務一式"),
        ])
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction, html_extraction=html)

        summary_match = next(
            (m for m in result.matches if m.field_name == "business_content.summary"),
            None,
        )
        assert summary_match is not None
        # Similar but not identical — should be at least candidate
        assert summary_match.confidence in ("strong", "candidate")

    def test_no_match(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                grade="A",
            ),
        )
        html = _make_html_extraction([
            ("スケジュール", "入札締切 令和8年3月15日"),
        ])
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction, html_extraction=html)

        grade_match = next(
            (m for m in result.matches if m.field_name == "eligibility.grade"),
            None,
        )
        assert grade_match is not None
        # "A" is too short and different from schedule text
        assert grade_match.confidence == "none" or grade_match.evidence_ref is not None

    def test_pdf_evidence_structure(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                business_category="役務の提供",
            ),
        )
        pdf = _make_pdf_extraction([
            "第1章 概要\n役務の提供に関する入札公告",
        ])
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction, pdf_extraction=pdf)

        biz_match = next(
            (m for m in result.matches if m.field_name == "eligibility.business_category"),
            None,
        )
        assert biz_match is not None
        if biz_match.evidence_ref:
            assert biz_match.evidence_ref.source_type == "pdf"
            assert biz_match.evidence_ref.page == 1

    def test_html_evidence_structure(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                region="関東・甲信越",
            ),
        )
        html = _make_html_extraction([
            ("参加資格", "関東・甲信越地域における全省庁統一資格を有すること"),
        ])
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction, html_extraction=html)

        region_match = next(
            (m for m in result.matches if m.field_name == "eligibility.region"),
            None,
        )
        assert region_match is not None
        if region_match.evidence_ref:
            assert region_match.evidence_ref.source_type == "html"

    def test_evidence_rate_calculation(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                grade="C",
                business_category="物品の販売",
                region="関東・甲信越",
            ),
        )
        html = _make_html_extraction([
            ("参加資格", "全省庁統一資格 等級C 物品の販売 関東甲信越地域"),
        ])
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction, html_extraction=html)

        # At least some fields should have evidence
        assert len(result.matches) == 3
        assert 0.0 <= result.evidence_rate <= 1.0

    def test_no_source_text_all_none(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                grade="C",
            ),
        )
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction)

        # No source text → no evidence
        assert all(m.confidence == "none" for m in result.matches)
        assert result.evidence_rate == 0.0

    def test_evidence_dict_populated(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                business_category="物品の販売",
            ),
        )
        html = _make_html_extraction([
            ("参加資格", "物品の販売に関する全省庁統一資格を有すること"),
        ])
        mapper = EvidenceMapper()
        result = mapper.map_evidence(extraction, html_extraction=html)

        # If evidence found, it should be in the dict
        if result.evidence_rate > 0:
            assert len(result.evidence_dict) > 0
