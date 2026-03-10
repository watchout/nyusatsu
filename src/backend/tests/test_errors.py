"""Tests for TASK-09: Response envelope + error handlers.

Validates:
- 14 error classes match SSOT-3 §7 codes and HTTP statuses
- Exception handlers produce correct envelope format
- PaginatedResponse and Warning models
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.errors import (
    AppError,
    BatchAlreadyRunningError,
    CaseCardNotFoundError,
    ChecklistItemNotFoundError,
    ChecklistNotFoundError,
    ChecklistVersionMismatchError,
    EligibilityNotFoundError,
    InternalError,
    InvalidTransitionError,
    NotFoundError,
    OverrideReasonRequiredError,
    PipelineInProgressError,
    SkipReasonRequiredError,
    StageMismatchError,
    ValidationError,
)
from app.schemas.envelope import (
    Meta,
    PaginatedMeta,
    PaginatedResponse,
    SuccessResponse,
    Warning,
)

# --- All 14 error classes ---

ALL_ERROR_CLASSES = [
    InvalidTransitionError,
    StageMismatchError,
    PipelineInProgressError,
    BatchAlreadyRunningError,
    ChecklistVersionMismatchError,
    NotFoundError,
    CaseCardNotFoundError,
    EligibilityNotFoundError,
    ChecklistNotFoundError,
    ChecklistItemNotFoundError,
    ValidationError,
    OverrideReasonRequiredError,
    SkipReasonRequiredError,
    InternalError,
]

EXPECTED_CODES = {
    "INVALID_TRANSITION": 409,
    "STAGE_MISMATCH": 409,
    "PIPELINE_IN_PROGRESS": 409,
    "BATCH_ALREADY_RUNNING": 409,
    "CHECKLIST_VERSION_MISMATCH": 409,
    "NOT_FOUND": 404,
    "CASE_CARD_NOT_FOUND": 404,
    "ELIGIBILITY_NOT_FOUND": 404,
    "CHECKLIST_NOT_FOUND": 404,
    "CHECKLIST_ITEM_NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "OVERRIDE_REASON_REQUIRED": 422,
    "SKIP_REASON_REQUIRED": 422,
    "INTERNAL_ERROR": 500,
}


class TestErrorClasses:
    """Test AppError hierarchy attributes."""

    def test_all_14_errors_inherit_from_app_error(self):
        assert len(ALL_ERROR_CLASSES) == 14
        for cls in ALL_ERROR_CLASSES:
            assert issubclass(cls, AppError)

    def test_all_14_error_codes_unique(self):
        codes = [cls.code for cls in ALL_ERROR_CLASSES]
        assert len(codes) == len(set(codes)), f"Duplicate codes: {codes}"

    def test_all_error_codes_match_ssot3(self):
        """Each error class code and HTTP status must match SSOT-3 §7."""
        for cls in ALL_ERROR_CLASSES:
            assert cls.code in EXPECTED_CODES, f"{cls.__name__} code not in SSOT-3"
            assert cls.http_status == EXPECTED_CODES[cls.code], (
                f"{cls.__name__}: expected status {EXPECTED_CODES[cls.code]}, "
                f"got {cls.http_status}"
            )

    def test_error_with_message_and_details(self):
        err = NotFoundError(
            message="Case not found",
            details={"id": "abc-123"},
        )
        assert err.message == "Case not found"
        assert err.details == {"id": "abc-123"}
        assert err.code == "NOT_FOUND"
        assert err.http_status == 404
        assert str(err) == "Case not found"

    def test_error_default_message(self):
        err = NotFoundError()
        assert err.message  # Should have a default message from docstring
        assert err.details is None


class TestEnvelopeModels:
    """Test envelope schema models."""

    def test_success_response_format(self):
        resp = SuccessResponse(data={"status": "ok"})
        dump = resp.model_dump()
        assert dump["data"] == {"status": "ok"}
        assert "timestamp" in dump["meta"]
        assert "request_id" in dump["meta"]

    def test_paginated_response_meta(self):
        resp = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            meta=PaginatedMeta(page=1, limit=20, total=42, total_pages=3),
        )
        dump = resp.model_dump()
        assert dump["meta"]["page"] == 1
        assert dump["meta"]["limit"] == 20
        assert dump["meta"]["total"] == 42
        assert dump["meta"]["total_pages"] == 3
        assert len(dump["data"]) == 2

    def test_warning_in_meta(self):
        meta = Meta(warnings=[Warning(code="EVIDENCE_MISSING", message="No source")])
        dump = meta.model_dump()
        assert len(dump["warnings"]) == 1
        assert dump["warnings"][0]["code"] == "EVIDENCE_MISSING"


@pytest.mark.anyio
class TestExceptionHandlers:
    """Test FastAPI exception handlers return correct envelope."""

    async def test_app_error_returns_envelope(self, client: AsyncClient):
        """AppError produces standard error envelope."""
        # Request a non-existent endpoint — this uses the catch-all
        # But let's test a specific error by adding a temporary route
        from fastapi import FastAPI

        from app.core.errors import NotFoundError
        from app.core.exception_handlers import register_exception_handlers

        test_app = FastAPI()
        register_exception_handlers(test_app)

        @test_app.get("/test-not-found")
        async def _raise_not_found():
            raise NotFoundError(message="Test resource not found")

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/test-not-found")

        assert resp.status_code == 404
        body = resp.json()
        assert body["data"] is None
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["message"] == "Test resource not found"
        assert "timestamp" in body["meta"]
        assert "request_id" in body["meta"]

    async def test_unhandled_error_returns_internal(self, client: AsyncClient):
        """Unexpected exception produces INTERNAL_ERROR envelope."""
        from fastapi import FastAPI

        from app.core.exception_handlers import register_exception_handlers

        test_app = FastAPI(debug=False)
        register_exception_handlers(test_app)

        @test_app.get("/test-crash")
        async def _raise_unexpected():
            raise RuntimeError("Oops")

        transport = ASGITransport(app=test_app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/test-crash")

        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"

    async def test_health_still_works(self, client: AsyncClient):
        """Existing health endpoint is not broken by exception handlers."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "ok"
