"""Case action API endpoints — TASK-22.

9 POST endpoints for case lifecycle actions:
1. mark-reviewed    — scored → under_review  (or skipped → under_review)
2. mark-planned     — under_review → planned  (+ cascade → reading_queued)
3. mark-skipped     — under_review → skipped  (reason required)
4. restore          — skipped → under_review
5. archive          — any → archived
6. retry-reading    — * → reading_queued
7. retry-judging    — * → judging_queued
8. retry-checklist  — checklist_active → checklist_generating
9. override         — metadata update only (reason required)

All endpoints use EventService for lifecycle transitions and
return SuccessResponse envelope per SSOT-3 §2-3.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, SkipReasonRequiredError
from app.models.case import Case
from app.schemas.actions import ActionRequest, OverrideRequest, SkipRequest
from app.schemas.envelope import SuccessResponse
from app.services.event_service import EventService

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/cases", tags=["case-actions"])

_event_service = EventService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_case(db: AsyncSession, case_id: str) -> Case:
    """Load a case by UUID or raise NotFoundError."""
    try:
        uid = uuid.UUID(case_id)
    except ValueError:
        raise NotFoundError(
            message=f"Invalid case ID: {case_id}",
            details={"case_id": case_id},
        )

    case = (
        await db.execute(select(Case).where(Case.id == uid))
    ).scalar_one_or_none()

    if case is None:
        raise NotFoundError(
            message=f"Case not found: {case_id}",
            details={"case_id": case_id},
        )

    return case


def _case_summary(case: Case) -> dict:
    """Build response data dict for a case."""
    return {
        "id": str(case.id),
        "case_name": case.case_name,
        "current_lifecycle_stage": case.current_lifecycle_stage,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{case_id}/actions/mark-reviewed")
async def mark_reviewed(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T02: scored → under_review, or T25: skipped → under_review."""
    case = await _get_case(db, case_id)

    await _event_service.record_transition(
        db,
        case=case,
        to_stage="under_review",
        triggered_by="user",
        feature_origin="F-001",
    )
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/mark-planned")
async def mark_planned(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T03: under_review → planned, then cascade T05: planned → reading_queued."""
    case = await _get_case(db, case_id)

    # Step 1: under_review → planned
    await _event_service.record_transition(
        db,
        case=case,
        to_stage="planned",
        triggered_by="user",
        feature_origin="F-001",
    )

    # Step 2: cascade — planned → reading_queued
    await _event_service.record_transition(
        db,
        case=case,
        to_stage="reading_queued",
        triggered_by="system",
        feature_origin="F-001",
    )
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/mark-skipped")
async def mark_skipped(
    case_id: str,
    body: SkipRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T04: under_review → skipped. Reason required (422)."""
    case = await _get_case(db, case_id)

    await _event_service.record_transition(
        db,
        case=case,
        to_stage="skipped",
        triggered_by="user",
        feature_origin="F-001",
        payload={"reason": body.reason},
    )
    case.skip_reason = body.reason
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/restore")
async def restore(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T25: skipped → under_review."""
    case = await _get_case(db, case_id)

    await _event_service.record_transition(
        db,
        case=case,
        to_stage="under_review",
        triggered_by="user",
        feature_origin="F-001",
    )
    case.skip_reason = None
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/archive")
async def archive(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T40: any non-archived → archived."""
    case = await _get_case(db, case_id)

    await _event_service.record_archive(
        db,
        case=case,
        triggered_by="user",
    )
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/retry-reading")
async def retry_reading(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T20/T22: * → reading_queued."""
    case = await _get_case(db, case_id)

    await _event_service.record_transition(
        db,
        case=case,
        to_stage="reading_queued",
        triggered_by="user",
        feature_origin="F-002",
    )
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/retry-judging")
async def retry_judging(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T21/T23: * → judging_queued."""
    case = await _get_case(db, case_id)

    await _event_service.record_transition(
        db,
        case=case,
        to_stage="judging_queued",
        triggered_by="user",
        feature_origin="F-002",
    )
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/retry-checklist")
async def retry_checklist(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T24: checklist_active → checklist_generating."""
    case = await _get_case(db, case_id)

    await _event_service.record_transition(
        db,
        case=case,
        to_stage="checklist_generating",
        triggered_by="user",
        feature_origin="F-003",
    )
    await db.commit()

    return SuccessResponse(data=_case_summary(case))


@router.post("/{case_id}/actions/override")
async def override_action(
    case_id: str,
    body: OverrideRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """T30: metadata update only (non-transition event). Reason required."""
    case = await _get_case(db, case_id)

    await _event_service.record_non_transition_event(
        db,
        case=case,
        event_type="case_overridden",
        triggered_by="user",
        feature_origin="F-001",
        payload={
            "reason": body.reason,
            "verdict": body.verdict,
        },
    )
    await db.commit()

    return SuccessResponse(data=_case_summary(case))
