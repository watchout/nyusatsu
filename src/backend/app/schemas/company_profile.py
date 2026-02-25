"""CompanyProfile response / request schemas — SSOT-3 §4-8.

Pydantic models for company profile endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CompanyProfileResponse(BaseModel):
    """CompanyProfile — company information (§4-8)."""

    id: UUID
    unified_qualification: bool
    grade: str
    business_categories: list[str]
    regions: list[str]
    licenses: list[Any]
    certifications: list[Any]
    experience: list[Any]
    subcontractors: list[dict[str, Any]]
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyProfileUpdate(BaseModel):
    """PATCH /company-profile request body — partial update (§4-8).

    All fields are optional. Only specified fields are updated.
    """

    unified_qualification: bool | None = None
    grade: str | None = None
    business_categories: list[str] | None = None
    regions: list[str] | None = None
    licenses: list[Any] | None = None
    certifications: list[Any] | None = None
    experience: list[Any] | None = None
    subcontractors: list[dict[str, Any]] | None = None
