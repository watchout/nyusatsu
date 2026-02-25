"""Lifecycle state machine — SSOT-2 §3 transition validation.

Encodes all valid transitions from SSOT-2 §3-1 through §3-4.
Any transition not in VALID_TRANSITIONS is rejected with InvalidTransitionError.
"""

from __future__ import annotations

from app.core.errors import InvalidTransitionError, PipelineInProgressError
from app.models.case import LifecycleStage

# ---------------------------------------------------------------------------
# All valid transitions: (from_stage, to_stage) -> event_type
# Source: SSOT-2 §3-1 (T01-T16), §3-2 (T20-T26), §3-4 (T40)
# T30 is a non-transition event (handled separately in EventService)
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[tuple[str, str], str] = {
    # §3-1: Forward transitions (happy path + branching)
    ("discovered", "scored"): "case_scored",                          # T01
    ("scored", "under_review"): "case_marked_reviewed",               # T02
    ("under_review", "planned"): "case_marked_planned",               # T03
    ("under_review", "skipped"): "case_marked_skipped",               # T04
    ("planned", "reading_queued"): "reading_queued",                  # T05
    ("reading_queued", "reading_in_progress"): "reading_started",     # T06
    ("reading_in_progress", "reading_completed"): "reading_completed",  # T07
    ("reading_in_progress", "reading_failed"): "reading_failed",      # T08
    ("reading_completed", "judging_queued"): "judging_queued",        # T09
    ("judging_queued", "judging_in_progress"): "judging_started",     # T10
    ("judging_in_progress", "judging_completed"): "judging_completed",  # T11
    ("judging_in_progress", "judging_failed"): "judging_failed",      # T12
    ("judging_completed", "checklist_generating"): "checklist_generating",  # T13
    ("checklist_generating", "checklist_active"): "checklist_generated",    # T14
    ("checklist_generating", "judging_completed"): "checklist_generation_failed",  # T15
    ("checklist_active", "checklist_completed"): "checklist_completed",  # T16
    # §3-2: User operations (gate + override)
    ("reading_failed", "reading_queued"): "reading_requeued",         # T20
    ("judging_failed", "judging_queued"): "judging_requeued",         # T21
    ("reading_completed", "reading_queued"): "reading_requeued",      # T22
    ("judging_completed", "judging_queued"): "judging_requeued",      # T23
    ("checklist_active", "checklist_generating"): "checklist_requeued",  # T24
    ("skipped", "under_review"): "case_marked_reviewed",              # T25
    ("checklist_completed", "checklist_active"): "checklist_item_unchecked",  # T26
}

# T40: Archive from any non-archived stage
ARCHIVE_EVENT_TYPE = "case_archived"

# Pipeline-in-progress stages (SSOT-2 §2-4)
# Operations that change the lifecycle are blocked while in these stages
PIPELINE_STAGES: frozenset[str] = frozenset({
    "reading_queued",
    "reading_in_progress",
    "judging_queued",
    "judging_in_progress",
    "checklist_generating",
})

# Non-transition event types (SSOT-2 §3-3)
NON_TRANSITION_EVENTS: frozenset[str] = frozenset({
    "eligibility_overridden",   # T30
    "checklist_item_checked",
    "checklist_item_unchecked",
    "reading_reviewed",
})


class LifecycleManager:
    """Validates and resolves lifecycle transitions."""

    @staticmethod
    def validate_transition(from_stage: str, to_stage: str) -> str:
        """Validate a state transition and return the event_type.

        Args:
            from_stage: Current lifecycle stage.
            to_stage: Target lifecycle stage.

        Returns:
            The event_type string for this transition.

        Raises:
            InvalidTransitionError: If the transition is not defined in SSOT-2 §3.
        """
        # Special case: archive (T40) — any non-archived stage to archived
        if to_stage == LifecycleStage.archived.value:
            if from_stage == LifecycleStage.archived.value:
                raise InvalidTransitionError(
                    message=f"Cannot archive: already archived",
                    details={"from_stage": from_stage, "to_stage": to_stage},
                )
            return ARCHIVE_EVENT_TYPE

        # Lookup in transition table
        key = (from_stage, to_stage)
        event_type = VALID_TRANSITIONS.get(key)
        if event_type is None:
            raise InvalidTransitionError(
                message=f"Invalid transition: {from_stage} → {to_stage}",
                details={"from_stage": from_stage, "to_stage": to_stage},
            )
        return event_type

    @staticmethod
    def is_pipeline_active(stage: str) -> bool:
        """Check if the stage indicates active pipeline processing."""
        return stage in PIPELINE_STAGES

    @staticmethod
    def get_allowed_transitions(from_stage: str) -> list[str]:
        """Return list of valid target stages from the current stage.

        Includes archive as an option for all non-archived stages.
        """
        targets = [
            to_stage
            for (f, to_stage) in VALID_TRANSITIONS
            if f == from_stage
        ]
        # Add archive option for all non-archived stages
        if from_stage != LifecycleStage.archived.value:
            targets.append(LifecycleStage.archived.value)
        return targets
