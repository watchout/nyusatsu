"""CaseEvent response schemas — SSOT-3 §4-6.

Pydantic models for GET /cases/:id/events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EventResponse(BaseModel):
    """CaseEvent — event spine entry (§4-6)."""

    id: UUID
    case_id: UUID
    event_type: str
    from_status: str | None = None
    to_status: str
    triggered_by: str
    actor_id: str
    feature_origin: str
    payload: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FoldedCheckOperations(BaseModel):
    """Folded check operations summary (§4-6 fold=check_operations)."""

    event_type: str = "_folded_check_operations"
    count: int
    first_at: datetime
    last_at: datetime
    summary: dict[str, int]
