"""EligibilityResult model — 参加可否判定結果 (F-003)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class EligibilityResult(UUIDPrimaryKeyMixin, Base):
    """参加可否判定結果。バージョン管理付き。"""

    __tablename__ = "eligibility_results"
    __table_args__ = (
        UniqueConstraint("case_id", "version", name="uq_eligibility_version"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False,
    )
    case_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case_cards.id"), nullable=False,
    )

    # Version management
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"),
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )

    # Judgment result
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    hard_fail_reasons: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    soft_gaps: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    evidence_refs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    check_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    company_profile_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
    )

    # Human override
    human_override: Mapped[str | None] = mapped_column(String(20))
    override_reason: Mapped[str | None] = mapped_column(Text)
    overridden_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    overridden_by: Mapped[str | None] = mapped_column(String(100))

    # Timestamps
    judged_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )

    # Relationships
    case: Mapped[Case] = relationship(
        back_populates="eligibility_results", lazy="raise",
    )
    case_card: Mapped[CaseCard] = relationship(
        back_populates="eligibility_results", lazy="raise",
    )
    checklists: Mapped[list[Checklist]] = relationship(
        back_populates="eligibility_result", lazy="raise",
    )


from app.models.case import Case  # noqa: E402
from app.models.case_card import CaseCard  # noqa: E402
from app.models.checklist import Checklist  # noqa: E402
