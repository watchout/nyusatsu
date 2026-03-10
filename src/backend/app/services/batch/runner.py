"""Batch runner / orchestrator — SSOT-5 §2.

Manages:
- Exclusive locking (same batch_type must not run concurrently)
- batch_logs INSERT (running) → loop → UPDATE (final status)
- Per-item error handling (partial failure → continue to next)
- Error details recording in JSONB
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
import structlog.contextvars
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BatchAlreadyRunningError
from app.models.batch_log import BatchLog
from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import BatchResult, ItemStatus

logger = structlog.get_logger()


class BatchRunner:
    """Orchestrate a batch run with logging and locking.

    Usage::

        runner = BatchRunner()
        batch_log, result = await runner.run(db, MyBatchRunner())
    """

    async def run(
        self,
        db: AsyncSession,
        batch_runner: BaseBatchRunner,
    ) -> tuple[BatchLog, BatchResult]:
        """Execute a batch job with full lifecycle management.

        Steps:
        1. Check exclusive lock (no running batch of same type+source)
        2. INSERT batch_log (status='running')
        3. Call on_batch_start() hook
        4. Loop: fetch_items → process_item → record results
        5. Call on_batch_end() hook
        6. UPDATE batch_log with final status and counts

        Args:
            db: Async DB session.
            batch_runner: The batch runner instance to execute.

        Returns:
            Tuple of (BatchLog, BatchResult).

        Raises:
            BatchAlreadyRunningError: If same batch_type+source is already running.
        """
        config = batch_runner.config

        # --- 1. Exclusive lock check (§2-3, §5-1) ---
        await self._check_exclusive_lock(db, config.source, config.batch_type)

        # --- 2. Create batch_log (status='running') ---
        batch_log = BatchLog(
            source=config.source,
            batch_type=config.batch_type,
            feature_origin=config.feature_origin,
            status="running",
        )
        db.add(batch_log)
        await db.flush()

        # Bind batch_log_id to structlog context for correlation (Item 0-2)
        structlog.contextvars.bind_contextvars(batch_log_id=str(batch_log.id))

        logger.info(
            "batch_started",
            source=config.source,
            batch_type=config.batch_type,
        )

        result = BatchResult()

        try:
            # --- 3. on_batch_start hook ---
            await batch_runner.on_batch_start()

            # --- 4. Process items ---
            async for item in batch_runner.fetch_items(db):
                try:
                    item_result = await batch_runner.process_item(db, item)

                    if item_result.status == ItemStatus.SUCCESS:
                        result.record_success(item_result.item_id)
                    elif item_result.status == ItemStatus.SKIPPED:
                        result.record_skipped(item_result.item_id)
                    else:
                        result.record_failure(
                            item_result.item_id,
                            item_result.error_message or "Unknown error",
                            item_result.error_details,
                        )
                except Exception as exc:
                    # Per-item failure: record and continue (Principle 1)
                    item_id = getattr(item, "id", str(item))
                    logger.warning(
                        "batch_item_error",
                        item_id=item_id,
                        error=str(exc),
                    )
                    result.record_failure(
                        str(item_id),
                        str(exc),
                        {"exception_type": type(exc).__name__},
                    )

            # --- 5. on_batch_end hook ---
            await batch_runner.on_batch_end()

        except Exception as exc:
            # Fatal batch-level error
            logger.error(
                "batch_fatal_error",
                batch_log_id=str(batch_log.id),
                error=str(exc),
            )
            result.record_failure(
                "__batch__",
                f"Fatal batch error: {exc}",
                {"exception_type": type(exc).__name__},
            )

        # --- 6. Finalize batch_log ---
        batch_log.status = result.status.value
        batch_log.total_fetched = result.total_fetched
        batch_log.new_count = result.new_count
        batch_log.updated_count = result.updated_count
        batch_log.unchanged_count = result.unchanged_count
        batch_log.error_count = result.error_count
        batch_log.finished_at = datetime.now(UTC)

        # Collect error details
        error_details = [
            {
                "item_id": item.item_id,
                "error": item.error_message,
                **(item.error_details or {}),
            }
            for item in result.items
            if item.status == ItemStatus.FAILED
        ]
        if error_details:
            batch_log.error_details = error_details

        await db.flush()

        logger.info(
            "batch_completed",
            status=result.status.value,
            total=result.total_fetched,
            success=result.success_count,
            errors=result.error_count,
        )

        # Unbind batch_log_id from structlog context
        structlog.contextvars.unbind_contextvars("batch_log_id")

        return batch_log, result

    async def _check_exclusive_lock(
        self,
        db: AsyncSession,
        source: str,
        batch_type: str,
    ) -> None:
        """Ensure no running batch of the same type+source exists.

        Raises:
            BatchAlreadyRunningError: If a running batch is found.
        """
        stmt = (
            select(BatchLog.id)
            .where(
                BatchLog.source == source,
                BatchLog.batch_type == batch_type,
                BatchLog.status == "running",
            )
            .limit(1)
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing is not None:
            raise BatchAlreadyRunningError(
                message=f"Batch '{batch_type}' for source '{source}' is already running",
                details={
                    "source": source,
                    "batch_type": batch_type,
                    "running_batch_id": str(existing),
                },
            )
