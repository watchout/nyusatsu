"""Tests for extraction schema (Wave 0 contract validation)."""

from app.schemas.evidence import AssertionType
from app.schemas.extraction import (
    AdditionalRequirement,
    BusinessContentExtraction,
    CaseCardExtraction,
    DeliveryItem,
    DeliveryLocation,
    EligibilityExtraction,
    RiskFactor,
    ScheduleExtraction,
    SubmissionItem,
    SubmissionItemsExtraction,
)


class TestCaseCardExtraction:
    def test_full_extraction(self) -> None:
        ext = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                unified_qualification=True,
                grade="D",
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
                submission_deadline="2026-03-15T17:00:00Z",
                opening_date="2026-03-20T10:00:00Z",
            ),
            business_content=BusinessContentExtraction(
                business_type="物品の販売",
                summary="コピー用紙購入",
                items=[DeliveryItem(name="コピー用紙", quantity="30箱")],
                delivery_locations=[
                    DeliveryLocation(address="東京都千代田区"),
                ],
                has_quote_requirement=True,
            ),
            submission_items=SubmissionItemsExtraction(
                bid_time_items=[
                    SubmissionItem(
                        name="入札書",
                        template_source="発注機関指定書式",
                        assertion_type=AssertionType.FACT,
                    ),
                ],
                performance_time_items=[
                    SubmissionItem(
                        name="業務計画書",
                        assertion_type=AssertionType.INFERRED,
                    ),
                ],
            ),
            risk_factors=[
                RiskFactor(
                    risk_type="quote_deadline_urgent",
                    label="下見積もり期限迫り",
                    severity="high",
                    description="期限が3日以内",
                    assertion_type=AssertionType.FACT,
                ),
            ],
        )
        assert ext.eligibility is not None
        assert ext.eligibility.grade == "D"
        assert len(ext.risk_factors) == 1
        assert ext.submission_items is not None
        assert len(ext.submission_items.bid_time_items) == 1

    def test_partial_extraction_nulls_allowed(self) -> None:
        ext = CaseCardExtraction(
            eligibility=EligibilityExtraction(
                unified_qualification=True,
            ),
        )
        assert ext.schedule is None
        assert ext.business_content is None
        assert ext.submission_items is None
        assert ext.risk_factors == []
        assert ext.eligibility.grade is None
        assert ext.eligibility.region is None

    def test_empty_extraction(self) -> None:
        ext = CaseCardExtraction()
        assert ext.eligibility is None
        assert ext.schedule is None
        assert ext.business_content is None
        assert ext.submission_items is None
        assert ext.risk_factors == []

    def test_assertion_type_on_additional_requirements(self) -> None:
        req = AdditionalRequirement(
            name="ISO27001",
            type="certification",
            assertion_type=AssertionType.CAUTION,
        )
        assert req.assertion_type == AssertionType.CAUTION

    def test_assertion_type_default_on_submission_item(self) -> None:
        item = SubmissionItem(name="入札書")
        assert item.assertion_type == AssertionType.INFERRED

    def test_risk_factor_fields(self) -> None:
        rf = RiskFactor(
            risk_type="pmark_requirement",
            label="Pマーク要件",
            severity="high",
            description="必須",
        )
        assert rf.severity == "high"
        assert rf.assertion_type == AssertionType.INFERRED  # default
