"""Action request schemas — TASK-22.

Pydantic models for case action API endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ActionRequest(BaseModel):
    """Base action request (no extra fields needed)."""

    pass


class SkipRequest(BaseModel):
    """Request to skip a case — reason is required (422 if missing)."""

    reason: str = Field(..., min_length=1, description="Skip reason")


class OverrideRequest(BaseModel):
    """Request to override case metadata — reason is required."""

    reason: str = Field(..., min_length=1, description="Override reason")
    verdict: str | None = Field(
        default=None, description="Override verdict",
    )
