"""Health endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    """GET /api/v1/health should return 200 with envelope."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200

    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert body["data"]["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_health_envelope_has_request_id(client: AsyncClient):
    """Response envelope must include meta.request_id."""
    resp = await client.get("/api/v1/health")
    body = resp.json()
    assert "request_id" in body["meta"]
    assert len(body["meta"]["request_id"]) > 0
