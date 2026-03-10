"""Eligibility API endpoints — F-003.

Provides read access to eligibility judgment results.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.eligibility_result import EligibilityResult
from app.schemas.envelope import SuccessResponse
from app.services.version_manager import VersionManager

router = APIRouter(prefix="/api/v1/cases", tags=["eligibility"])
_vm = VersionManager(EligibilityResult)


@router.get("/{case_id}/eligibility", response_model=SuccessResponse)
async def get_current_eligibility(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Get the current EligibilityResult for a case."""
    elig = await _vm.get_current(db, case_id=case_id)
    if not elig:
        raise NotFoundError(
            message="EligibilityResult not found",
            details={"case_id": str(case_id)},
        )
    return SuccessResponse(data=_elig_to_dict(elig))


@router.get("/{case_id}/eligibilities", response_model=SuccessResponse)
async def get_all_eligibilities(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Get all EligibilityResult versions for a case."""
    results = await _vm.get_all_versions(db, case_id=case_id)
    return SuccessResponse(data=[_elig_to_dict(e) for e in results])


def _elig_to_dict(elig: EligibilityResult) -> dict:
    return {
        "id": str(elig.id),
        "case_id": str(elig.case_id),
        "case_card_id": str(elig.case_card_id),
        "version": elig.version,
        "is_current": elig.is_current,
        "verdict": elig.verdict,
        "confidence": float(elig.confidence),
        "hard_fail_reasons": elig.hard_fail_reasons,
        "soft_gaps": elig.soft_gaps,
        "check_details": elig.check_details,
        "human_override": elig.human_override,
    }
