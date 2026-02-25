"""Batch response / request schemas — SSOT-3 §4-7.

Pydantic models for batch management endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BatchLogResponse(BaseModel):
    """BatchLog — batch execution record (§4-7)."""

    id: UUID
    source: str
    feature_origin: str
    batch_type: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    total_fetched: int
    new_count: int
    updated_count: int
    unchanged_count: int
    error_count: int
    error_details: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class BatchTriggerRequest(BaseModel):
    """POST /batch/trigger request body (§4-7)."""

    source: str = Field(..., description="'chotatku_portal' or 'od_csv'")
    batch_type: str = Field(
        ..., description="'case_fetch', 'od_import', or 'detail_scrape'",
    )


class BatchTriggerResponse(BaseModel):
    """POST /batch/trigger response (§4-7)."""

    batch_log_id: UUID
    status: str = "running"
