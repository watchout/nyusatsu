"""Checklist response / request schemas — SSOT-3 §4-5.

Pydantic models for checklist endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChecklistResponse(BaseModel):
    """Checklist — preparation checklist (§4-5)."""

    id: UUID
    case_id: UUID
    case_card_id: UUID
    eligibility_result_id: UUID
    version: int
    is_current: bool
    checklist_items: list[dict[str, Any]]
    schedule_items: list[dict[str, Any]]
    warnings: list[str]
    progress: dict[str, Any]
    status: str
    generated_at: datetime
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChecklistItemUpdate(BaseModel):
    """PATCH /checklists/:id/items/:item_id request body (§4-5)."""

    status: str = Field(
        ..., pattern="^(pending|done)$",
        description="'pending' or 'done'",
    )
    expected_checklist_version: int | None = Field(
        default=None,
        description="Optimistic lock: compare with checklists.version",
    )


class ChecklistItemAdd(BaseModel):
    """POST /checklists/:id/items request body (§4-5)."""

    name: str = Field(..., min_length=1, description="Item name")
    phase: str = Field(
        default="bid_time",
        description="'bid_time' or 'performance_time'",
    )
    deadline: str | None = Field(
        default=None, description="Deadline date string (YYYY-MM-DD)",
    )
    notes: str | None = Field(
        default=None, description="Additional notes",
    )
