"""Checklist model — チェックリスト (F-004)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Checklist(UUIDPrimaryKeyMixin, Base):
    """チェックリスト。入札準備用（バージョン管理付き）。"""

    __tablename__ = "checklists"
    __table_args__ = (
        UniqueConstraint("case_id", "version", name="uq_checklists_version"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False,
    )
    case_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case_cards.id"), nullable=False,
    )
    eligibility_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eligibility_results.id"), nullable=False,
    )

    # Version management
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"),
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )

    # Checklist content
    checklist_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False,
    )
    schedule_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False,
    )
    warnings: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{\"total\": 0, \"done\": 0, \"rate\": 0.0}'::jsonb"),
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'draft'"),
    )
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )

    # Relationships
    case: Mapped[Case] = relationship(back_populates="checklists", lazy="raise")
    case_card: Mapped[CaseCard] = relationship(
        back_populates="checklists", lazy="raise",
    )
    eligibility_result: Mapped[EligibilityResult] = relationship(
        back_populates="checklists", lazy="raise",
    )


from app.models.case import Case  # noqa: E402
from app.models.case_card import CaseCard  # noqa: E402
from app.models.eligibility_result import EligibilityResult  # noqa: E402
