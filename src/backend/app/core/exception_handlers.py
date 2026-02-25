"""FastAPI exception handlers — SSOT-3 §2-3 envelope format.

Converts AppError (and unexpected exceptions) into the standard
{ data: null, error: { code, message, details }, meta: { ... } } response.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.schemas.envelope import ErrorDetail, ErrorResponse, Meta

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request, exc: AppError,
    ) -> JSONResponse:
        """Handle domain errors with structured envelope response."""
        logger.warning(
            "app_error",
            error_code=exc.code,
            message=exc.message,
            details=exc.details,
            path=str(request.url),
        )
        body = ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=body.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError,
    ) -> JSONResponse:
        """Wrap Pydantic validation errors in VALIDATION_ERROR envelope."""
        errors = exc.errors()
        logger.warning(
            "validation_error",
            errors=errors,
            path=str(request.url),
        )
        body = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": errors},
            ),
        )
        return JSONResponse(
            status_code=422,
            content=body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception,
    ) -> JSONResponse:
        """Catch-all for unexpected errors — return INTERNAL_ERROR."""
        logger.exception(
            "unhandled_error",
            error_type=type(exc).__name__,
            message=str(exc),
            path=str(request.url),
        )
        body = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            ),
        )
        return JSONResponse(
            status_code=500,
            content=body.model_dump(),
        )
