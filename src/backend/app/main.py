"""FastAPI application factory."""

import structlog
from fastapi import FastAPI

from app.api.actions import router as actions_router
from app.api.batch_trigger import router as batch_trigger_router
from app.api.case_cards import router as case_cards_router
from app.api.checklists import router as checklists_router
from app.api.eligibility import router as eligibility_router
from app.api.health import health_check
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.schemas.envelope import SuccessResponse


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    _configure_logging()

    app = FastAPI(
        title="入札ラクダAI API",
        version="0.1.0",
        docs_url="/docs" if settings.APP_ENV == "development" else None,
        redoc_url=None,
    )

    # --- Exception handlers (SSOT-3 §2-3 envelope format) ---
    register_exception_handlers(app)

    # --- Routes ---
    @app.get("/api/v1/health", response_model=SuccessResponse)
    async def _health():
        result = await health_check()
        return SuccessResponse(data=result)

    # --- API Routers ---
    app.include_router(actions_router)
    app.include_router(case_cards_router)
    app.include_router(eligibility_router)
    app.include_router(checklists_router)
    app.include_router(batch_trigger_router)

    return app


def _configure_logging() -> None:
    """Set up structlog with JSON output per SSOT-5 §11."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


app = create_app()
