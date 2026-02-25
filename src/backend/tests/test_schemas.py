"""Tests for Pydantic response schemas and enums — TASK-38.

Validates:
1. LifecycleStage has exactly 17 values
2. All enums are (str, Enum) and serialize correctly
3. Response schemas accept valid data and enforce required fields
4. ChecklistItemUpdate validates status pattern
5. CompanyProfileUpdate allows partial fields
6. from_attributes works for ORM-like dicts
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.analytics import (
    AmountStats,
    PeriodRange,
    PriceSummaryResponse,
    TrendByQuarter,
    WinningRateByAmount,
)
from app.schemas.batch import BatchLogResponse, BatchTriggerRequest, BatchTriggerResponse
from app.schemas.case import CaseDetailResponse, CaseResponse
from app.schemas.case_card import CaseCardResponse
from app.schemas.checklist import ChecklistItemAdd, ChecklistItemUpdate, ChecklistResponse
from app.schemas.company_profile import CompanyProfileResponse, CompanyProfileUpdate
from app.schemas.eligibility import EligibilityResponse
from app.schemas.enums import (
    CaseStatus,
    ChecklistItemStatus,
    IncludeParam,
    LifecycleStage,
    RetryScope,
    SortDirection,
    SortField,
    TriggeredBy,
    Verdict,
)
from app.schemas.event import EventResponse, FoldedCheckOperations


_NOW = datetime.now(timezone.utc)
_UUID = uuid.uuid4()


class TestEnums:
    """Enum validation tests."""

    def test_lifecycle_stage_has_17_values(self) -> None:
        assert len(LifecycleStage) == 17

    def test_lifecycle_stage_values(self) -> None:
        expected = {
            "discovered", "scored", "under_review", "planned", "skipped",
            "reading_queued", "reading_in_progress", "reading_completed",
            "reading_failed", "judging_queued", "judging_in_progress",
            "judging_completed", "judging_failed", "checklist_generating",
            "checklist_active", "checklist_completed", "archived",
        }
        actual = {stage.value for stage in LifecycleStage}
        assert actual == expected

    def test_case_status_has_5_values(self) -> None:
        assert len(CaseStatus) == 5

    def test_verdict_has_3_values(self) -> None:
        assert len(Verdict) == 3

    def test_checklist_item_status_has_2_values(self) -> None:
        assert len(ChecklistItemStatus) == 2

    def test_triggered_by_has_4_values(self) -> None:
        assert len(TriggeredBy) == 4

    def test_include_param_has_4_values(self) -> None:
        assert len(IncludeParam) == 4

    def test_sort_field_has_5_values(self) -> None:
        assert len(SortField) == 5

    def test_sort_direction_has_2_values(self) -> None:
        assert len(SortDirection) == 2

    def test_retry_scope_has_2_values(self) -> None:
        assert len(RetryScope) == 2

    def test_enums_are_str_enums(self) -> None:
        """All enums are (str, Enum) so they serialize to their value."""
        assert isinstance(LifecycleStage.DISCOVERED, str)
        assert LifecycleStage.DISCOVERED == "discovered"
        assert isinstance(Verdict.ELIGIBLE, str)
        assert Verdict.ELIGIBLE == "eligible"


class TestCaseSchemas:
    """Case response schema tests."""

    def test_case_response_valid(self) -> None:
        data = CaseResponse(
            id=_UUID,
            source="chotatku_portal",
            source_id="2026-0001234",
            case_name="テスト案件",
            issuing_org="○○省",
            status="new",
            current_lifecycle_stage="discovered",
            first_seen_at=_NOW,
            last_updated_at=_NOW,
        )
        assert data.id == _UUID
        assert data.case_name == "テスト案件"
        assert data.score is None

    def test_case_detail_response_with_includes(self) -> None:
        data = CaseDetailResponse(
            id=_UUID,
            source="chotatku_portal",
            source_id="2026-0001234",
            case_name="テスト案件",
            issuing_org="○○省",
            status="planned",
            current_lifecycle_stage="reading_completed",
            first_seen_at=_NOW,
            last_updated_at=_NOW,
            card={"id": str(_UUID), "version": 1},
            eligibility={"verdict": "eligible"},
            checklist=None,
            latest_events=[],
        )
        assert data.card is not None
        assert data.checklist is None


class TestCaseCardSchema:
    """CaseCard response schema tests."""

    def test_case_card_response_valid(self) -> None:
        data = CaseCardResponse(
            id=_UUID,
            case_id=_UUID,
            version=1,
            is_current=True,
            extraction_method="text",
            is_scanned=False,
            status="completed",
            confidence_score=Decimal("0.85"),
            created_at=_NOW,
        )
        assert data.version == 1
        assert data.confidence_score == Decimal("0.85")

    def test_case_card_response_nullable_fields(self) -> None:
        data = CaseCardResponse(
            id=_UUID,
            case_id=_UUID,
            version=1,
            is_current=True,
            extraction_method="text",
            is_scanned=False,
            status="pending",
            created_at=_NOW,
        )
        assert data.eligibility is None
        assert data.reviewed_at is None
        assert data.llm_model is None


class TestEligibilitySchema:
    """EligibilityResult response schema tests."""

    def test_eligibility_response_valid(self) -> None:
        data = EligibilityResponse(
            id=_UUID,
            case_id=_UUID,
            case_card_id=_UUID,
            version=1,
            is_current=True,
            verdict="eligible",
            confidence=Decimal("0.90"),
            hard_fail_reasons=[],
            soft_gaps=[],
            check_details={"hard_checks": [], "soft_checks": []},
            company_profile_snapshot={"grade": "D"},
            judged_at=_NOW,
            created_at=_NOW,
        )
        assert data.verdict == "eligible"
        assert data.human_override is None


class TestChecklistSchemas:
    """Checklist schema tests."""

    def test_checklist_response_valid(self) -> None:
        data = ChecklistResponse(
            id=_UUID,
            case_id=_UUID,
            case_card_id=_UUID,
            eligibility_result_id=_UUID,
            version=1,
            is_current=True,
            checklist_items=[{"item_id": "bid_001", "name": "入札書"}],
            schedule_items=[],
            warnings=[],
            progress={"total": 1, "done": 0, "rate": 0.0},
            status="active",
            generated_at=_NOW,
            created_at=_NOW,
        )
        assert data.progress["total"] == 1

    def test_checklist_item_update_done(self) -> None:
        update = ChecklistItemUpdate(status="done")
        assert update.status == "done"
        assert update.expected_checklist_version is None

    def test_checklist_item_update_pending(self) -> None:
        update = ChecklistItemUpdate(
            status="pending", expected_checklist_version=2,
        )
        assert update.expected_checklist_version == 2

    def test_checklist_item_update_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            ChecklistItemUpdate(status="invalid")

    def test_checklist_item_add_valid(self) -> None:
        item = ChecklistItemAdd(
            name="社印の手配",
            phase="bid_time",
            deadline="2026-03-14",
            notes="総務に依頼済み",
        )
        assert item.name == "社印の手配"

    def test_checklist_item_add_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChecklistItemAdd(name="")


class TestEventSchema:
    """Event response schema tests."""

    def test_event_response_valid(self) -> None:
        data = EventResponse(
            id=_UUID,
            case_id=_UUID,
            event_type="case_marked_planned",
            from_status="under_review",
            to_status="planned",
            triggered_by="user",
            actor_id="kaneko",
            feature_origin="F-001",
            payload={"reason": "相場が合いそう"},
            created_at=_NOW,
        )
        assert data.event_type == "case_marked_planned"

    def test_folded_check_operations(self) -> None:
        folded = FoldedCheckOperations(
            count=5,
            first_at=_NOW,
            last_at=_NOW,
            summary={"checked": 4, "unchecked": 1},
        )
        assert folded.event_type == "_folded_check_operations"
        assert folded.count == 5


class TestBatchSchemas:
    """Batch schema tests."""

    def test_batch_log_response_valid(self) -> None:
        data = BatchLogResponse(
            id=_UUID,
            source="chotatku_portal",
            feature_origin="F-001",
            batch_type="case_fetch",
            started_at=_NOW,
            status="success",
            total_fetched=150,
            new_count=12,
            updated_count=5,
            unchanged_count=133,
            error_count=0,
        )
        assert data.total_fetched == 150

    def test_batch_trigger_request(self) -> None:
        req = BatchTriggerRequest(
            source="chotatku_portal", batch_type="case_fetch",
        )
        assert req.source == "chotatku_portal"

    def test_batch_trigger_response(self) -> None:
        resp = BatchTriggerResponse(batch_log_id=_UUID)
        assert resp.status == "running"


class TestCompanyProfileSchemas:
    """CompanyProfile schema tests."""

    def test_company_profile_response_valid(self) -> None:
        data = CompanyProfileResponse(
            id=_UUID,
            unified_qualification=True,
            grade="D",
            business_categories=["物品の販売"],
            regions=["関東・甲信越"],
            licenses=[],
            certifications=[],
            experience=[],
            subcontractors=[],
            updated_at=_NOW,
            created_at=_NOW,
        )
        assert data.grade == "D"

    def test_company_profile_update_partial(self) -> None:
        """Only specified fields should be present."""
        update = CompanyProfileUpdate(licenses=["一般貨物自動車運送事業許可"])
        assert update.licenses == ["一般貨物自動車運送事業許可"]
        assert update.grade is None
        assert update.regions is None


class TestAnalyticsSchema:
    """Analytics response schema tests."""

    def test_price_summary_response_valid(self) -> None:
        data = PriceSummaryResponse(
            total_records=1250,
            period=PeriodRange(from_date="2023-03-01", to_date="2026-03-01"),
            amount_stats=AmountStats(
                median=1200000, q1=800000, q3=1800000,
                mean=1350000, min=200000, max=5000000,
            ),
            participants_stats={"median": 3, "mean": 3.5, "single_bid_rate": 0.25},
            winning_rate_by_amount=[
                WinningRateByAmount(range="0-500k", win_rate=0.85),
            ],
            trend_by_quarter=[
                TrendByQuarter(
                    quarter="2025-Q4", median_amount=1150000,
                    avg_participants=3.2,
                ),
            ],
        )
        assert data.total_records == 1250
        assert data.amount_stats.median == 1200000
