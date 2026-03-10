"""Tests for QualityChecker (F-002 Stage 3)."""

from app.schemas.evidence import AssertionType
from app.schemas.extraction import (
    AdditionalRequirement,
    BusinessContentExtraction,
    CaseCardExtraction,
    EligibilityExtraction,
    RiskFactor,
    ScheduleExtraction,
    SubmissionItem,
    SubmissionItemsExtraction,
)
from app.services.reading.evidence_mapper import EvidenceMappingResult, EvidenceMatch
from app.services.reading.quality_checker import QualityChecker


def _make_full_extraction() -> CaseCardExtraction:
    return CaseCardExtraction(
        eligibility=EligibilityExtraction(
            unified_qualification=True,
            grade="C",
            business_category="物品の販売",
            region="関東・甲信越",
            additional_requirements=[
                AdditionalRequirement(
                    name="Pマーク",
                    type="certification",
                    assertion_type=AssertionType.FACT,
                ),
            ],
        ),
        schedule=ScheduleExtraction(
            submission_deadline="2026-03-15T17:00:00+09:00",
            opening_date="2026-03-20T10:00:00+09:00",
        ),
        business_content=BusinessContentExtraction(
            summary="コピー用紙購入",
            business_type="物品の販売",
        ),
        submission_items=SubmissionItemsExtraction(
            bid_time_items=[
                SubmissionItem(name="入札書", assertion_type=AssertionType.FACT),
            ],
        ),
        risk_factors=[],
    )


def _make_evidence_result(rate: float, num_matches: int = 5) -> EvidenceMappingResult:
    """Create an EvidenceMappingResult with a given rate."""
    matches = []
    matched_count = int(num_matches * rate)
    for i in range(num_matches):
        matches.append(
            EvidenceMatch(
                field_name=f"field_{i}",
                confidence="strong" if i < matched_count else "none",
            ),
        )
    return EvidenceMappingResult(matches=matches)


class TestQualityChecker:
    def test_full_evidence_high_confidence(self) -> None:
        extraction = _make_full_extraction()
        evidence = _make_evidence_result(rate=1.0, num_matches=5)
        checker = QualityChecker()

        result = checker.compute(extraction, evidence)

        assert result.confidence_score > 0.6
        assert result.needs_review is False

    def test_partial_evidence_medium_confidence(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                unified_qualification=True,
                grade="C",
            ),
        )
        evidence = _make_evidence_result(rate=0.5, num_matches=4)
        checker = QualityChecker()

        result = checker.compute(extraction, evidence)

        assert 0.0 < result.confidence_score < 1.0

    def test_below_threshold_needs_review(self) -> None:
        extraction = CaseCardExtraction()
        evidence = _make_evidence_result(rate=0.0)
        checker = QualityChecker()

        result = checker.compute(extraction, evidence)

        assert result.confidence_score < 0.6
        assert result.needs_review is True

    def test_assertion_counts(self) -> None:
        extraction = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="Pマーク",
                        type="certification",
                        assertion_type=AssertionType.FACT,
                    ),
                    AdditionalRequirement(
                        name="ISO27001",
                        type="certification",
                        assertion_type=AssertionType.INFERRED,
                    ),
                ],
            ),
            submission_items=SubmissionItemsExtraction(
                bid_time_items=[
                    SubmissionItem(name="入札書", assertion_type=AssertionType.FACT),
                ],
            ),
            risk_factors=[
                RiskFactor(
                    risk_type="test",
                    label="test",
                    severity="low",
                    description="test",
                    assertion_type=AssertionType.CAUTION,
                ),
            ],
        )
        evidence = _make_evidence_result(rate=0.5)
        checker = QualityChecker()

        result = checker.compute(extraction, evidence)

        assert result.assertion_counts["fact"] == 2
        assert result.assertion_counts["inferred"] == 1
        assert result.assertion_counts["caution"] == 1

    def test_risk_level_high(self) -> None:
        extraction = CaseCardExtraction(
            risk_factors=[
                RiskFactor(
                    risk_type="urgent",
                    label="緊急",
                    severity="high",
                    description="期限迫り",
                ),
            ],
        )
        evidence = _make_evidence_result(rate=0.5)
        checker = QualityChecker()

        result = checker.compute(extraction, evidence)
        assert result.risk_level == "high"

    def test_risk_level_medium(self) -> None:
        extraction = CaseCardExtraction(
            risk_factors=[
                RiskFactor(
                    risk_type="complexity",
                    label="複雑",
                    severity="medium",
                    description="要件が多い",
                ),
            ],
        )
        evidence = _make_evidence_result(rate=0.5)
        checker = QualityChecker()

        result = checker.compute(extraction, evidence)
        assert result.risk_level == "medium"

    def test_risk_level_low_when_no_risks(self) -> None:
        extraction = CaseCardExtraction()
        evidence = _make_evidence_result(rate=0.5)
        checker = QualityChecker()

        result = checker.compute(extraction, evidence)
        assert result.risk_level == "low"

    def test_confidence_score_bounds(self) -> None:
        """Confidence score should always be 0.0 to 1.0."""
        checker = QualityChecker()

        # Minimum case
        result_min = checker.compute(
            CaseCardExtraction(),
            _make_evidence_result(rate=0.0),
        )
        assert 0.0 <= result_min.confidence_score <= 1.0

        # Maximum case
        result_max = checker.compute(
            _make_full_extraction(),
            _make_evidence_result(rate=1.0),
        )
        assert 0.0 <= result_max.confidence_score <= 1.0
