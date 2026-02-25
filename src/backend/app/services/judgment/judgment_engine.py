"""Judgment engine for F-003.

4-phase judgment:
  Phase 1: Precondition checks (profile completeness, data quality)
  Phase 2: Hard conditions (5 mandatory requirements)
  Phase 3: Soft conditions (4 desirable attributes)
  Phase 4: Final verdict + confidence calculation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import structlog

from app.core.constants import CONFIDENCE_THRESHOLD
from app.models.company_profile import CompanyProfile
from app.schemas.evidence import AssertionType
from app.schemas.extraction import CaseCardExtraction
from app.services.judgment.grade_comparator import GRADE_ORDER, grade_meets_requirement

logger = structlog.get_logger()


@dataclass
class HardCheckResult:
    """Result of a single hard condition check."""

    rule_id: str
    label: str
    result: str  # "pass", "fail", "uncertain"
    required: str | None = None
    actual: str | None = None
    assertion_type: str | None = None
    evidence_ref: dict | None = None


@dataclass
class SoftCheckResult:
    """Result of a single soft condition check."""

    rule_id: str
    label: str
    result: str  # "pass", "gap", "unknown"
    severity: str = "low"  # "high", "medium", "low"
    required: str | None = None
    actual: str | None = None
    evidence_ref: dict | None = None


@dataclass
class JudgmentResult:
    """Full judgment outcome."""

    verdict: str  # "eligible", "ineligible", "uncertain"
    confidence: Decimal
    hard_fail_reasons: list[dict[str, Any]] = field(default_factory=list)
    soft_gaps: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: dict[str, Any] = field(default_factory=dict)
    check_details: dict[str, Any] = field(default_factory=dict)
    company_profile_snapshot: dict[str, Any] = field(default_factory=dict)


class JudgmentEngine:
    """4-phase eligibility judgment engine."""

    def judge(
        self,
        extraction: CaseCardExtraction,
        profile: CompanyProfile,
        *,
        confidence_score: float = 1.0,
    ) -> JudgmentResult:
        """Run 4-phase judgment and return the result.

        Args:
            extraction: CaseCard extraction from F-002
            profile: Company profile with permanent attributes
            confidence_score: CaseCard confidence from quality checker (0-1)
        """
        snapshot = self._build_snapshot(profile)

        # Phase 1: Preconditions
        precondition_issue = self._check_preconditions(
            extraction, profile, confidence_score,
        )
        if precondition_issue:
            return JudgmentResult(
                verdict="uncertain",
                confidence=Decimal("0.30"),
                check_details={"precondition_issue": precondition_issue},
                company_profile_snapshot=snapshot,
            )

        # Phase 2: Hard conditions
        hard_checks = self._check_hard_conditions(extraction, profile)
        hard_fails = [c for c in hard_checks if c.result == "fail"]
        hard_uncertains = [c for c in hard_checks if c.result == "uncertain"]

        # Phase 3: Soft conditions
        soft_checks = self._check_soft_conditions(extraction, profile)
        soft_gaps = [c for c in soft_checks if c.result == "gap"]
        soft_high_gaps = [g for g in soft_gaps if g.severity == "high"]

        # Phase 4: Final verdict
        verdict, confidence = self._compute_verdict(
            hard_fails, hard_uncertains, soft_gaps, soft_high_gaps, confidence_score,
        )

        return JudgmentResult(
            verdict=verdict,
            confidence=confidence,
            hard_fail_reasons=[self._check_to_dict(c) for c in hard_fails],
            soft_gaps=[self._check_to_dict(c) for c in soft_gaps],
            evidence_refs={},
            check_details={
                "hard_checks": [self._check_to_dict(c) for c in hard_checks],
                "soft_checks": [self._check_to_dict(c) for c in soft_checks],
            },
            company_profile_snapshot=snapshot,
        )

    # ------------------------------------------------------------------
    # Phase 1: Preconditions
    # ------------------------------------------------------------------
    def _check_preconditions(
        self,
        extraction: CaseCardExtraction,
        profile: CompanyProfile,
        confidence_score: float,
    ) -> str | None:
        """Return a reason string if preconditions fail, else None."""
        if not profile.unified_qualification:
            return "profile_no_qualification"

        if not profile.grade:
            return "profile_no_grade"

        if not extraction.eligibility:
            return "no_eligibility_data"

        if confidence_score < CONFIDENCE_THRESHOLD:
            return "low_confidence"

        return None

    # ------------------------------------------------------------------
    # Phase 2: Hard conditions (5 checks)
    # ------------------------------------------------------------------
    def _check_hard_conditions(
        self,
        extraction: CaseCardExtraction,
        profile: CompanyProfile,
    ) -> list[HardCheckResult]:
        """Check 5 mandatory hard conditions."""
        checks: list[HardCheckResult] = []
        elig = extraction.eligibility

        # H1: Unified qualification
        checks.append(self._check_qualification(elig, profile))

        # H2: Grade
        checks.append(self._check_grade(elig, profile))

        # H3: Business category
        checks.append(self._check_category(elig, profile))

        # H4: Region
        checks.append(self._check_region(elig, profile))

        # H5: License requirements
        checks.append(self._check_license(elig, profile))

        return checks

    def _check_qualification(self, elig, profile: CompanyProfile) -> HardCheckResult:
        required = elig.unified_qualification if elig else None
        if required is None:
            return HardCheckResult(
                rule_id="H1", label="全省庁統一資格",
                result="pass", required="不問", actual=str(profile.unified_qualification),
            )
        if required and not profile.unified_qualification:
            return HardCheckResult(
                rule_id="H1", label="全省庁統一資格",
                result="fail", required="必要", actual="なし",
            )
        return HardCheckResult(
            rule_id="H1", label="全省庁統一資格",
            result="pass", required=str(required), actual=str(profile.unified_qualification),
        )

    def _check_grade(self, elig, profile: CompanyProfile) -> HardCheckResult:
        required = elig.grade if elig else None
        if not required:
            return HardCheckResult(
                rule_id="H2", label="等級",
                result="pass", required="不問", actual=profile.grade,
            )
        # Handle unknown grades
        if required.upper() not in GRADE_ORDER:
            return HardCheckResult(
                rule_id="H2", label="等級",
                result="uncertain", required=required, actual=profile.grade,
            )
        if grade_meets_requirement(profile.grade, required):
            return HardCheckResult(
                rule_id="H2", label="等級",
                result="pass", required=required, actual=profile.grade,
            )
        return HardCheckResult(
            rule_id="H2", label="等級",
            result="fail", required=required, actual=profile.grade,
        )

    def _check_category(self, elig, profile: CompanyProfile) -> HardCheckResult:
        required = elig.business_category if elig else None
        if not required:
            return HardCheckResult(
                rule_id="H3", label="営業品目",
                result="pass", required="不問", actual=str(profile.business_categories),
            )
        # "その他" acts as a wildcard
        if required == "その他":
            return HardCheckResult(
                rule_id="H3", label="営業品目",
                result="pass", required=required, actual=str(profile.business_categories),
            )
        if required in profile.business_categories:
            return HardCheckResult(
                rule_id="H3", label="営業品目",
                result="pass", required=required, actual=str(profile.business_categories),
            )
        return HardCheckResult(
            rule_id="H3", label="営業品目",
            result="fail", required=required, actual=str(profile.business_categories),
        )

    def _check_region(self, elig, profile: CompanyProfile) -> HardCheckResult:
        required = elig.region if elig else None
        if not required:
            return HardCheckResult(
                rule_id="H4", label="地域",
                result="pass", required="不問", actual=str(profile.regions),
            )
        if required in profile.regions:
            return HardCheckResult(
                rule_id="H4", label="地域",
                result="pass", required=required, actual=str(profile.regions),
            )
        return HardCheckResult(
            rule_id="H4", label="地域",
            result="fail", required=required, actual=str(profile.regions),
        )

    def _check_license(self, elig, profile: CompanyProfile) -> HardCheckResult:
        if not elig or not elig.additional_requirements:
            return HardCheckResult(
                rule_id="H5", label="資格・免許",
                result="pass", required="なし",
            )
        license_reqs = [
            r for r in elig.additional_requirements if r.type == "license"
        ]
        if not license_reqs:
            return HardCheckResult(
                rule_id="H5", label="資格・免許",
                result="pass", required="なし",
            )
        # Check each license requirement
        profile_license_names = {
            lic.get("name", "") if isinstance(lic, dict) else str(lic)
            for lic in profile.licenses
        }
        missing = []
        for req in license_reqs:
            if req.name not in profile_license_names:
                missing.append(req.name)

        if missing:
            # If assertion_type is inferred, mark as uncertain
            assertion_types = {r.assertion_type for r in license_reqs}
            if AssertionType.INFERRED in assertion_types:
                return HardCheckResult(
                    rule_id="H5", label="資格・免許",
                    result="uncertain",
                    required=", ".join(r.name for r in license_reqs),
                    actual=str(profile_license_names),
                    assertion_type="inferred",
                )
            return HardCheckResult(
                rule_id="H5", label="資格・免許",
                result="fail",
                required=", ".join(r.name for r in license_reqs),
                actual=str(profile_license_names),
            )

        return HardCheckResult(
            rule_id="H5", label="資格・免許",
            result="pass",
            required=", ".join(r.name for r in license_reqs),
            actual=str(profile_license_names),
        )

    # ------------------------------------------------------------------
    # Phase 3: Soft conditions (4 checks)
    # ------------------------------------------------------------------
    def _check_soft_conditions(
        self,
        extraction: CaseCardExtraction,
        profile: CompanyProfile,
    ) -> list[SoftCheckResult]:
        """Check 4 desirable soft conditions."""
        checks: list[SoftCheckResult] = []
        elig = extraction.eligibility

        # S1: Experience
        checks.append(self._check_experience(elig, profile))

        # S2: Certifications (e.g., ISO, P-mark)
        checks.append(self._check_certifications(elig, profile))

        # S3: Location proximity
        checks.append(self._check_location(extraction, profile))

        # S4: Personnel
        checks.append(self._check_personnel(elig, profile))

        return checks

    def _check_experience(self, elig, profile: CompanyProfile) -> SoftCheckResult:
        if not elig or not elig.additional_requirements:
            return SoftCheckResult(
                rule_id="S1", label="実績", result="pass",
            )
        exp_reqs = [r for r in elig.additional_requirements if r.type == "experience"]
        if not exp_reqs:
            return SoftCheckResult(
                rule_id="S1", label="実績", result="pass",
            )
        # Check if company has matching experience
        profile_exp_names = {
            exp.get("name", "") if isinstance(exp, dict) else str(exp)
            for exp in profile.experience
        }
        for req in exp_reqs:
            if req.name not in profile_exp_names:
                severity = "high" if req.assertion_type == AssertionType.FACT else "low"
                return SoftCheckResult(
                    rule_id="S1", label="実績", result="gap",
                    severity=severity,
                    required=req.name,
                    actual=str(profile_exp_names) if profile_exp_names else "なし",
                )
        return SoftCheckResult(
            rule_id="S1", label="実績", result="pass",
        )

    def _check_certifications(self, elig, profile: CompanyProfile) -> SoftCheckResult:
        if not elig or not elig.additional_requirements:
            return SoftCheckResult(
                rule_id="S2", label="認証", result="pass",
            )
        cert_reqs = [r for r in elig.additional_requirements if r.type == "certification"]
        if not cert_reqs:
            return SoftCheckResult(
                rule_id="S2", label="認証", result="pass",
            )
        profile_cert_names = {
            cert.get("name", "") if isinstance(cert, dict) else str(cert)
            for cert in profile.certifications
        }
        for req in cert_reqs:
            if req.name not in profile_cert_names:
                return SoftCheckResult(
                    rule_id="S2", label="認証", result="gap",
                    severity="medium",
                    required=req.name,
                    actual=str(profile_cert_names) if profile_cert_names else "なし",
                )
        return SoftCheckResult(
            rule_id="S2", label="認証", result="pass",
        )

    def _check_location(
        self,
        extraction: CaseCardExtraction,
        profile: CompanyProfile,
    ) -> SoftCheckResult:
        if not extraction.business_content or not extraction.business_content.delivery_locations:
            return SoftCheckResult(
                rule_id="S3", label="所在地", result="pass",
            )
        # Basic check: are any delivery locations in profile regions?
        for loc in extraction.business_content.delivery_locations:
            in_region = any(r in loc.address for r in profile.regions)
            if not in_region:
                return SoftCheckResult(
                    rule_id="S3", label="所在地", result="gap",
                    severity="low",
                    required=loc.address,
                    actual=str(profile.regions),
                )
        return SoftCheckResult(
            rule_id="S3", label="所在地", result="pass",
        )

    def _check_personnel(self, elig, profile: CompanyProfile) -> SoftCheckResult:
        if not elig or not elig.additional_requirements:
            return SoftCheckResult(
                rule_id="S4", label="人員", result="pass",
            )
        personnel_reqs = [
            r for r in elig.additional_requirements if r.type == "personnel"
        ]
        if not personnel_reqs:
            return SoftCheckResult(
                rule_id="S4", label="人員", result="pass",
            )
        # No personnel data in profile currently → gap
        return SoftCheckResult(
            rule_id="S4", label="人員", result="gap",
            severity="low",
            required=", ".join(r.name for r in personnel_reqs),
        )

    # ------------------------------------------------------------------
    # Phase 4: Verdict + Confidence
    # ------------------------------------------------------------------
    def _compute_verdict(
        self,
        hard_fails: list[HardCheckResult],
        hard_uncertains: list[HardCheckResult],
        soft_gaps: list[SoftCheckResult],
        soft_high_gaps: list[SoftCheckResult],
        confidence_score: float,
    ) -> tuple[str, Decimal]:
        """Compute final verdict and confidence."""
        # Any hard fail → ineligible
        if hard_fails:
            conf = Decimal("0.90") if not hard_uncertains else Decimal("0.80")
            return "ineligible", conf

        # Any hard uncertain → uncertain
        if hard_uncertains:
            return "uncertain", Decimal("0.50")

        # High-severity soft gaps → uncertain
        if soft_high_gaps:
            return "uncertain", Decimal("0.55")

        # Calculate confidence based on soft gaps and data quality
        base = Decimal("0.90")
        gap_penalty = Decimal("0.05") * len(soft_gaps)
        data_factor = Decimal(str(min(confidence_score, 1.0)))

        confidence = max(
            base - gap_penalty,
            Decimal("0.60"),
        ) * data_factor

        # Clamp to 0.99
        confidence = min(confidence, Decimal("0.99"))

        return "eligible", confidence

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_snapshot(self, profile: CompanyProfile) -> dict[str, Any]:
        return {
            "unified_qualification": profile.unified_qualification,
            "grade": profile.grade,
            "business_categories": profile.business_categories,
            "regions": profile.regions,
            "licenses": profile.licenses,
            "certifications": profile.certifications,
        }

    @staticmethod
    def _check_to_dict(check: HardCheckResult | SoftCheckResult) -> dict[str, Any]:
        return {k: v for k, v in check.__dict__.items() if v is not None}
