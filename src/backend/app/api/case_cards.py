"""Case Card API endpoints — F-002.

Provides read access to AI-extracted case card data,
and mark-reviewed action (SSOT-3 §4-3).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.case import Case
from app.models.case_card import CaseCard
from app.schemas.envelope import SuccessResponse
from app.services.event_service import EventService
from app.services.version_manager import VersionManager

router = APIRouter(tags=["case-cards"])
_vm = VersionManager(CaseCard)
_event_service = EventService()


@router.get("/api/v1/cases/{case_id}/card", response_model=SuccessResponse)
async def get_current_card(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the current CaseCard for a case."""
    card = await _vm.get_current(db, case_id=case_id)
    if not card:
        raise NotFoundError(
            message="CaseCard not found",
            details={"case_id": str(case_id)},
        )
    return SuccessResponse(data=_card_to_dict(card))


@router.get("/api/v1/cases/{case_id}/cards", response_model=SuccessResponse)
async def get_all_cards(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all CaseCard versions for a case."""
    cards = await _vm.get_all_versions(db, case_id=case_id)
    return SuccessResponse(data=[_card_to_dict(c) for c in cards])


@router.post(
    "/api/v1/case-cards/{card_id}/actions/mark-reviewed",
    response_model=SuccessResponse,
)
async def mark_card_reviewed(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a CaseCard as human-reviewed (SSOT-3 §4-3).

    Sets reviewed_at = NOW(), reviewed_by = 'kaneko' (Phase1 single user).
    Records 'reading_reviewed' event. No stage transition.
    """
    card = (
        await db.execute(select(CaseCard).where(CaseCard.id == card_id))
    ).scalar_one_or_none()

    if card is None:
        raise NotFoundError(
            message="CaseCard not found",
            details={"card_id": str(card_id)},
        )

    card.reviewed_at = datetime.now(timezone.utc)
    card.reviewed_by = "kaneko"

    # Record non-transition event
    case = (
        await db.execute(select(Case).where(Case.id == card.case_id))
    ).scalar_one_or_none()

    if case:
        await _event_service.record_non_transition_event(
            db,
            case=case,
            event_type="reading_reviewed",
            triggered_by="user",
            feature_origin="F-002",
            payload={"card_id": str(card_id), "version": card.version},
        )

    await db.commit()

    return SuccessResponse(data=_card_to_dict(card))


def _card_to_dict(card: CaseCard) -> dict:
    return {
        "id": str(card.id),
        "case_id": str(card.case_id),
        "version": card.version,
        "is_current": card.is_current,
        "eligibility": card.eligibility,
        "schedule": card.schedule,
        "business_content": card.business_content,
        "submission_items": card.submission_items,
        "risk_factors": card.risk_factors,
        "confidence_score": float(card.confidence_score) if card.confidence_score else None,
        "evidence": card.evidence,
        "reviewed_at": card.reviewed_at.isoformat() if card.reviewed_at else None,
        "reviewed_by": card.reviewed_by,
    }
