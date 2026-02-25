"""Tests for TASK-19: Case filter."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.services.case_fetch.filter import CaseFilter, CaseFilterCriteria


async def _seed_cases(db: AsyncSession) -> list[Case]:
    """Seed test cases for filtering."""
    cases_data = [
        {
            "source": "test",
            "source_id": "FILT-001",
            "case_name": "サーバー保守業務",
            "issuing_org": "防衛省",
            "bid_type": "一般競争入札",
            "region": "東京都",
            "grade": "A",
            "submission_deadline": datetime(2025, 5, 1, tzinfo=timezone.utc),
        },
        {
            "source": "test",
            "source_id": "FILT-002",
            "case_name": "ネットワーク構築",
            "issuing_org": "総務省",
            "bid_type": "一般競争入札",
            "region": "大阪府",
            "grade": "B",
            "submission_deadline": datetime(2025, 6, 1, tzinfo=timezone.utc),
        },
        {
            "source": "test",
            "source_id": "FILT-003",
            "case_name": "サーバー移行業務",
            "issuing_org": "防衛省",
            "bid_type": "指名競争入札",
            "region": "東京都",
            "grade": "A",
            "submission_deadline": datetime(2025, 4, 1, tzinfo=timezone.utc),
        },
        {
            "source": "test",
            "source_id": "FILT-004",
            "case_name": "清掃業務",
            "issuing_org": "厚生労働省",
            "bid_type": "一般競争入札",
            "region": "愛知県",
            "grade": "C",
            "submission_deadline": None,
        },
    ]

    cases = []
    for data in cases_data:
        c = Case(**data)
        db.add(c)
        cases.append(c)

    await db.flush()
    return cases


@pytest.mark.anyio
class TestCaseFilter:
    """Test case filtering."""

    async def test_keyword_or_match(self, db: AsyncSession):
        """Keywords use OR partial match."""
        await _seed_cases(db)
        f = CaseFilter()
        results = await f.apply(
            db,
            CaseFilterCriteria(keywords=["サーバー"]),
        )
        assert len(results) == 2  # FILT-001, FILT-003

    async def test_bid_type_filter(self, db: AsyncSession):
        """Exact bid_type match."""
        await _seed_cases(db)
        f = CaseFilter()
        results = await f.apply(
            db,
            CaseFilterCriteria(bid_type="指名競争入札"),
        )
        assert len(results) == 1
        assert results[0].source_id == "FILT-003"

    async def test_region_filter(self, db: AsyncSession):
        """Exact region match."""
        await _seed_cases(db)
        f = CaseFilter()
        results = await f.apply(
            db,
            CaseFilterCriteria(region="東京都"),
        )
        assert len(results) == 2  # FILT-001, FILT-003

    async def test_grade_filter(self, db: AsyncSession):
        """Exact grade match."""
        await _seed_cases(db)
        f = CaseFilter()
        results = await f.apply(
            db,
            CaseFilterCriteria(grade="A"),
        )
        assert len(results) == 2  # FILT-001, FILT-003

    async def test_deadline_filter(self, db: AsyncSession):
        """Deadline filter (>= threshold)."""
        await _seed_cases(db)
        f = CaseFilter()
        results = await f.apply(
            db,
            CaseFilterCriteria(
                deadline_after=datetime(2025, 4, 15, tzinfo=timezone.utc),
            ),
        )
        assert len(results) == 2  # FILT-001, FILT-002

    async def test_no_filter_returns_all(self, db: AsyncSession):
        """Empty criteria → all cases."""
        await _seed_cases(db)
        f = CaseFilter()
        results = await f.apply(db, CaseFilterCriteria())
        assert len(results) == 4

    async def test_combined_filter_no_match(self, db: AsyncSession):
        """Combined filters with no match → 0 results."""
        await _seed_cases(db)
        f = CaseFilter()
        results = await f.apply(
            db,
            CaseFilterCriteria(
                keywords=["サーバー"],
                region="愛知県",
            ),
        )
        assert len(results) == 0
