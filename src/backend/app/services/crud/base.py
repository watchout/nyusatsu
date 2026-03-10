"""Generic CRUD base class for SQLAlchemy models."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase[ModelType: Base]:
    """Reusable async CRUD operations for any ORM model.

    Usage:
        crud_case = CRUDBase[Case](Case)
        case = await crud_case.get(db, id=some_uuid)
    """

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, *, id: uuid.UUID) -> ModelType | None:
        """Get a single record by primary key."""
        return await db.get(self.model, id)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        """Get multiple records with offset/limit pagination."""
        stmt = select(self.model).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """Create a new record from a dict of values."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """Update an existing record with a dict of new values."""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def count(self, db: AsyncSession) -> int:
        """Count all records."""
        stmt = select(func.count()).select_from(self.model)
        result = await db.execute(stmt)
        return result.scalar_one()
