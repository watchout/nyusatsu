"""Tests for TASK-10: EventService — atomic event recording."""

from __future__ import annotations

import pytest

from app.core.errors import InvalidTransitionError, StageMismatchError
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.services.event_service import EventService


@pytest.fixture
def event_service():
    return EventService()


@pytest.fixture
async def fresh_case(db):
    """Create a case in 'discovered' stage."""
    case = Case(
        source="test",
        source_id="evt-test-001",
        case_name="EventService Test Case",
        issuing_org="Test Org",
        current_lifecycle_stage="discovered",
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return case


@pytest.mark.anyio
class TestEventServiceTransitions:
    """Test record_transition method."""

    async def test_record_transition_creates_event(
        self, db, fresh_case, event_service,
    ):
        """CaseEvent is created with correct fields."""
        event = await event_service.record_transition(
            db,
            case=fresh_case,
            to_stage="scored",
            triggered_by="batch",
            feature_origin="F-001",
        )
        assert isinstance(event, CaseEvent)
        assert event.event_type == "case_scored"
        assert event.from_status == "discovered"
        assert event.to_status == "scored"
        assert event.triggered_by == "batch"
        assert event.feature_origin == "F-001"

    async def test_record_transition_updates_case_stage(
        self, db, fresh_case, event_service,
    ):
        """case.current_lifecycle_stage is updated to target stage."""
        await event_service.record_transition(
            db,
            case=fresh_case,
            to_stage="scored",
            triggered_by="batch",
            feature_origin="F-001",
        )
        assert fresh_case.current_lifecycle_stage == "scored"

    async def test_expected_stage_mismatch_raises(
        self, db, fresh_case, event_service,
    ):
        """StageMismatchError when expected != actual."""
        with pytest.raises(StageMismatchError) as exc_info:
            await event_service.record_transition(
                db,
                case=fresh_case,
                to_stage="scored",
                triggered_by="batch",
                feature_origin="F-001",
                expected_lifecycle_stage="scored",  # actual is "discovered"
            )
        assert "Stage mismatch" in exc_info.value.message
        assert exc_info.value.details["expected"] == "scored"
        assert exc_info.value.details["actual"] == "discovered"

    async def test_expected_stage_none_skips_check(
        self, db, fresh_case, event_service,
    ):
        """No error when expected_lifecycle_stage is None."""
        event = await event_service.record_transition(
            db,
            case=fresh_case,
            to_stage="scored",
            triggered_by="batch",
            feature_origin="F-001",
            expected_lifecycle_stage=None,
        )
        assert event.to_status == "scored"

    async def test_invalid_transition_raises(
        self, db, fresh_case, event_service,
    ):
        """InvalidTransitionError for undefined transition."""
        with pytest.raises(InvalidTransitionError):
            await event_service.record_transition(
                db,
                case=fresh_case,
                to_stage="planned",  # discovered → planned is invalid
                triggered_by="user",
                feature_origin="F-001",
            )

    async def test_event_payload_recorded(
        self, db, fresh_case, event_service,
    ):
        """Custom payload dict is persisted in event."""
        payload = {"score": 85, "reasons": ["good match"]}
        event = await event_service.record_transition(
            db,
            case=fresh_case,
            to_stage="scored",
            triggered_by="batch",
            feature_origin="F-001",
            payload=payload,
        )
        assert event.payload == payload

    async def test_multi_step_transition(
        self, db, fresh_case, event_service,
    ):
        """Chain of transitions: discovered → scored → under_review."""
        await event_service.record_transition(
            db, case=fresh_case, to_stage="scored",
            triggered_by="batch", feature_origin="F-001",
        )
        assert fresh_case.current_lifecycle_stage == "scored"

        event2 = await event_service.record_transition(
            db, case=fresh_case, to_stage="under_review",
            triggered_by="user", feature_origin="F-001",
        )
        assert fresh_case.current_lifecycle_stage == "under_review"
        assert event2.from_status == "scored"
        assert event2.to_status == "under_review"


@pytest.mark.anyio
class TestEventServiceNonTransition:
    """Test non-transition events (T30 etc.)."""

    async def test_non_transition_event(
        self, db, fresh_case, event_service,
    ):
        """Non-transition event doesn't change stage."""
        # First move to judging_completed
        await event_service.record_transition(
            db, case=fresh_case, to_stage="scored",
            triggered_by="batch", feature_origin="F-001",
        )
        await event_service.record_transition(
            db, case=fresh_case, to_stage="under_review",
            triggered_by="user", feature_origin="F-001",
        )
        await event_service.record_transition(
            db, case=fresh_case, to_stage="planned",
            triggered_by="user", feature_origin="F-001",
        )

        original_stage = fresh_case.current_lifecycle_stage

        event = await event_service.record_non_transition_event(
            db,
            case=fresh_case,
            event_type="checklist_item_checked",
            triggered_by="user",
            feature_origin="F-004",
            payload={"item_id": "item-1"},
        )

        assert event.event_type == "checklist_item_checked"
        assert event.from_status == original_stage
        assert event.to_status == original_stage  # No change
        assert fresh_case.current_lifecycle_stage == original_stage


@pytest.mark.anyio
class TestEventServiceArchive:
    """Test archive transitions (T40)."""

    async def test_archive_sets_archived_at(
        self, db, fresh_case, event_service,
    ):
        """Archive sets case.archived_at timestamp."""
        assert fresh_case.archived_at is None

        event = await event_service.record_archive(
            db, case=fresh_case, triggered_by="system",
        )

        assert fresh_case.current_lifecycle_stage == "archived"
        assert fresh_case.archived_at is not None
        assert event.event_type == "case_archived"
        assert event.to_status == "archived"
