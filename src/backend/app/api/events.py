"""Case Events API endpoints — SSOT-3 §4-6.

GET /api/v1/cases/:id/events — event history with filters and pagination.
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.case_event import CaseEvent
from app.schemas.envelope import PaginatedMeta, PaginatedResponse
from app.schemas.event import EventResponse

router = APIRouter(prefix="/api/v1/cases", tags=["events"])


@router.get("/{case_id}/events", response_model=PaginatedResponse)
async def list_events(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    event_type: str | None = Query(None, description="Comma-sep event types"),
    feature_origin: str | None = Query(None, description="F-001, F-002, etc."),
    triggered_by: str | None = Query(None, description="user, system, batch, cascade"),
    created_after: str | None = Query(None, description="ISO8601"),
    created_before: str | None = Query(None, description="ISO8601"),
    since_event_id: uuid.UUID | None = Query(None, description="Events after this ID"),
    since_ts: str | None = Query(None, description="Events after this timestamp"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> PaginatedResponse:
    """イベント履歴 (§4-6)."""
    stmt = select(CaseEvent).where(CaseEvent.case_id == case_id)
    count_stmt = select(func.count()).select_from(CaseEvent).where(
        CaseEvent.case_id == case_id,
    )

    # --- Filters ---
    if event_type:
        types = [t.strip() for t in event_type.split(",") if t.strip()]
        if types:
            stmt = stmt.where(CaseEvent.event_type.in_(types))
            count_stmt = count_stmt.where(CaseEvent.event_type.in_(types))

    if feature_origin:
        stmt = stmt.where(CaseEvent.feature_origin == feature_origin)
        count_stmt = count_stmt.where(CaseEvent.feature_origin == feature_origin)

    if triggered_by:
        stmt = stmt.where(CaseEvent.triggered_by == triggered_by)
        count_stmt = count_stmt.where(CaseEvent.triggered_by == triggered_by)

    if created_after:
        stmt = stmt.where(CaseEvent.created_at >= created_after)
        count_stmt = count_stmt.where(CaseEvent.created_at >= created_after)

    if created_before:
        stmt = stmt.where(CaseEvent.created_at <= created_before)
        count_stmt = count_stmt.where(CaseEvent.created_at <= created_before)

    # since_event_id takes priority over since_ts (§4-6)
    if since_event_id is not None:
        # Get the created_at of the reference event
        ref_stmt = select(CaseEvent.created_at).where(CaseEvent.id == since_event_id)
        ref_row = (await db.execute(ref_stmt)).scalar_one_or_none()
        if ref_row is not None:
            stmt = stmt.where(CaseEvent.created_at > ref_row)
            count_stmt = count_stmt.where(CaseEvent.created_at > ref_row)
    elif since_ts:
        stmt = stmt.where(CaseEvent.created_at > since_ts)
        count_stmt = count_stmt.where(CaseEvent.created_at > since_ts)

    # --- Sort ---
    stmt = stmt.order_by(CaseEvent.created_at.desc())

    # --- Pagination ---
    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / limit))

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    rows = (await db.execute(stmt)).scalars().all()

    data = [
        EventResponse.model_validate(row).model_dump(mode="json")
        for row in rows
    ]

    return PaginatedResponse(
        data=data,
        meta=PaginatedMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        ),
    )
