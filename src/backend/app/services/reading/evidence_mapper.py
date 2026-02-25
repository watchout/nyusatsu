"""Evidence mapper for F-002 Stage 3.

Maps extracted fields back to source text using Jaccard similarity
and Levenshtein distance as a rescue mechanism.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import structlog

from app.core.constants import EVIDENCE_MATCH_CANDIDATE, EVIDENCE_MATCH_STRONG
from app.schemas.evidence import AssertionType, HtmlEvidence, PdfEvidence
from app.schemas.extraction import CaseCardExtraction
from app.services.reading.text_extractor import HtmlExtraction, PdfExtraction

logger = structlog.get_logger()


@dataclass
class EvidenceMatch:
    """A single field matched to source text."""

    field_name: str
    confidence: str  # "strong", "candidate", "none"
    evidence_ref: HtmlEvidence | PdfEvidence | None = None


@dataclass
class EvidenceMappingResult:
    """Result of mapping all extracted fields to evidence."""

    matches: list[EvidenceMatch] = field(default_factory=list)
    evidence_dict: dict = field(default_factory=dict)

    @property
    def evidence_rate(self) -> float:
        """Fraction of fields with evidence (strong or candidate)."""
        if not self.matches:
            return 0.0
        matched = sum(1 for m in self.matches if m.confidence != "none")
        return matched / len(self.matches)


def _normalize(text: str) -> str:
    """Normalize text for comparison: NFKC + lowercase + strip whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "", text)
    return text.lower()


def _contains(value: str, content: str) -> bool:
    """Check if normalized value is contained in normalized content."""
    return _normalize(value) in _normalize(content)


def _similarity(value: str, content: str) -> float:
    """Compute similarity score combining containment and bigram overlap.

    Uses substring containment as primary signal, then measures what
    fraction of the value's bigrams appear in the content (asymmetric
    overlap) so that short extracted values match against longer source
    text reliably.
    """
    nv = _normalize(value)
    nc = _normalize(content)

    if not nv or not nc:
        return 0.0

    # Substring containment: strongest signal
    if nv in nc:
        return 1.0

    if len(nv) < 2 or len(nc) < 2:
        return 1.0 if nv == nc else 0.0

    # Asymmetric bigram overlap: what fraction of value bigrams exist in content?
    # This works well when the value is a condensed extraction from longer text.
    set_a = {nv[i : i + 2] for i in range(len(nv) - 1)}
    set_b = {nc[i : i + 2] for i in range(len(nc) - 1)}
    intersection = set_a & set_b
    if not set_a:
        return 0.0
    return len(intersection) / len(set_a)


def _levenshtein_ratio(a: str, b: str) -> float:
    """Compute normalized Levenshtein similarity (0.0 to 1.0)."""
    na, nb = _normalize(a), _normalize(b)
    if na == nb:
        return 1.0
    max_len = max(len(na), len(nb))
    if max_len == 0:
        return 1.0
    # Simple Levenshtein via dynamic programming
    rows = len(na) + 1
    cols = len(nb) + 1
    prev = list(range(cols))
    for i in range(1, rows):
        curr = [i] + [0] * (cols - 1)
        for j in range(1, cols):
            cost = 0 if na[i - 1] == nb[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    distance = prev[cols - 1]
    return 1.0 - (distance / max_len)


class EvidenceMapper:
    """Map extracted fields to source text evidence."""

    def map_evidence(
        self,
        extraction: CaseCardExtraction,
        html_extraction: HtmlExtraction | None = None,
        pdf_extraction: PdfExtraction | None = None,
    ) -> EvidenceMappingResult:
        """Map each extracted field to its source evidence."""
        result = EvidenceMappingResult()
        fields = self._collect_fields(extraction)

        for field_name, value in fields:
            match = self._find_best_match(
                field_name,
                value,
                html_extraction,
                pdf_extraction,
            )
            result.matches.append(match)
            if match.evidence_ref:
                result.evidence_dict[field_name] = match.evidence_ref.model_dump()

        return result

    def _collect_fields(
        self,
        extraction: CaseCardExtraction,
    ) -> list[tuple[str, str]]:
        """Collect all string fields from extraction for evidence matching."""
        fields: list[tuple[str, str]] = []

        if extraction.eligibility:
            e = extraction.eligibility
            if e.grade:
                fields.append(("eligibility.grade", e.grade))
            if e.business_category:
                fields.append(("eligibility.business_category", e.business_category))
            if e.region:
                fields.append(("eligibility.region", e.region))

        if extraction.schedule:
            s = extraction.schedule
            if s.submission_deadline:
                fields.append(("schedule.submission_deadline", s.submission_deadline))
            if s.opening_date:
                fields.append(("schedule.opening_date", s.opening_date))

        if extraction.business_content:
            bc = extraction.business_content
            if bc.summary:
                fields.append(("business_content.summary", bc.summary))
            if bc.business_type:
                fields.append(("business_content.business_type", bc.business_type))

        return fields

    def _find_best_match(
        self,
        field_name: str,
        value: str,
        html_extraction: HtmlExtraction | None,
        pdf_extraction: PdfExtraction | None,
    ) -> EvidenceMatch:
        """Find the best evidence match for a single field."""
        best_score = 0.0
        best_ref = None
        best_confidence = "none"

        # Search in HTML sections
        if html_extraction:
            for section in html_extraction.sections:
                score = _similarity(value, section.content)
                if score > best_score:
                    best_score = score
                    if score >= EVIDENCE_MATCH_STRONG:
                        best_confidence = "strong"
                        best_ref = HtmlEvidence(
                            selector=section.selector_hint,
                            heading_path=section.heading_path or section.heading,
                            quote=value[:200],
                            assertion_type=AssertionType.FACT,
                        )
                    elif score >= EVIDENCE_MATCH_CANDIDATE:
                        best_confidence = "candidate"
                        best_ref = HtmlEvidence(
                            selector=section.selector_hint,
                            heading_path=section.heading_path or section.heading,
                            quote=value[:200],
                            assertion_type=AssertionType.INFERRED,
                        )

        # Search in PDF pages
        if pdf_extraction:
            for page in pdf_extraction.pages:
                score = _similarity(value, page.text)
                if score > best_score:
                    best_score = score
                    if score >= EVIDENCE_MATCH_STRONG:
                        best_confidence = "strong"
                        best_ref = PdfEvidence(
                            page=page.page_number,
                            section=field_name,
                            quote=value[:200],
                            assertion_type=AssertionType.FACT,
                        )
                    elif score >= EVIDENCE_MATCH_CANDIDATE:
                        best_confidence = "candidate"
                        best_ref = PdfEvidence(
                            page=page.page_number,
                            section=field_name,
                            quote=value[:200],
                            assertion_type=AssertionType.INFERRED,
                        )

        # Levenshtein rescue for near-misses
        if best_confidence == "none" and (html_extraction or pdf_extraction):
            best_ref, best_confidence = self._levenshtein_rescue(
                value,
                field_name,
                html_extraction,
                pdf_extraction,
            )

        return EvidenceMatch(
            field_name=field_name,
            confidence=best_confidence,
            evidence_ref=best_ref,
        )

    def _levenshtein_rescue(
        self,
        value: str,
        field_name: str,
        html_extraction: HtmlExtraction | None,
        pdf_extraction: PdfExtraction | None,
    ) -> tuple[HtmlEvidence | PdfEvidence | None, str]:
        """Try Levenshtein distance as a rescue for Jaccard misses."""
        best_lev = 0.0
        best_ref = None

        if html_extraction:
            for section in html_extraction.sections:
                lev = _levenshtein_ratio(value, section.content)
                if lev > best_lev and lev >= EVIDENCE_MATCH_CANDIDATE:
                    best_lev = lev
                    best_ref = HtmlEvidence(
                        selector=section.selector_hint,
                        heading_path=section.heading_path or section.heading,
                        quote=value[:200],
                        assertion_type=AssertionType.INFERRED,
                    )

        if pdf_extraction:
            for page in pdf_extraction.pages:
                lev = _levenshtein_ratio(value, page.text)
                if lev > best_lev and lev >= EVIDENCE_MATCH_CANDIDATE:
                    best_lev = lev
                    best_ref = PdfEvidence(
                        page=page.page_number,
                        section=field_name,
                        quote=value[:200],
                        assertion_type=AssertionType.INFERRED,
                    )

        if best_ref:
            return best_ref, "candidate"
        return None, "none"
