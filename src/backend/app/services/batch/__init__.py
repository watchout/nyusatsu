"""Batch processing framework — SSOT-5 §2.

Provides:
- BaseBatchRunner: ABC for implementing batch jobs
- BatchRunner: Orchestrator that manages logs, locking, and error handling
- BatchConfig, BatchItemResult, BatchResult: Type-safe data structures
"""

from app.services.batch.base import BaseBatchRunner
from app.services.batch.runner import BatchRunner
from app.services.batch.types import BatchConfig, BatchItemResult, BatchResult

__all__ = [
    "BaseBatchRunner",
    "BatchConfig",
    "BatchItemResult",
    "BatchResult",
    "BatchRunner",
]
