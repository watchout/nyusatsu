"""Tests for TASK-22: Case action API endpoints (9 actions)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case


async def _create_case(
    db: AsyncSession,
    stage: str = "discovered",
    suffix: str = "001",
) -> Case:
    """Create a test case at a specific lifecycle stage."""
    case = Case(
        source="test",
        source_id=f"ACTION-{suffix}",
        case_name=f"Action Test Case {suffix}",
        issuing_org="Test Org",
        current_lifecycle_stage=stage,
    )
    db.add(case)
    await db.flush()
    return case


@pytest.mark.anyio
class TestMarkReviewed:
    """POST /cases/:id/actions/mark-reviewed."""

    async def test_scored_to_under_review(self, client: AsyncClient, db: AsyncSession):
        """scored → under_review succeeds."""
        case = await _create_case(db, "scored", "reviewed-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/mark-reviewed",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "under_review"

    async def test_skipped_to_under_review(self, client: AsyncClient, db: AsyncSession):
        """skipped → under_review (T25) succeeds."""
        case = await _create_case(db, "skipped", "reviewed-2")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/mark-reviewed",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "under_review"

    async def test_invalid_stage_returns_409(self, client: AsyncClient, db: AsyncSession):
        """discovered → under_review is not a valid transition → 409."""
        case = await _create_case(db, "discovered", "reviewed-3")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/mark-reviewed",
        )
        assert resp.status_code == 409


@pytest.mark.anyio
class TestMarkPlanned:
    """POST /cases/:id/actions/mark-planned."""

    async def test_under_review_to_reading_queued(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """under_review → planned → reading_queued (cascade)."""
        case = await _create_case(db, "under_review", "planned-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/mark-planned",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        # After cascade, should be reading_queued
        assert data["current_lifecycle_stage"] == "reading_queued"


@pytest.mark.anyio
class TestMarkSkipped:
    """POST /cases/:id/actions/mark-skipped."""

    async def test_under_review_to_skipped(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """under_review → skipped with reason."""
        case = await _create_case(db, "under_review", "skipped-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/mark-skipped",
            json={"reason": "予算オーバー"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "skipped"

    async def test_missing_reason_returns_422(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """Missing reason → 422 validation error."""
        case = await _create_case(db, "under_review", "skipped-2")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/mark-skipped",
            json={},
        )
        assert resp.status_code == 422


@pytest.mark.anyio
class TestRestore:
    """POST /cases/:id/actions/restore."""

    async def test_skipped_to_under_review(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """skipped → under_review (restore)."""
        case = await _create_case(db, "skipped", "restore-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/restore",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "under_review"


@pytest.mark.anyio
class TestArchive:
    """POST /cases/:id/actions/archive."""

    async def test_archive_from_discovered(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """discovered → archived."""
        case = await _create_case(db, "discovered", "archive-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/archive",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "archived"

    async def test_archive_from_scored(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """scored → archived."""
        case = await _create_case(db, "scored", "archive-2")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/archive",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "archived"


@pytest.mark.anyio
class TestRetryReading:
    """POST /cases/:id/actions/retry-reading."""

    async def test_reading_failed_to_reading_queued(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """reading_failed → reading_queued."""
        case = await _create_case(db, "reading_failed", "retry-r-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/retry-reading",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "reading_queued"


@pytest.mark.anyio
class TestRetryJudging:
    """POST /cases/:id/actions/retry-judging."""

    async def test_judging_failed_to_judging_queued(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """judging_failed → judging_queued."""
        case = await _create_case(db, "judging_failed", "retry-j-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/retry-judging",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "judging_queued"


@pytest.mark.anyio
class TestRetryChecklist:
    """POST /cases/:id/actions/retry-checklist."""

    async def test_checklist_active_to_generating(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """checklist_active → checklist_generating."""
        case = await _create_case(db, "checklist_active", "retry-c-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/retry-checklist",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "checklist_generating"


@pytest.mark.anyio
class TestOverride:
    """POST /cases/:id/actions/override."""

    async def test_override_records_event(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """Override creates non-transition event."""
        case = await _create_case(db, "scored", "override-1")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/override",
            json={"reason": "手動判定", "verdict": "approved"},
        )
        assert resp.status_code == 200
        # Stage should not change
        data = resp.json()["data"]
        assert data["current_lifecycle_stage"] == "scored"

    async def test_override_missing_reason_422(
        self, client: AsyncClient, db: AsyncSession,
    ):
        """Missing reason → 422."""
        case = await _create_case(db, "scored", "override-2")
        resp = await client.post(
            f"/api/v1/cases/{case.id}/actions/override",
            json={},
        )
        assert resp.status_code == 422


@pytest.mark.anyio
class TestNotFound:
    """Non-existent case → 404."""

    async def test_not_found(self, client: AsyncClient):
        """Invalid UUID → 404."""
        resp = await client.post(
            "/api/v1/cases/00000000-0000-0000-0000-000000000000/actions/mark-reviewed",
        )
        assert resp.status_code == 404
