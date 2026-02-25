"""Run detail page scraping batch (F-005) — standalone script.

Usage:
    python -m app.scripts.run_detail_scrape
"""

from __future__ import annotations

import asyncio
import sys

import structlog

from app.core.database import async_session
from app.services.batch.detail_scrape_batch import DetailScrapeBatch
from app.services.batch.runner import BatchRunner

logger = structlog.get_logger()


async def main() -> int:
    logger.info("script_started", script="run_detail_scrape")
    async with async_session() as db:
        batch = DetailScrapeBatch()
        runner = BatchRunner()
        try:
            batch_log, result = await runner.run(db, batch)
            await db.commit()
            logger.info(
                "script_completed",
                script="run_detail_scrape",
                status=result.status.value,
                total=result.total_fetched,
            )
            return 0
        except Exception as exc:
            logger.error("script_failed", script="run_detail_scrape", error=str(exc))
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
