"""Run case fetch batch (F-001) — standalone script.

Fetches new/updated cases from the Chotatsu Portal.

Usage:
    python -m app.scripts.run_case_fetch
"""

from __future__ import annotations

import asyncio
import sys

import structlog

from app.core.database import async_session
from app.services.batch.case_fetch_batch import CaseFetchBatch
from app.services.batch.runner import BatchRunner
from app.services.case_fetch.chotatku_adapter import ChotatkuPortalAdapter

logger = structlog.get_logger()


async def main() -> int:
    logger.info("script_started", script="run_case_fetch")
    async with async_session() as db:
        adapter = ChotatkuPortalAdapter()
        batch = CaseFetchBatch(adapter=adapter)
        runner = BatchRunner()
        try:
            batch_log, result = await runner.run(db, batch)
            await db.commit()
            logger.info(
                "script_completed",
                script="run_case_fetch",
                status=result.status.value,
                total=result.total_fetched,
            )
            return 0
        except Exception as exc:
            logger.error("script_failed", script="run_case_fetch", error=str(exc))
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
