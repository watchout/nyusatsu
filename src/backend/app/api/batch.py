"""Batch management API endpoints — SSOT-3 §4-7.

GET /api/v1/batch/latest    — latest batch status
GET /api/v1/batch/logs      — batch history (paginated)
GET /api/v1/batch/logs/:id  — batch detail
POST /api/v1/batch/trigger  — manual trigger
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.batch_log import BatchLog
from app.schemas.batch import BatchLogResponse
from app.schemas.envelope import PaginatedMeta, PaginatedResponse, SuccessResponse
from app.services.batch.cascade_batch import CascadeBatch
from app.services.batch.runner import BatchRunner
from app.services.llm.mock import MockProvider

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])


def _batch_to_dict(log: BatchLog) -> dict:
    return BatchLogResponse(
        id=log.id,
        source=log.source,
        feature_origin=log.feature_origin,
        batch_type=log.batch_type,
        started_at=log.started_at,
        finished_at=log.finished_at,
        status=log.status,
        total_fetched=log.total_fetched,
        new_count=log.new_count,
        updated_count=log.updated_count,
        unchanged_count=log.unchanged_count,
        error_count=log.error_count,
        error_details=log.error_details,
        metadata=log.metadata_,
    ).model_dump(mode="json")


@router.get("/latest", response_model=SuccessResponse)
async def get_latest_batch(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SuccessResponse:
    """最新バッチ状態 (§4-7)."""
    stmt = select(BatchLog).order_by(BatchLog.started_at.desc()).limit(1)
    log = (await db.execute(stmt)).scalar_one_or_none()

    if log is None:
        return SuccessResponse(data=None)

    return SuccessResponse(data=_batch_to_dict(log))


@router.get("/logs", response_model=PaginatedResponse)
async def list_batch_logs(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    page: int = Query(1, ge=1),  # noqa: B008
    limit: int = Query(20, ge=1, le=100),  # noqa: B008
) -> PaginatedResponse:
    """バッチ履歴 (§4-7)."""
    count_stmt = select(func.count()).select_from(BatchLog)
    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / limit))

    offset = (page - 1) * limit
    stmt = (
        select(BatchLog)
        .order_by(BatchLog.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedResponse(
        data=[_batch_to_dict(log) for log in rows],
        meta=PaginatedMeta(
            page=page, limit=limit, total=total, total_pages=total_pages,
        ),
    )


@router.get("/logs/{log_id}", response_model=SuccessResponse)
async def get_batch_log(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SuccessResponse:
    """バッチ詳細 (§4-7)."""
    stmt = select(BatchLog).where(BatchLog.id == log_id)
    log = (await db.execute(stmt)).scalar_one_or_none()

    if log is None:
        raise NotFoundError(
            message="BatchLog not found",
            details={"log_id": str(log_id)},
        )

    return SuccessResponse(data=_batch_to_dict(log))


@router.post("/trigger", response_model=SuccessResponse)
async def trigger_cascade(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SuccessResponse:
    """手動バッチ起動 (§4-7)."""
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
