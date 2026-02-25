"""Run cascade pipeline batch (F-002 → F-003 → F-004) — standalone script.

Usage:
    python -m app.scripts.run_cascade
"""

from __future__ import annotations

import asyncio
import sys

import structlog

from app.core.database import async_session
from app.services.batch.cascade_batch import CascadeBatch
from app.services.batch.runner import BatchRunner
from app.services.llm.mock import MockProvider

logger = structlog.get_logger()


async def main() -> int:
    logger.info("script_started", script="run_cascade")
    async with async_session() as db:
        # TODO: Use real LLM provider from config instead of mock
        provider = MockProvider()
        batch = CascadeBatch(provider)
        runner = BatchRunner()
        try:
            batch_log, result = await runner.run(db, batch)
            await db.commit()
            logger.info(
                "script_completed",
                script="run_cascade",
                status=result.status.value,
                total=result.total_fetched,
            )
            return 0
        except Exception as exc:
            logger.error("script_failed", script="run_cascade", error=str(exc))
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
