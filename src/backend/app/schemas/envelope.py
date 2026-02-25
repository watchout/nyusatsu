"""SSOT-3 §2-3 Response envelope models.

Defines the standard response format used by all API endpoints:
- SuccessResponse: { data, meta }
- PaginatedResponse: { data: [...], meta: { ..., page, limit, total, total_pages } }
- ErrorResponse: { data: null, error: { code, message, details }, meta }
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Warning(BaseModel):
    """SSOT-3 §2-7: warning entry for partial success / evidence gaps."""

    code: str
    message: str
    affected_fields: list[str] | None = None


class Meta(BaseModel):
    """Base response metadata."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    warnings: list[Warning] | None = None


class PaginatedMeta(Meta):
    """SSOT-3 §2-3: pagination metadata extending base Meta."""

    page: int
    limit: int
    total: int
    total_pages: int


class ErrorDetail(BaseModel):
    """Error detail block inside ErrorResponse."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class SuccessResponse(BaseModel):
    """Standard success response envelope."""

    data: Any
    meta: Meta = Field(default_factory=Meta)


class PaginatedResponse(BaseModel):
    """Paginated list response envelope."""

    data: list[Any]
    meta: PaginatedMeta


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    data: None = None
    error: ErrorDetail
    meta: Meta = Field(default_factory=Meta)
