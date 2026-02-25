"""Case Card API endpoints — F-002.

Provides read access to AI-extracted case card data.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.case_card import CaseCard
from app.schemas.envelope import SuccessResponse
from app.services.version_manager import VersionManager

router = APIRouter(prefix="/api/v1/cases", tags=["case-cards"])
_vm = VersionManager(CaseCard)


@router.get("/{case_id}/card", response_model=SuccessResponse)
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


@router.get("/{case_id}/cards", response_model=SuccessResponse)
async def get_all_cards(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all CaseCard versions for a case."""
    cards = await _vm.get_all_versions(db, case_id=case_id)
    return SuccessResponse(data=[_card_to_dict(c) for c in cards])


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
    }
