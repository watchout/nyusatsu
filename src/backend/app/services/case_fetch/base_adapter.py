"""Base source adapter — F-001.

Abstract base class for all case source adapters.
Each adapter knows how to:
1. Fetch raw cases from its source
2. Store normalised cases into the DB (UPSERT on (source, source_id))

Data flow:
    Source → RawCase (adapter-specific) → normalise → cases table UPSERT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case

logger = structlog.get_logger()


@dataclass
class RawCase:
    """Raw case data from a source, before normalisation.

    The adapter populates this from its source-specific format.
    The normalizer then converts it to a dict ready for Case(**data).
    """

    source: str
    """Source identifier (e.g. 'chotatku_portal')."""

    source_id: str
    """Unique ID within the source."""

    case_name: str
    """Case title / name."""

    issuing_org: str
    """Issuing organisation name."""

    bid_type: str | None = None
    region: str | None = None
    grade: str | None = None
    deadline: date | None = None
    opening_date: date | None = None
    published_date: date | None = None
    summary: str | None = None
    detail_url: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


class StoreAction(str, Enum):
    """Result of storing a single case."""

    INSERTED = "inserted"
    UPDATED = "updated"
    SKIPPED = "skipped"


@dataclass
class StoreResult:
    """Outcome of storing a case."""

    source_id: str
    action: StoreAction
    case_id: str | None = None


class BaseSourceAdapter(ABC):
    """Abstract base for source adapters.

    Subclass and implement:
    - ``source_name`` — unique source identifier
    - ``fetch()`` — fetch raw cases from the source
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the unique source identifier."""

    @abstractmethod
    async def fetch(self) -> list[RawCase]:
        """Fetch raw cases from the source.

        Returns:
            List of RawCase objects.
        """

    async def store(
        self, db: AsyncSession, normalised: dict[str, Any],
    ) -> StoreResult:
        """UPSERT a normalised case dict into the cases table.

        Dedup on (source, source_id) UNIQUE constraint.
        Updates if deadline has changed; skips otherwise.

        Args:
            db: Async DB session.
            normalised: Dict matching Case column names.

        Returns:
            StoreResult with action taken.
        """
        source = normalised["source"]
        source_id = normalised["source_id"]

        stmt = select(Case).where(
            Case.source == source,
            Case.source_id == source_id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing is None:
            # INSERT
            case = Case(**normalised)
            db.add(case)
            await db.flush()
            logger.debug(
                "case_inserted",
                source=source,
                source_id=source_id,
            )
            return StoreResult(
                source_id=source_id,
                action=StoreAction.INSERTED,
                case_id=str(case.id),
            )

        # Check for changes (submission_deadline change = significant update)
        new_deadline = normalised.get("submission_deadline")
        old_deadline = existing.submission_deadline

        has_change = False
        if new_deadline and old_deadline and new_deadline != old_deadline:
            has_change = True
        elif normalised.get("case_name") != existing.case_name:
            has_change = True

        if not has_change:
            return StoreResult(
                source_id=source_id,
                action=StoreAction.SKIPPED,
                case_id=str(existing.id),
            )

        # UPDATE
        for key, value in normalised.items():
            if key in ("source", "source_id"):
                continue
            if hasattr(existing, key):
                setattr(existing, key, value)

        await db.flush()
        logger.debug(
            "case_updated",
            source=source,
            source_id=source_id,
        )
        return StoreResult(
            source_id=source_id,
            action=StoreAction.UPDATED,
            case_id=str(existing.id),
        )
