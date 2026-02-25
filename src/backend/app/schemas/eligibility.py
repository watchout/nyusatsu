"""EligibilityResult response schemas — SSOT-3 §4-4.

Pydantic models for GET /cases/:id/eligibility and /eligibilities.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EligibilityResponse(BaseModel):
    """EligibilityResult — judgment result (§4-4)."""

    id: UUID
    case_id: UUID
    case_card_id: UUID
    version: int
    is_current: bool
    verdict: str
    confidence: Decimal
    hard_fail_reasons: list[dict[str, Any]]
    soft_gaps: list[dict[str, Any]]
    check_details: dict[str, Any]
    company_profile_snapshot: dict[str, Any]
    human_override: str | None = None
    override_reason: str | None = None
    overridden_at: datetime | None = None
    judged_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
