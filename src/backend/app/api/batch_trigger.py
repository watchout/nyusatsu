"""Batch trigger API endpoint — manual cascade trigger.

POST /api/v1/batch/trigger starts a cascade pipeline batch run.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.envelope import SuccessResponse
from app.services.batch.cascade_batch import CascadeBatch
from app.services.batch.runner import BatchRunner
from app.services.llm.mock import MockProvider

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])


@router.post("/trigger", response_model=SuccessResponse)
async def trigger_cascade(
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a cascade pipeline batch run."""
    # TODO: Use real provider from config
    provider = MockProvider()
    batch = CascadeBatch(provider)
    runner = BatchRunner()

    batch_log, result = await runner.run(db, batch)

    return SuccessResponse(data={
        "batch_log_id": str(batch_log.id),
        "status": result.status.value,
        "total_fetched": result.total_fetched,
        "success_count": result.success_count,
        "error_count": result.error_count,
    })
