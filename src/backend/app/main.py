"""FastAPI application factory."""

from fastapi import FastAPI

from app.api.actions import router as actions_router
from app.api.analytics import router as analytics_router
from app.api.batch import router as batch_router
from app.api.case_cards import router as case_cards_router
from app.api.cases import router as cases_router
from app.api.checklists import router as checklists_router
from app.api.company_profile import router as company_profile_router
from app.api.eligibility import router as eligibility_router
from app.api.events import router as events_router
from app.api.health import health_check
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.schemas.envelope import SuccessResponse


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()

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
    app.include_router(cases_router)
    app.include_router(actions_router)
    app.include_router(case_cards_router)
    app.include_router(eligibility_router)
    app.include_router(checklists_router)
    app.include_router(events_router)
    app.include_router(batch_router)
    app.include_router(company_profile_router)
    app.include_router(analytics_router)

    return app


app = create_app()
