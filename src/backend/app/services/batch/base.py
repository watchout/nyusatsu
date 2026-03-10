"""Abstract base for batch runners — SSOT-5 §2.

Subclass ``BaseBatchRunner`` and implement:
- ``config`` property → BatchConfig
- ``fetch_items(db)`` → async iterator of items to process
- ``process_item(db, item)`` → BatchItemResult
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.batch.types import BatchConfig, BatchItemResult


class BaseBatchRunner(ABC):
    """Abstract base for all batch jobs.

    Subclass and implement the three abstract members.
    Use ``BatchRunner.run(db, runner)`` to execute with full
    logging, locking, and error handling.
    """

    @property
    @abstractmethod
    def config(self) -> BatchConfig:
        """Return the batch configuration (source, batch_type, feature_origin)."""

    @abstractmethod
    async def fetch_items(self, db: AsyncSession) -> AsyncIterator[Any]:
        """Yield items to be processed.

        Each yielded item is passed to ``process_item()``.
        Yield nothing for a 0-item batch (status=success per §2-5).
        """
        yield  # pragma: no cover

    @abstractmethod
    async def process_item(self, db: AsyncSession, item: Any) -> BatchItemResult:
        """Process a single batch item.

        Returns:
            BatchItemResult with success/failed/skipped status.

        Raises:
            Exception: Caught by BatchRunner; recorded as failure.
        """

    async def on_batch_start(self) -> None:  # noqa: B027
        """Hook called before processing starts. Override for setup."""

    async def on_batch_end(self) -> None:  # noqa: B027
        """Hook called after processing ends. Override for cleanup."""
