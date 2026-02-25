"""Checklist API endpoints — F-004.

Provides read/update access to checklists.
Includes optimistic locking (TASK-35) and completion event.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import ChecklistVersionMismatchError, NotFoundError
from app.models.case import Case
from app.models.checklist import Checklist
from app.schemas.envelope import SuccessResponse
from app.services.event_service import EventService
from app.services.version_manager import VersionManager

router = APIRouter(prefix="/api/v1", tags=["checklists"])
_vm = VersionManager(Checklist)
_event_service = EventService()


class CheckItemRequest(BaseModel):
    is_checked: bool
    expected_checklist_version: int | None = None


class AddItemRequest(BaseModel):
    name: str
    category: str = "bid_time"


@router.get("/cases/{case_id}/checklist", response_model=SuccessResponse)
async def get_current_checklist(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the current Checklist for a case."""
    checklist = await _vm.get_current(db, case_id=case_id)
    if not checklist:
        raise NotFoundError(
            message="Checklist not found",
            details={"case_id": str(case_id)},
        )
    return SuccessResponse(data=_checklist_to_dict(checklist))


@router.get("/cases/{case_id}/checklists", response_model=SuccessResponse)
async def get_all_checklists(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all Checklist versions for a case."""
    checklists = await _vm.get_all_versions(db, case_id=case_id)
    return SuccessResponse(data=[_checklist_to_dict(c) for c in checklists])


@router.patch("/checklists/{checklist_id}/items/{item_index}", response_model=SuccessResponse)
async def toggle_check_item(
    checklist_id: uuid.UUID,
    item_index: int,
    body: CheckItemRequest,
    db: AsyncSession = Depends(get_db),
):
    """Toggle check/uncheck on a checklist item.

    Supports optimistic lock via expected_checklist_version (SSOT-3 §4-5).
    When all items become checked, records checklist_completed event.
    """
    stmt = select(Checklist).where(Checklist.id == checklist_id)
    result = await db.execute(stmt)
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise NotFoundError(message="Checklist not found")

    # --- Optimistic lock (TASK-35) ---
    if body.expected_checklist_version is not None:
        if body.expected_checklist_version != checklist.version:
            raise ChecklistVersionMismatchError(
                message=(
                    f"Checklist version mismatch. "
                    f"Expected {body.expected_checklist_version} "
                    f"but found {checklist.version}."
                ),
                details={
                    "expected": body.expected_checklist_version,
                    "actual": checklist.version,
                },
            )

    items = list(checklist.checklist_items)
    if item_index < 0 or item_index >= len(items):
        raise NotFoundError(message="Item index out of range")

    items[item_index] = {**items[item_index], "is_checked": body.is_checked}
    checklist.checklist_items = items

    # Recompute progress
    total = len(items)
    done = sum(1 for i in items if i.get("is_checked"))
    checklist.progress = {
        "total": total,
        "done": done,
        "rate": round(done / total, 2) if total > 0 else 0.0,
    }

    # --- Completion event (TASK-35) ---
    if done == total and total > 0:
        checklist.status = "completed"
        checklist.completed_at = datetime.now(timezone.utc)

        case = (
            await db.execute(select(Case).where(Case.id == checklist.case_id))
        ).scalar_one_or_none()
        if case:
            await _event_service.record_non_transition_event(
                db,
                case=case,
                event_type="checklist_completed",
                triggered_by="user",
                feature_origin="F-004",
                payload={
                    "checklist_id": str(checklist.id),
                    "progress": checklist.progress,
                },
            )

    await db.flush()
    return SuccessResponse(data=_checklist_to_dict(checklist))


@router.post("/checklists/{checklist_id}/items", response_model=SuccessResponse)
async def add_manual_item(
    checklist_id: uuid.UUID,
    body: AddItemRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a manual item to the checklist."""
    stmt = select(Checklist).where(Checklist.id == checklist_id)
    result = await db.execute(stmt)
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise NotFoundError(message="Checklist not found")

    items = list(checklist.checklist_items)
    items.append({
        "name": body.name,
        "category": body.category,
        "source": "manual",
        "is_checked": False,
    })
    checklist.checklist_items = items

    # Recompute progress
    total = len(items)
    done = sum(1 for i in items if i.get("is_checked"))
    checklist.progress = {
        "total": total,
        "done": done,
        "rate": round(done / total, 2) if total > 0 else 0.0,
    }

    await db.flush()
    return SuccessResponse(data=_checklist_to_dict(checklist))


def _checklist_to_dict(checklist: Checklist) -> dict:
    return {
        "id": str(checklist.id),
        "case_id": str(checklist.case_id),
        "version": checklist.version,
        "is_current": checklist.is_current,
        "checklist_items": checklist.checklist_items,
        "schedule_items": checklist.schedule_items,
        "warnings": checklist.warnings,
        "progress": checklist.progress,
        "status": checklist.status,
    }
