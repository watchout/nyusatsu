"""Health check endpoint with DB connectivity test."""

from sqlalchemy import text

from app.core.database import async_session


async def check_db() -> bool:
    """Execute SELECT 1 to verify database connectivity."""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def health_check() -> dict:
    """GET /api/v1/health — returns status and DB connectivity."""
    db_ok = await check_db()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
    }
