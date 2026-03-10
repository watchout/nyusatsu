"""Tests for Events API — TASK-36.

Tests GET /api/v1/cases/:id/events with filters and pagination.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_event import CaseEvent

_NOW = datetime.now(UTC)


async def _create_case(db: AsyncSession) -> Case:
    case = Case(
        source="test",
        source_id=f"EVT-{uuid.uuid4().hex[:8]}",
        case_name="Events Test Case",
        issuing_org="Test Org",
        current_lifecycle_stage="scored",
        first_seen_at=_NOW,
        last_updated_at=_NOW,
    )
    db.add(case)
    await db.flush()
    return case


async def _create_event(
    db: AsyncSession,
    case: Case,
    *,
    event_type: str = "case_marked_reviewed",
    triggered_by: str = "user",
    feature_origin: str = "F-001",
) -> CaseEvent:
    ev = CaseEvent(
        id=uuid.uuid4(),
        case_id=case.id,
        event_type=event_type,
        from_status="scored",
        to_status="under_review",
        triggered_by=triggered_by,
        actor_id="kaneko",
        feature_origin=feature_origin,
        created_at=_NOW,
    )
    db.add(ev)
    await db.flush()
    return ev


@pytest.mark.anyio
class TestListEvents:
    """GET /api/v1/cases/:id/events."""

    async def test_list_empty(self, client: AsyncClient, db: AsyncSession) -> None:
        case = await _create_case(db)
        resp = await client.get(f"/api/v1/cases/{case.id}/events")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    async def test_list_returns_events(self, client: AsyncClient, db: AsyncSession) -> None:
        case = await _create_case(db)
        await _create_event(db, case)
        await _create_event(db, case, event_type="case_marked_planned")

        resp = await client.get(f"/api/v1/cases/{case.id}/events")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2

    async def test_filter_event_type(self, client: AsyncClient, db: AsyncSession) -> None:
        case = await _create_case(db)
        await _create_event(db, case, event_type="case_marked_reviewed")
        await _create_event(db, case, event_type="case_marked_planned")

        resp = await client.get(
            f"/api/v1/cases/{case.id}/events?event_type=case_marked_reviewed",
        )
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 1

    async def test_filter_feature_origin(self, client: AsyncClient, db: AsyncSession) -> None:
        case = await _create_case(db)
        await _create_event(db, case, feature_origin="F-001")
        await _create_event(db, case, feature_origin="F-002")

        resp = await client.get(
            f"/api/v1/cases/{case.id}/events?feature_origin=F-002",
        )
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 1

    async def test_filter_triggered_by(self, client: AsyncClient, db: AsyncSession) -> None:
        case = await _create_case(db)
        await _create_event(db, case, triggered_by="user")
        await _create_event(db, case, triggered_by="system")

        resp = await client.get(
            f"/api/v1/cases/{case.id}/events?triggered_by=system",
        )
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 1

    async def test_pagination(self, client: AsyncClient, db: AsyncSession) -> None:
        case = await _create_case(db)
        for _ in range(5):
            await _create_event(db, case)

        resp = await client.get(
            f"/api/v1/cases/{case.id}/events?page=1&limit=2",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 5
        assert body["meta"]["total_pages"] == 3
        assert len(body["data"]) == 2
