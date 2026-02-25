"""Run OpenData import batch (F-005) — standalone script.

Downloads the latest OpenData CSV and imports it.

Usage:
    python -m app.scripts.run_od_import
"""

from __future__ import annotations

import asyncio
import hashlib
import sys

import structlog

from app.core.database import async_session
from app.services.batch.od_import_batch import ODImportBatch
from app.services.batch.runner import BatchRunner

logger = structlog.get_logger()

# TODO: Move to config / env
OD_CSV_URL = "https://info.gbiz.go.jp/hojin/ichiran"  # placeholder


async def _fetch_csv() -> tuple[str, str]:
    """Fetch CSV from OpenData source. Returns (csv_text, sha256)."""
    # TODO: Replace with actual HTTP download (httpx)
    # For now, return empty to demonstrate the script structure
    import httpx

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(OD_CSV_URL)
        resp.raise_for_status()
        csv_text = resp.text
        sha256 = hashlib.sha256(csv_text.encode()).hexdigest()
        return csv_text, sha256


async def main() -> int:
    logger.info("script_started", script="run_od_import")
    try:
        csv_text, sha256 = await _fetch_csv()
    except Exception as exc:
        logger.error("csv_download_failed", script="run_od_import", error=str(exc))
        return 1

    async with async_session() as db:
        batch = ODImportBatch(csv_text=csv_text, sha256=sha256)
        runner = BatchRunner()
        try:
            batch_log, result = await runner.run(db, batch)
            await db.commit()
            logger.info(
                "script_completed",
                script="run_od_import",
                status=result.status.value,
                total=result.total_fetched,
            )
            return 0
        except Exception as exc:
            logger.error("script_failed", script="run_od_import", error=str(exc))
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
