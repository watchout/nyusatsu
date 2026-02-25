"""Application error hierarchy — SSOT-3 §7.

All domain errors inherit from AppError. Each subclass encodes a specific
error code and HTTP status, matching the 14 error codes in SSOT-3 §7.

Usage:
    raise NotFoundError(message="Case not found", details={"id": str(case_id)})
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error.

    Attributes:
        code: Machine-readable error code (e.g. "NOT_FOUND").
        http_status: HTTP status code to return.
        message: Human-readable error message.
        details: Optional dict with structured error context.
    """

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.__doc__ or self.code
        self.details = details
        super().__init__(self.message)


# --- 409 Conflict ---


class InvalidTransitionError(AppError):
    """Attempted an invalid lifecycle stage transition."""

    code = "INVALID_TRANSITION"
    http_status = 409


class StageMismatchError(AppError):
    """Optimistic lock: expected_lifecycle_stage does not match current."""

    code = "STAGE_MISMATCH"
    http_status = 409


class PipelineInProgressError(AppError):
    """Cannot perform action while pipeline is in progress."""

    code = "PIPELINE_IN_PROGRESS"
    http_status = 409


class BatchAlreadyRunningError(AppError):
    """A batch of the same type is already running."""

    code = "BATCH_ALREADY_RUNNING"
    http_status = 409


class ChecklistVersionMismatchError(AppError):
    """Optimistic lock: expected_checklist_version does not match current."""

    code = "CHECKLIST_VERSION_MISMATCH"
    http_status = 409


# --- 404 Not Found ---


class NotFoundError(AppError):
    """Resource not found."""

    code = "NOT_FOUND"
    http_status = 404


class CaseCardNotFoundError(AppError):
    """No current case_card found (case has not been analyzed yet)."""

    code = "CASE_CARD_NOT_FOUND"
    http_status = 404


class EligibilityNotFoundError(AppError):
    """No current eligibility_result found (case has not been judged yet)."""

    code = "ELIGIBILITY_NOT_FOUND"
    http_status = 404


class ChecklistNotFoundError(AppError):
    """No current checklist found (checklist has not been generated yet)."""

    code = "CHECKLIST_NOT_FOUND"
    http_status = 404


class ChecklistItemNotFoundError(AppError):
    """Specified checklist item_id not found."""

    code = "CHECKLIST_ITEM_NOT_FOUND"
    http_status = 404


# --- 422 Unprocessable Entity ---


class ValidationError(AppError):
    """Request validation failed (missing/invalid parameters)."""

    code = "VALIDATION_ERROR"
    http_status = 422


class OverrideReasonRequiredError(AppError):
    """Override action requires a reason."""

    code = "OVERRIDE_REASON_REQUIRED"
    http_status = 422


class SkipReasonRequiredError(AppError):
    """Skip action requires a reason."""

    code = "SKIP_REASON_REQUIRED"
    http_status = 422


# --- 500 Internal Server Error ---


class InternalError(AppError):
    """Unexpected server error."""

    code = "INTERNAL_ERROR"
    http_status = 500
