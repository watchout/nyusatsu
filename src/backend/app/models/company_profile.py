"""CompanyProfile model — 会社プロフィール (F-003)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompanyProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """会社プロフィール。Phase1 では 1 固定レコード。"""

    __tablename__ = "company_profiles"

    unified_qualification: Mapped[bool] = mapped_column(Boolean, nullable=False)
    grade: Mapped[str] = mapped_column(String(10), nullable=False)
    business_categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    regions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    licenses: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb",
    )
    certifications: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb",
    )
    experience: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb",
    )
    subcontractors: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb",
    )
