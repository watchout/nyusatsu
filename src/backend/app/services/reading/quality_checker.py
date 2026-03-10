"""Quality checker for F-002 Stage 3.

Computes confidence score and risk level from extraction + evidence results.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import CONFIDENCE_THRESHOLD
from app.schemas.extraction import CaseCardExtraction
from app.services.reading.evidence_mapper import EvidenceMappingResult


@dataclass(frozen=True)
class QualityResult:
    """Quality assessment of an extraction."""

    confidence_score: float
    assertion_counts: dict[str, int]
    risk_level: str  # "high", "medium", "low"
    needs_review: bool


class QualityChecker:
    """Compute quality metrics for extraction results."""

    def compute(
        self,
        extraction: CaseCardExtraction,
        evidence_result: EvidenceMappingResult,
    ) -> QualityResult:
        """Compute quality result from extraction and evidence mapping."""
        assertion_counts = self._count_assertions(extraction)
        confidence = self._compute_confidence(extraction, evidence_result)
        risk_level = self._determine_risk_level(extraction)
        needs_review = confidence < CONFIDENCE_THRESHOLD

        return QualityResult(
            confidence_score=round(confidence, 2),
            assertion_counts=assertion_counts,
            risk_level=risk_level,
            needs_review=needs_review,
        )

    @staticmethod
    def _count_assertions(extraction: CaseCardExtraction) -> dict[str, int]:
        """Count assertion types across all extracted fields."""
        counts = {"fact": 0, "inferred": 0, "caution": 0}

        if extraction.eligibility:
            for req in extraction.eligibility.additional_requirements:
                counts[req.assertion_type.value] += 1

        if extraction.submission_items:
            for item in extraction.submission_items.bid_time_items:
                counts[item.assertion_type.value] += 1
            for item in extraction.submission_items.performance_time_items:
                counts[item.assertion_type.value] += 1

        for rf in extraction.risk_factors:
            counts[rf.assertion_type.value] += 1

        return counts

    @staticmethod
    def _compute_confidence(
        extraction: CaseCardExtraction,
        evidence_result: EvidenceMappingResult,
    ) -> float:
        """Compute confidence score (0.0 to 1.0).

        Based on:
        - Evidence match rate (40%)
        - Field completeness (40%)
        - Assertion quality (20%)
        """
        # Evidence rate component
        evidence_score = evidence_result.evidence_rate

        # Field completeness component
        total_fields = 0
        filled_fields = 0

        if extraction.eligibility:
            total_fields += 4
            if extraction.eligibility.unified_qualification is not None:
                filled_fields += 1
            if extraction.eligibility.grade:
                filled_fields += 1
            if extraction.eligibility.business_category:
                filled_fields += 1
            if extraction.eligibility.region:
                filled_fields += 1
        else:
            total_fields += 4

        if extraction.schedule:
            total_fields += 2
            if extraction.schedule.submission_deadline:
                filled_fields += 1
            if extraction.schedule.opening_date:
                filled_fields += 1
        else:
            total_fields += 2

        if extraction.business_content:
            total_fields += 2
            if extraction.business_content.summary:
                filled_fields += 1
            if extraction.business_content.business_type:
                filled_fields += 1
        else:
            total_fields += 2

        completeness = filled_fields / total_fields if total_fields > 0 else 0.0

        # Assertion quality component
        counts = QualityChecker._count_assertions(extraction)
        total_assertions = sum(counts.values())
        if total_assertions > 0:
            fact_ratio = counts["fact"] / total_assertions
            caution_penalty = counts["caution"] / total_assertions * 0.5
            assertion_score = fact_ratio - caution_penalty
        else:
            assertion_score = 0.5  # No assertions = neutral

        confidence = (
            evidence_score * 0.4
            + completeness * 0.4
            + max(0.0, assertion_score) * 0.2
        )
        return min(1.0, max(0.0, confidence))

    @staticmethod
    def _determine_risk_level(extraction: CaseCardExtraction) -> str:
        """Determine risk level from risk factors."""
        if not extraction.risk_factors:
            return "low"
        severities = [rf.severity for rf in extraction.risk_factors]
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"
