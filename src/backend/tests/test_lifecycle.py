"""Tests for TASK-10: LifecycleManager — SSOT-2 §3 transition validation."""

from __future__ import annotations

import pytest

from app.core.errors import InvalidTransitionError
from app.models.case import LifecycleStage
from app.services.lifecycle import (
    ARCHIVE_EVENT_TYPE,
    PIPELINE_STAGES,
    VALID_TRANSITIONS,
    LifecycleManager,
)


class TestLifecycleManager:
    """Validate transition table against SSOT-2 §3."""

    def test_transition_count(self):
        """SSOT-2 §3-1 (16) + §3-2 (7) = 23 non-archive transitions."""
        assert len(VALID_TRANSITIONS) == 23

    @pytest.mark.parametrize(
        "from_stage, to_stage, expected_event",
        [
            # §3-1: Forward transitions
            ("discovered", "scored", "case_scored"),
            ("scored", "under_review", "case_marked_reviewed"),
            ("under_review", "planned", "case_marked_planned"),
            ("under_review", "skipped", "case_marked_skipped"),
            ("planned", "reading_queued", "reading_queued"),
            ("reading_queued", "reading_in_progress", "reading_started"),
            ("reading_in_progress", "reading_completed", "reading_completed"),
            ("reading_in_progress", "reading_failed", "reading_failed"),
            ("reading_completed", "judging_queued", "judging_queued"),
            ("judging_queued", "judging_in_progress", "judging_started"),
            ("judging_in_progress", "judging_completed", "judging_completed"),
            ("judging_in_progress", "judging_failed", "judging_failed"),
            ("judging_completed", "checklist_generating", "checklist_generating"),
            ("checklist_generating", "checklist_active", "checklist_generated"),
            ("checklist_generating", "judging_completed", "checklist_generation_failed"),
            ("checklist_active", "checklist_completed", "checklist_completed"),
            # §3-2: User operations
            ("reading_failed", "reading_queued", "reading_requeued"),
            ("judging_failed", "judging_queued", "judging_requeued"),
            ("reading_completed", "reading_queued", "reading_requeued"),
            ("judging_completed", "judging_queued", "judging_requeued"),
            ("checklist_active", "checklist_generating", "checklist_requeued"),
            ("skipped", "under_review", "case_marked_reviewed"),
            ("checklist_completed", "checklist_active", "checklist_item_unchecked"),
        ],
    )
    def test_valid_transitions(self, from_stage, to_stage, expected_event):
        """Every defined transition returns the correct event_type."""
        event = LifecycleManager.validate_transition(from_stage, to_stage)
        assert event == expected_event

    def test_invalid_transition_raises(self):
        """Undefined transitions raise InvalidTransitionError."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            LifecycleManager.validate_transition("discovered", "planned")
        assert "Invalid transition" in exc_info.value.message
        assert exc_info.value.details["from_stage"] == "discovered"
        assert exc_info.value.details["to_stage"] == "planned"

    @pytest.mark.parametrize(
        "from_stage",
        [s.value for s in LifecycleStage if s != LifecycleStage.archived],
    )
    def test_archive_from_any_non_archived_stage(self, from_stage):
        """T40: Any non-archived stage can transition to archived."""
        event = LifecycleManager.validate_transition(from_stage, "archived")
        assert event == ARCHIVE_EVENT_TYPE

    def test_archive_from_archived_raises(self):
        """archived → archived is not allowed."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            LifecycleManager.validate_transition("archived", "archived")
        assert "already archived" in exc_info.value.message

    def test_pipeline_stages_identified(self):
        """All 5 pipeline stages are in PIPELINE_STAGES."""
        expected = {
            "reading_queued", "reading_in_progress",
            "judging_queued", "judging_in_progress",
            "checklist_generating",
        }
        assert expected == PIPELINE_STAGES
        for stage in expected:
            assert LifecycleManager.is_pipeline_active(stage) is True
        # Non-pipeline stages
        assert LifecycleManager.is_pipeline_active("discovered") is False
        assert LifecycleManager.is_pipeline_active("checklist_active") is False

    def test_get_allowed_transitions(self):
        """under_review can go to planned, skipped, or archived."""
        targets = LifecycleManager.get_allowed_transitions("under_review")
        assert "planned" in targets
        assert "skipped" in targets
        assert "archived" in targets
        assert "discovered" not in targets
