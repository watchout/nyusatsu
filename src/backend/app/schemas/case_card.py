"""CaseCard response schemas — SSOT-3 §4-3.

Pydantic models for GET /cases/:id/card and /cards.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CaseCardResponse(BaseModel):
    """CaseCard — AI reading result (§4-3)."""

    id: UUID
    case_id: UUID
    version: int
    is_current: bool
    eligibility: dict[str, Any] | None = None
    schedule: dict[str, Any] | None = None
    business_content: dict[str, Any] | None = None
    submission_items: list[dict[str, Any]] | None = None
    risk_factors: list[dict[str, Any]] | None = None
    deadline_at: datetime | None = None
    business_type: str | None = None
    risk_level: str | None = None
    extraction_method: str
    is_scanned: bool
    assertion_counts: dict[str, int] | None = None
    evidence: dict[str, Any] | None = None
    confidence_score: Decimal | None = None
    file_hash: str | None = None
    status: str
    llm_model: str | None = None
    token_usage: dict[str, int] | None = None
    extracted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
