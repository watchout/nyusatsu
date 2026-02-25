"""EventService — atomic event recording + stage update.

SSOT-5 §6-1: All state transitions go through case_events.
SSOT-2 §1-2: case_events INSERT + cases.current_lifecycle_stage UPDATE
in the same transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import StageMismatchError
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.services.lifecycle import LifecycleManager

logger = structlog.get_logger()


class EventService:
    """Manages case lifecycle events with atomic consistency."""

    def __init__(self, lifecycle: LifecycleManager | None = None) -> None:
        self._lifecycle = lifecycle or LifecycleManager()

    async def record_transition(
        self,
        db: AsyncSession,
        *,
        case: Case,
        to_stage: str,
        triggered_by: str,
        feature_origin: str,
        actor_id: str = "system",
        payload: dict[str, Any] | None = None,
        expected_lifecycle_stage: str | None = None,
    ) -> CaseEvent:
        """Atomic: validate transition + insert event + update case stage.

        1. If expected_lifecycle_stage provided, compare with current
           → StageMismatchError on mismatch
        2. Validate transition via LifecycleManager
           → InvalidTransitionError if not allowed
        3. INSERT case_event
        4. UPDATE case.current_lifecycle_stage

        All in the caller's transaction (no commit).
        Returns the created CaseEvent.
        """
        from_stage = case.current_lifecycle_stage

        # Step 1: Optimistic lock check
        if expected_lifecycle_stage is not None:
            if from_stage != expected_lifecycle_stage:
                raise StageMismatchError(
                    message=(
                        f"Stage mismatch: expected {expected_lifecycle_stage}, "
                        f"got {from_stage}"
                    ),
                    details={
                        "expected": expected_lifecycle_stage,
                        "actual": from_stage,
                    },
                )

        # Step 2: Validate transition (raises InvalidTransitionError if invalid)
        event_type = self._lifecycle.validate_transition(from_stage, to_stage)

        # Step 3: Insert event
        event = CaseEvent(
            case_id=case.id,
            event_type=event_type,
            from_status=from_stage,
            to_status=to_stage,
            triggered_by=triggered_by,
            actor_id=actor_id,
            feature_origin=feature_origin,
            payload=payload,
        )
        db.add(event)

        # Step 4: Update case stage
        case.current_lifecycle_stage = to_stage
        case.last_updated_at = datetime.now(timezone.utc)

        # Set archived_at for archive transitions
        if to_stage == "archived":
            case.archived_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(event)

        logger.info(
            "lifecycle_transition",
            case_id=str(case.id),
            from_stage=from_stage,
            to_stage=to_stage,
            event_type=event_type,
            triggered_by=triggered_by,
            feature_origin=feature_origin,
        )

        return event

    async def record_non_transition_event(
        self,
        db: AsyncSession,
        *,
        case: Case,
        event_type: str,
        triggered_by: str,
        feature_origin: str,
        actor_id: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> CaseEvent:
        """Record an event that doesn't change lifecycle stage.

        Used for: T30 (eligibility_overridden), checklist_item_checked/unchecked,
        reading_reviewed.
        """
        current_stage = case.current_lifecycle_stage

        event = CaseEvent(
            case_id=case.id,
            event_type=event_type,
            from_status=current_stage,
            to_status=current_stage,  # No change
            triggered_by=triggered_by,
            actor_id=actor_id,
            feature_origin=feature_origin,
            payload=payload,
        )
        db.add(event)
        await db.flush()
        await db.refresh(event)

        logger.info(
            "non_transition_event",
            case_id=str(case.id),
            stage=current_stage,
            event_type=event_type,
            triggered_by=triggered_by,
        )

        return event

    async def record_archive(
        self,
        db: AsyncSession,
        *,
        case: Case,
        triggered_by: str,
        actor_id: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> CaseEvent:
        """Archive a case from any non-archived stage (T40)."""
        return await self.record_transition(
            db,
            case=case,
            to_stage="archived",
            triggered_by=triggered_by,
            feature_origin="F-001",
            actor_id=actor_id,
            payload=payload,
        )
