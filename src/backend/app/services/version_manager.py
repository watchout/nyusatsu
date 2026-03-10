"""Version management for re-execution tables — SSOT-4 §6.

Handles the atomic version rotation for tables with version + is_current
fields (case_cards, eligibility_results, checklists):

1. Set is_current=false on the current version
2. Insert new version with version=MAX+1, is_current=true

Both operations run in the caller's transaction (no internal commit).

## 新規テーブル追加手順

1. **Model 定義** — 以下のカラムを含むこと::

       case_id: Mapped[uuid.UUID]  = mapped_column(ForeignKey("cases.id"))
       version: Mapped[int]        = mapped_column(Integer, nullable=False)
       is_current: Mapped[bool]    = mapped_column(Boolean, nullable=False)

2. **Alembic migration** — テーブルとインデックスを作成

3. **VersionManager インスタンス化**::

       from app.services.version_manager import VersionManager
       from app.models.my_new_model import MyNewModel

       vm = VersionManager(MyNewModel)

4. **利用**::

       # 初回作成
       record = await vm.create_initial(db, data={"case_id": cid, ...})

       # 再実行 (ローテーション)
       new_record = await vm.rotate(db, case_id=cid, new_data={...})

       # 現行バージョン取得
       current = await vm.get_current(db, case_id=cid)
"""

from __future__ import annotations

import uuid
from typing import Any, TypeVar

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

VersionedModel = TypeVar("VersionedModel", bound=Base)


class VersionManager[VersionedModel: Base]:
    """Generic version rotation for versioned models.

    Usage:
        vm = VersionManager(CaseCard)
        new_card = await vm.create_initial(db, data={...})
        rotated = await vm.rotate(db, case_id=some_uuid, new_data={...})
    """

    def __init__(self, model: type[VersionedModel]) -> None:
        self.model = model

    async def get_current(
        self, db: AsyncSession, *, case_id: uuid.UUID,
    ) -> VersionedModel | None:
        """Get the is_current=true record for a case."""
        stmt = (
            select(self.model)
            .where(
                self.model.case_id == case_id,  # type: ignore[attr-defined]
                self.model.is_current.is_(True),  # type: ignore[attr-defined]
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_max_version(
        self, db: AsyncSession, *, case_id: uuid.UUID,
    ) -> int:
        """Get the maximum version number for a case (0 if none exist)."""
        stmt = (
            select(func.coalesce(func.max(self.model.version), 0))  # type: ignore[attr-defined]
            .where(self.model.case_id == case_id)  # type: ignore[attr-defined]
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_all_versions(
        self,
        db: AsyncSession,
        *,
        case_id: uuid.UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[VersionedModel]:
        """Get all versions for a case, ordered by version DESC."""
        stmt = (
            select(self.model)
            .where(self.model.case_id == case_id)  # type: ignore[attr-defined]
            .order_by(self.model.version.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_initial(
        self, db: AsyncSession, *, data: dict[str, Any],
    ) -> VersionedModel:
        """Create the first version (version=1, is_current=true).

        Caller must include case_id and all required fields in `data`.
        """
        data["version"] = 1
        data["is_current"] = True
        obj = self.model(**data)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def rotate(
        self,
        db: AsyncSession,
        *,
        case_id: uuid.UUID,
        new_data: dict[str, Any],
    ) -> VersionedModel:
        """Atomic version rotation.

        1. UPDATE: set is_current=false on existing current record(s)
        2. Compute next version = MAX(version) + 1
        3. INSERT: new record with version=next, is_current=true

        All in the caller's transaction (no commit).
        """
        # Step 1: Deactivate current version(s)
        deactivate_stmt = (
            update(self.model)
            .where(
                self.model.case_id == case_id,  # type: ignore[attr-defined]
                self.model.is_current.is_(True),  # type: ignore[attr-defined]
            )
            .values(is_current=False)
        )
        await db.execute(deactivate_stmt)

        # Step 2: Get next version number
        max_version = await self.get_max_version(db, case_id=case_id)
        next_version = max_version + 1

        # Step 3: Insert new version
        new_data["case_id"] = case_id
        new_data["version"] = next_version
        new_data["is_current"] = True
        new_obj = self.model(**new_data)
        db.add(new_obj)
        await db.flush()
        await db.refresh(new_obj)
        return new_obj
