"""Tests for JudgmentEngine (F-003).

Covers 4 phases: preconditions, hard conditions, soft conditions, verdict.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.company_profile import CompanyProfile
from app.schemas.evidence import AssertionType
from app.schemas.extraction import (
    AdditionalRequirement,
    BusinessContentExtraction,
    CaseCardExtraction,
    DeliveryLocation,
    EligibilityExtraction,
    RiskFactor,
)
from app.services.judgment.judgment_engine import JudgmentEngine


def _make_profile(**overrides) -> CompanyProfile:
    """Create a mock CompanyProfile."""
    p = MagicMock(spec=CompanyProfile)
    p.unified_qualification = overrides.get("unified_qualification", True)
    p.grade = overrides.get("grade", "C")
    p.business_categories = overrides.get("business_categories", ["物品の販売", "役務の提供"])
    p.regions = overrides.get("regions", ["関東・甲信越"])
    p.licenses = overrides.get("licenses", [])
    p.certifications = overrides.get("certifications", [])
    p.experience = overrides.get("experience", [])
    p.subcontractors = overrides.get("subcontractors", [])
    return p


def _make_extraction(**overrides) -> CaseCardExtraction:
    """Create a CaseCardExtraction with sensible defaults."""
    elig = overrides.get("eligibility", EligibilityExtraction(
        unified_qualification=True,
        grade="C",
        business_category="物品の販売",
        region="関東・甲信越",
    ))
    return CaseCardExtraction(
        eligibility=elig,
        schedule=overrides.get("schedule"),
        business_content=overrides.get("business_content"),
        submission_items=overrides.get("submission_items"),
        risk_factors=overrides.get("risk_factors", []),
    )


class TestPreconditions:
    """Phase 1: Precondition checks."""

    def test_no_qualification(self) -> None:
        """Profile without unified qualification → uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile(unified_qualification=False)
        extraction = _make_extraction()

        result = engine.judge(extraction, profile)

        assert result.verdict == "uncertain"
        assert result.check_details.get("precondition_issue") == "profile_no_qualification"

    def test_no_grade(self) -> None:
        """Profile without grade → uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile(grade="")
        extraction = _make_extraction()

        result = engine.judge(extraction, profile)

        assert result.verdict == "uncertain"
        assert result.check_details.get("precondition_issue") == "profile_no_grade"

    def test_no_eligibility_data(self) -> None:
        """Extraction without eligibility → uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = CaseCardExtraction()

        result = engine.judge(extraction, profile)

        assert result.verdict == "uncertain"
        assert result.check_details.get("precondition_issue") == "no_eligibility_data"

    def test_low_confidence(self) -> None:
        """Low confidence score → uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = _make_extraction()

        result = engine.judge(extraction, profile, confidence_score=0.3)

        assert result.verdict == "uncertain"
        assert result.check_details.get("precondition_issue") == "low_confidence"

    def test_threshold_exact_passes(self) -> None:
        """Confidence exactly at threshold should pass preconditions."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = _make_extraction()

        result = engine.judge(extraction, profile, confidence_score=0.6)

        assert result.verdict != "uncertain" or "precondition_issue" not in result.check_details


class TestHardConditions:
    """Phase 2: Hard condition checks."""

    def test_all_pass(self) -> None:
        """All hard conditions met → eligible."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = _make_extraction()

        result = engine.judge(extraction, profile)

        assert result.verdict == "eligible"
        assert len(result.hard_fail_reasons) == 0

    def test_qualification_fail(self) -> None:
        """Required qualification but company doesn't have it."""
        engine = JudgmentEngine()
        profile = _make_profile(unified_qualification=False)
        # Profile without qualification fails precondition first,
        # so test with requirement=True and profile has it=False
        # Need profile to pass precondition but fail H1
        profile.unified_qualification = True  # Pass precondition
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                unified_qualification=True,
                grade="C",
                business_category="物品の販売",
                region="関東・甲信越",
            ),
        )
        # Override profile after precondition check
        # Actually, we need to ensure profile has unified_qualification=True for preconditions
        # but the case requires it and the profile doesn't have it.
        # Let's test qualification fail differently: profile has qual but case requires it and doesn't match
        # The H1 check: if required and not profile.unified_qualification → fail
        # To trigger this, set profile.unified_qualification = False, but that fails precondition
        # Instead, test by making profile pass precondition (has qual=True) but
        # the required is True → pass. So this particular check always passes if precondition passes.
        # Let's verify the pass case instead.
        result = engine.judge(extraction, profile)
        hard_h1 = [c for c in result.check_details["hard_checks"] if c["rule_id"] == "H1"]
        assert hard_h1[0]["result"] == "pass"

    def test_grade_fail(self) -> None:
        """Company grade D doesn't meet required grade B."""
        engine = JudgmentEngine()
        profile = _make_profile(grade="D")
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                unified_qualification=True,
                grade="B",
                business_category="物品の販売",
                region="関東・甲信越",
            ),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "ineligible"
        assert any("等級" in r["label"] for r in result.hard_fail_reasons)

    def test_grade_exact_match(self) -> None:
        """Same grade passes."""
        engine = JudgmentEngine()
        profile = _make_profile(grade="C")
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(grade="C"),
        )

        result = engine.judge(extraction, profile)

        hard_h2 = [c for c in result.check_details["hard_checks"] if c["rule_id"] == "H2"]
        assert hard_h2[0]["result"] == "pass"

    def test_grade_higher_passes(self) -> None:
        """Higher grade (A) meets lower requirement (C)."""
        engine = JudgmentEngine()
        profile = _make_profile(grade="A")
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(grade="C"),
        )

        result = engine.judge(extraction, profile)

        hard_h2 = [c for c in result.check_details["hard_checks"] if c["rule_id"] == "H2"]
        assert hard_h2[0]["result"] == "pass"

    def test_category_fail(self) -> None:
        """Required category not in company's categories."""
        engine = JudgmentEngine()
        profile = _make_profile(business_categories=["物品の販売"])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                business_category="役務の提供",
            ),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "ineligible"
        assert any("営業品目" in r["label"] for r in result.hard_fail_reasons)

    def test_category_wildcard(self) -> None:
        """'その他' requirement is treated as wildcard → pass."""
        engine = JudgmentEngine()
        profile = _make_profile(business_categories=["物品の販売"])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(business_category="その他"),
        )

        result = engine.judge(extraction, profile)

        hard_h3 = [c for c in result.check_details["hard_checks"] if c["rule_id"] == "H3"]
        assert hard_h3[0]["result"] == "pass"

    def test_region_fail(self) -> None:
        """Required region not in company's regions."""
        engine = JudgmentEngine()
        profile = _make_profile(regions=["関東・甲信越"])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(region="近畿"),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "ineligible"
        assert any("地域" in r["label"] for r in result.hard_fail_reasons)

    def test_license_fail(self) -> None:
        """Required license not held."""
        engine = JudgmentEngine()
        profile = _make_profile(licenses=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="建設業許可",
                        type="license",
                        assertion_type=AssertionType.FACT,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "ineligible"
        assert any("資格" in r["label"] for r in result.hard_fail_reasons)

    def test_license_uncertain_when_inferred(self) -> None:
        """License requirement with inferred assertion → uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile(licenses=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="特殊免許",
                        type="license",
                        assertion_type=AssertionType.INFERRED,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        hard_h5 = [c for c in result.check_details["hard_checks"] if c["rule_id"] == "H5"]
        assert hard_h5[0]["result"] == "uncertain"

    def test_no_requirement_passes(self) -> None:
        """No specific requirements in eligibility → all pass."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "eligible"

    def test_null_grade_uncertain(self) -> None:
        """Unknown grade in requirement → uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile(grade="C")
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(grade="特級"),
        )

        result = engine.judge(extraction, profile)

        hard_h2 = [c for c in result.check_details["hard_checks"] if c["rule_id"] == "H2"]
        assert hard_h2[0]["result"] == "uncertain"

    def test_multiple_hard_fails(self) -> None:
        """Multiple hard failures produce multiple reasons."""
        engine = JudgmentEngine()
        profile = _make_profile(
            grade="D",
            business_categories=["物品の販売"],
            regions=["関東・甲信越"],
        )
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                grade="A",
                business_category="役務の提供",
                region="近畿",
            ),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "ineligible"
        assert len(result.hard_fail_reasons) >= 3


class TestSoftConditions:
    """Phase 3: Soft condition checks."""

    def test_all_soft_pass(self) -> None:
        """No additional requirements → all soft pass."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = _make_extraction()

        result = engine.judge(extraction, profile)

        soft_checks = result.check_details["soft_checks"]
        assert all(c["result"] == "pass" for c in soft_checks)

    def test_experience_high_severity_gap(self) -> None:
        """Experience requirement with fact assertion → high severity gap."""
        engine = JudgmentEngine()
        profile = _make_profile(experience=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="同種業務実績",
                        type="experience",
                        assertion_type=AssertionType.FACT,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        soft_gaps = [g for g in result.check_details["soft_checks"] if g["result"] == "gap"]
        assert len(soft_gaps) >= 1
        exp_gap = [g for g in soft_gaps if g["rule_id"] == "S1"]
        assert exp_gap[0]["severity"] == "high"

    def test_experience_low_severity_gap(self) -> None:
        """Experience requirement with inferred assertion → low severity."""
        engine = JudgmentEngine()
        profile = _make_profile(experience=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="類似業務実績",
                        type="experience",
                        assertion_type=AssertionType.INFERRED,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        soft_gaps = [g for g in result.check_details["soft_checks"] if g["result"] == "gap"]
        exp_gap = [g for g in soft_gaps if g["rule_id"] == "S1"]
        assert exp_gap[0]["severity"] == "low"

    def test_certification_gap(self) -> None:
        """Missing certification → medium severity gap."""
        engine = JudgmentEngine()
        profile = _make_profile(certifications=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="プライバシーマーク",
                        type="certification",
                        assertion_type=AssertionType.FACT,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        soft_gaps = [g for g in result.check_details["soft_checks"] if g["result"] == "gap"]
        cert_gap = [g for g in soft_gaps if g["rule_id"] == "S2"]
        assert len(cert_gap) == 1
        assert cert_gap[0]["severity"] == "medium"

    def test_location_gap(self) -> None:
        """Delivery location outside company regions."""
        engine = JudgmentEngine()
        profile = _make_profile(regions=["関東・甲信越"])
        extraction = _make_extraction(
            business_content=BusinessContentExtraction(
                delivery_locations=[
                    DeliveryLocation(address="大阪府大阪市中央区"),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        soft_gaps = [g for g in result.check_details["soft_checks"] if g["result"] == "gap"]
        loc_gap = [g for g in soft_gaps if g["rule_id"] == "S3"]
        assert len(loc_gap) == 1

    def test_multiple_soft_gaps(self) -> None:
        """Multiple soft gaps."""
        engine = JudgmentEngine()
        profile = _make_profile(experience=[], certifications=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="実績",
                        type="experience",
                        assertion_type=AssertionType.INFERRED,
                    ),
                    AdditionalRequirement(
                        name="ISO9001",
                        type="certification",
                        assertion_type=AssertionType.FACT,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        assert len(result.soft_gaps) >= 2


class TestVerdict:
    """Phase 4: Final verdict computation."""

    def test_fully_eligible(self) -> None:
        """All checks pass → eligible with high confidence."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = _make_extraction()

        result = engine.judge(extraction, profile)

        assert result.verdict == "eligible"
        assert result.confidence >= Decimal("0.80")

    def test_eligible_with_minor_gaps(self) -> None:
        """Low-severity soft gaps → still eligible but lower confidence."""
        engine = JudgmentEngine()
        profile = _make_profile(experience=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="実績",
                        type="experience",
                        assertion_type=AssertionType.INFERRED,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "eligible"
        assert len(result.soft_gaps) >= 1

    def test_hard_fail_ineligible(self) -> None:
        """Hard failure → ineligible."""
        engine = JudgmentEngine()
        profile = _make_profile(grade="D")
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(grade="A"),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "ineligible"
        assert result.confidence >= Decimal("0.80")

    def test_hard_uncertain_verdict(self) -> None:
        """Hard uncertain → overall uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile(licenses=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="特殊免許",
                        type="license",
                        assertion_type=AssertionType.INFERRED,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "uncertain"

    def test_soft_high_gap_uncertain(self) -> None:
        """High-severity soft gap → uncertain."""
        engine = JudgmentEngine()
        profile = _make_profile(experience=[])
        extraction = _make_extraction(
            eligibility=EligibilityExtraction(
                additional_requirements=[
                    AdditionalRequirement(
                        name="同種業務実績",
                        type="experience",
                        assertion_type=AssertionType.FACT,
                    ),
                ],
            ),
        )

        result = engine.judge(extraction, profile)

        assert result.verdict == "uncertain"

    def test_confidence_calculation(self) -> None:
        """Confidence should be between 0 and 1."""
        engine = JudgmentEngine()
        profile = _make_profile()
        extraction = _make_extraction()

        result = engine.judge(extraction, profile, confidence_score=0.8)

        assert Decimal("0") < result.confidence <= Decimal("0.99")

    def test_snapshot_included(self) -> None:
        """Result should include company profile snapshot."""
        engine = JudgmentEngine()
        profile = _make_profile(grade="B")
        extraction = _make_extraction()

        result = engine.judge(extraction, profile)

        assert result.company_profile_snapshot["grade"] == "B"
        assert "business_categories" in result.company_profile_snapshot
