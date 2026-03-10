"""Tests for Cases API — TASK-33.

Tests GET /api/v1/cases (list) and GET /api/v1/cases/:id (detail).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard

_NOW = datetime.now(UTC)


async def _create_case(
    db: AsyncSession,
    *,
    case_name: str = "テスト案件",
    issuing_org: str = "○○省",
    status: str = "new",
    lifecycle_stage: str = "discovered",
    score: int | None = None,
    submission_deadline: datetime | None = None,
    source: str = "chotatku_portal",
    source_id: str | None = None,
) -> Case:
    """Helper: insert a Case row."""
    case = Case(
        id=uuid.uuid4(),
        source=source,
        source_id=source_id or str(uuid.uuid4()),
        case_name=case_name,
        issuing_org=issuing_org,
        status=status,
        current_lifecycle_stage=lifecycle_stage,
        score=score,
        submission_deadline=submission_deadline,
        first_seen_at=_NOW,
        last_updated_at=_NOW,
    )
    db.add(case)
    await db.flush()
    return case


@pytest.mark.anyio
class TestListCases:
    """GET /api/v1/cases — list endpoint tests."""

    async def test_list_empty(self, client: AsyncClient) -> None:
        """Empty DB returns empty list with pagination meta."""
        resp = await client.get("/api/v1/cases")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0
        assert body["meta"]["total_pages"] == 1

    async def test_list_returns_cases(self, client: AsyncClient, db: AsyncSession) -> None:
        """Returns created cases."""
        await _create_case(db, case_name="案件A", score=80)
        await _create_case(db, case_name="案件B", score=60)
        await db.flush()

        resp = await client.get("/api/v1/cases")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        names = {c["case_name"] for c in body["data"]}
        assert names == {"案件A", "案件B"}

    async def test_filter_lifecycle_stage(self, client: AsyncClient, db: AsyncSession) -> None:
        """Filter by lifecycle_stage."""
        await _create_case(db, lifecycle_stage="scored")
        await _create_case(db, lifecycle_stage="under_review")
        await db.flush()

        resp = await client.get("/api/v1/cases?lifecycle_stage=scored")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["current_lifecycle_stage"] == "scored"

    async def test_filter_multiple_stages(self, client: AsyncClient, db: AsyncSession) -> None:
        """Filter by multiple comma-separated lifecycle_stages."""
        await _create_case(db, lifecycle_stage="scored")
        await _create_case(db, lifecycle_stage="under_review")
        await _create_case(db, lifecycle_stage="planned")
        await db.flush()

        resp = await client.get("/api/v1/cases?lifecycle_stage=scored,under_review")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2

    async def test_filter_score_range(self, client: AsyncClient, db: AsyncSession) -> None:
        """Filter by score_min / score_max."""
        await _create_case(db, score=30)
        await _create_case(db, score=70)
        await _create_case(db, score=90)
        await db.flush()

        resp = await client.get("/api/v1/cases?score_min=50&score_max=80")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["score"] == 70

    async def test_filter_search(self, client: AsyncClient, db: AsyncSession) -> None:
        """search= matches case_name or issuing_org."""
        await _create_case(db, case_name="配送業務委託", issuing_org="○○省")
        await _create_case(db, case_name="清掃業務委託", issuing_org="△△省")
        await db.flush()

        resp = await client.get("/api/v1/cases?search=配送")
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 1

        resp2 = await client.get("/api/v1/cases?search=△△省")
        assert resp2.status_code == 200
        assert resp2.json()["meta"]["total"] == 1

    async def test_filter_has_failed(self, client: AsyncClient, db: AsyncSession) -> None:
        """has_failed=true returns only failed-stage cases."""
        await _create_case(db, lifecycle_stage="reading_failed")
        await _create_case(db, lifecycle_stage="scored")
        await db.flush()

        resp = await client.get("/api/v1/cases?has_failed=true")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["current_lifecycle_stage"] == "reading_failed"

    async def test_exclude_archived_default(self, client: AsyncClient, db: AsyncSession) -> None:
        """Archived cases excluded by default."""
        await _create_case(db, lifecycle_stage="archived")
        await _create_case(db, lifecycle_stage="scored")
        await db.flush()

        resp = await client.get("/api/v1/cases")
        assert resp.json()["meta"]["total"] == 1

        resp2 = await client.get("/api/v1/cases?exclude_archived=false")
        assert resp2.json()["meta"]["total"] == 2

    async def test_sort_by_score_desc(self, client: AsyncClient, db: AsyncSession) -> None:
        """Sort by score descending."""
        await _create_case(db, case_name="Low", score=30)
        await _create_case(db, case_name="High", score=90)
        await db.flush()

        resp = await client.get("/api/v1/cases?sort=score:desc")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data[0]["case_name"] == "High"
        assert data[1]["case_name"] == "Low"

    async def test_sort_invalid_field_422(self, client: AsyncClient) -> None:
        """Invalid sort field returns 422."""
        resp = await client.get("/api/v1/cases?sort=invalid_field:asc")
        assert resp.status_code == 422

    async def test_pagination(self, client: AsyncClient, db: AsyncSession) -> None:
        """Pagination returns correct page and meta."""
        for i in range(5):
            await _create_case(db, case_name=f"Case-{i}")
        await db.flush()

        resp = await client.get("/api/v1/cases?page=2&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["page"] == 2
        assert body["meta"]["limit"] == 2
        assert body["meta"]["total"] == 5
        assert body["meta"]["total_pages"] == 3
        assert len(body["data"]) == 2


@pytest.mark.anyio
class TestGetCaseDetail:
    """GET /api/v1/cases/:id — detail endpoint tests."""

    async def test_get_detail(self, client: AsyncClient, db: AsyncSession) -> None:
        """Returns full case detail."""
        case = await _create_case(db, case_name="詳細テスト案件")
        await db.flush()

        resp = await client.get(f"/api/v1/cases/{case.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["case_name"] == "詳細テスト案件"
        # No includes → null
        assert body["data"]["card"] is None
        assert body["data"]["eligibility"] is None

    async def test_get_detail_404(self, client: AsyncClient) -> None:
        """Non-existent case returns 404."""
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/cases/{fake_id}")
        assert resp.status_code == 404

    async def test_include_card_current(self, client: AsyncClient, db: AsyncSession) -> None:
        """?include=card_current embeds the current CaseCard."""
        case = await _create_case(db)
        card = CaseCard(
            id=uuid.uuid4(),
            case_id=case.id,
            version=1,
            is_current=True,
            extraction_method="text",
            is_scanned=False,
            status="completed",
            created_at=_NOW,
        )
        db.add(card)
        await db.flush()

        resp = await client.get(f"/api/v1/cases/{case.id}?include=card_current")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["card"] is not None
        assert body["data"]["card"]["version"] == 1

    async def test_include_invalid_422(self, client: AsyncClient, db: AsyncSession) -> None:
        """Invalid include value returns 422."""
        case = await _create_case(db)
        await db.flush()

        resp = await client.get(f"/api/v1/cases/{case.id}?include=bad_value")
        assert resp.status_code == 422
