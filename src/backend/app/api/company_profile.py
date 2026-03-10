"""Company Profile API endpoints — SSOT-3 §4-8.

GET  /api/v1/company-profile  — get the single company profile
PATCH /api/v1/company-profile — partial update
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.company_profile import CompanyProfile
from app.schemas.company_profile import CompanyProfileResponse, CompanyProfileUpdate
from app.schemas.envelope import SuccessResponse

router = APIRouter(prefix="/api/v1/company-profile", tags=["company-profile"])


async def _get_profile(db: AsyncSession) -> CompanyProfile:
    """Get the single company profile (Phase1: 1 record)."""
    stmt = select(CompanyProfile).limit(1)
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if profile is None:
        raise NotFoundError(message="Company profile not found")
    return profile


@router.get("", response_model=SuccessResponse)
async def get_company_profile(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SuccessResponse:
    """取得 (§4-8)."""
    profile = await _get_profile(db)
    data = CompanyProfileResponse.model_validate(profile).model_dump(mode="json")
    return SuccessResponse(data=data)


@router.patch("", response_model=SuccessResponse)
async def update_company_profile(
    body: CompanyProfileUpdate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SuccessResponse:
    """部分更新 (§4-8). Only specified fields are updated."""
    profile = await _get_profile(db)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()

    data = CompanyProfileResponse.model_validate(profile).model_dump(mode="json")
    return SuccessResponse(data=data)
