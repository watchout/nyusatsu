"""Case response schemas — SSOT-3 §4-1.

Pydantic models for GET /cases and GET /cases/:id.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CaseResponse(BaseModel):
    """Case list item — GET /api/v1/cases response element (§4-1)."""

    id: UUID
    source: str
    source_id: str
    case_name: str
    issuing_org: str
    bid_type: str | None = None
    category: str | None = None
    region: str | None = None
    grade: str | None = None
    submission_deadline: datetime | None = None
    opening_date: datetime | None = None
    status: str
    current_lifecycle_stage: str
    score: int | None = None
    score_detail: dict[str, Any] | None = None
    first_seen_at: datetime
    last_updated_at: datetime

    model_config = {"from_attributes": True}


class CaseDetailResponse(BaseModel):
    """Case detail — GET /api/v1/cases/:id response (§4-1).

    Extends CaseResponse with optional URL fields and embedded resources.
    """

    id: UUID
    source: str
    source_id: str
    case_name: str
    issuing_org: str
    issuing_org_code: str | None = None
    bid_type: str | None = None
    category: str | None = None
    region: str | None = None
    grade: str | None = None
    submission_deadline: datetime | None = None
    opening_date: datetime | None = None
    spec_url: str | None = None
    notice_url: str | None = None
    detail_url: str | None = None
    status: str
    current_lifecycle_stage: str
    score: int | None = None
    score_detail: dict[str, Any] | None = None
    first_seen_at: datetime
    last_updated_at: datetime

    # Embedded resources (populated via ?include= parameter)
    card: Any | None = None
    eligibility: Any | None = None
    checklist: Any | None = None
    latest_events: list[Any] | None = None

    model_config = {"from_attributes": True}
