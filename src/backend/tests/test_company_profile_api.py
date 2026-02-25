"""Tests for Company Profile API — TASK-36.

Tests GET and PATCH /api/v1/company-profile.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_profile import CompanyProfile


async def _create_profile(db: AsyncSession) -> CompanyProfile:
    profile = CompanyProfile(
        id=uuid.uuid4(),
        unified_qualification=True,
        grade="D",
        business_categories=["物品の販売", "役務の提供その他"],
        regions=["関東・甲信越"],
        licenses=[],
        certifications=[],
        experience=[],
        subcontractors=[
            {"name": "クローバー運輸", "license": "運送業", "capabilities": ["軽運送"]},
        ],
    )
    db.add(profile)
    await db.flush()
    return profile


@pytest.mark.anyio
class TestGetCompanyProfile:
    """GET /api/v1/company-profile."""

    async def test_get_profile(self, client: AsyncClient, db: AsyncSession) -> None:
        profile = await _create_profile(db)
        resp = await client.get("/api/v1/company-profile")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["grade"] == "D"
        assert data["unified_qualification"] is True

    async def test_not_found_when_no_profile(self, client: AsyncClient, db: AsyncSession) -> None:
        # Remove seed data if present
        await db.execute(delete(CompanyProfile))
        await db.flush()

        resp = await client.get("/api/v1/company-profile")
        assert resp.status_code == 404


@pytest.mark.anyio
class TestUpdateCompanyProfile:
    """PATCH /api/v1/company-profile."""

    async def test_partial_update(self, client: AsyncClient, db: AsyncSession) -> None:
        await _create_profile(db)

        resp = await client.patch(
            "/api/v1/company-profile",
            json={"licenses": ["一般貨物自動車運送事業許可"]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["licenses"] == ["一般貨物自動車運送事業許可"]
        # Other fields remain unchanged
        assert data["grade"] == "D"
        assert len(data["business_categories"]) == 2

    async def test_update_multiple_fields(self, client: AsyncClient, db: AsyncSession) -> None:
        await _create_profile(db)

        resp = await client.patch(
            "/api/v1/company-profile",
            json={
                "grade": "C",
                "experience": [{"description": "配送業務", "year": 2025}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["grade"] == "C"
        assert len(data["experience"]) == 1
