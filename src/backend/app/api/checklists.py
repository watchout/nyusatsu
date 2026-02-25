"""Checklist API endpoints — F-004.

Provides read/update access to checklists.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.checklist import Checklist
from app.schemas.envelope import SuccessResponse
from app.services.version_manager import VersionManager

router = APIRouter(prefix="/api/v1", tags=["checklists"])
_vm = VersionManager(Checklist)


class CheckItemRequest(BaseModel):
    is_checked: bool


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
    """Toggle check/uncheck on a checklist item."""
    stmt = select(Checklist).where(Checklist.id == checklist_id)
    result = await db.execute(stmt)
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise NotFoundError(message="Checklist not found")

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
