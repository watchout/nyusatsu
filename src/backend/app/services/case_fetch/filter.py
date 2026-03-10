"""Case filter — F-001 TASK-19.

Filters cases based on 5 criteria:
1. keywords — OR partial match on case_name
2. bid_type — exact match
3. region — exact match
4. grade — exact match
5. deadline — cases with submission_deadline >= threshold

All filters are AND-combined. Empty filter = accept all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case


@dataclass
class CaseFilterCriteria:
    """Filter criteria for case selection."""

    keywords: list[str] | None = None
    """OR partial match on case_name."""

    bid_type: str | None = None
    """Exact match on bid_type."""

    region: str | None = None
    """Exact match on region."""

    grade: str | None = None
    """Exact match on grade."""

    deadline_after: datetime | None = None
    """Only cases with submission_deadline >= this value."""


class CaseFilter:
    """Filter cases based on criteria.

    Usage::

        f = CaseFilter()
        cases = await f.apply(db, CaseFilterCriteria(keywords=["保守"]))
    """

    async def apply(
        self,
        db: AsyncSession,
        criteria: CaseFilterCriteria,
    ) -> list[Case]:
        """Apply filter criteria and return matching cases.

        Args:
            db: Async DB session.
            criteria: Filter criteria.

        Returns:
            List of matching Case objects.
        """
        conditions = self._build_conditions(criteria)

        stmt = select(Case).where(*conditions) if conditions else select(Case)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    def matches(self, case: Case, criteria: CaseFilterCriteria) -> bool:
        """Check if a single case matches the criteria (in-memory).

        Args:
            case: Case to check.
            criteria: Filter criteria.

        Returns:
            True if the case matches all criteria.
        """
        if criteria.keywords and not any(
            kw.lower() in (case.case_name or "").lower()
            for kw in criteria.keywords
        ):
            return False

        if criteria.bid_type and case.bid_type != criteria.bid_type:
            return False

        if criteria.region and case.region != criteria.region:
            return False

        if criteria.grade and case.grade != criteria.grade:
            return False

        if criteria.deadline_after:
            if not case.submission_deadline:
                return False
            if case.submission_deadline < criteria.deadline_after:
                return False

        return True

    @staticmethod
    def _build_conditions(criteria: CaseFilterCriteria) -> list:
        """Build SQLAlchemy WHERE conditions."""
        conditions: list = []

        if criteria.keywords:
            kw_conditions = [
                Case.case_name.ilike(f"%{kw}%") for kw in criteria.keywords
            ]
            conditions.append(or_(*kw_conditions))

        if criteria.bid_type:
            conditions.append(Case.bid_type == criteria.bid_type)

        if criteria.region:
            conditions.append(Case.region == criteria.region)

        if criteria.grade:
            conditions.append(Case.grade == criteria.grade)

        if criteria.deadline_after:
            conditions.append(
                Case.submission_deadline >= criteria.deadline_after,
            )

        return conditions
