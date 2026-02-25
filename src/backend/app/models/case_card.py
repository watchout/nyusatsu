"""CaseCard model — AI読解結果 (F-002)."""

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


class CaseCard(UUIDPrimaryKeyMixin, Base):
    """AI読解結果。仕様書・公告からの抽出情報（バージョン管理付き）。"""

    __tablename__ = "case_cards"
    __table_args__ = (
        UniqueConstraint("case_id", "version", name="uq_case_cards_version"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False,
    )
    # Version management
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"),
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )

    # Extracted content (JSONB)
    eligibility: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    schedule: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    business_content: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    submission_items: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    risk_factors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    # Normalized fields
    deadline_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    business_type: Mapped[str | None] = mapped_column(String(50))
    risk_level: Mapped[str | None] = mapped_column(String(10))

    # Extraction metadata
    extraction_method: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'text'"),
    )
    is_scanned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    assertion_counts: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    file_hash: Mapped[str | None] = mapped_column(String(64))

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
    )

    # Raw text
    raw_notice_text: Mapped[str | None] = mapped_column(Text)
    raw_spec_text: Mapped[str | None] = mapped_column(Text)

    # LLM tracking
    llm_model: Mapped[str | None] = mapped_column(String(100))
    llm_request_id: Mapped[str | None] = mapped_column(String(200))
    token_usage: Mapped[dict[str, int] | None] = mapped_column(JSONB)

    # Timestamps
    extracted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )

    # Relationships
    case: Mapped[Case] = relationship(back_populates="case_cards", lazy="raise")
    eligibility_results: Mapped[list[EligibilityResult]] = relationship(
        back_populates="case_card", lazy="raise",
    )
    checklists: Mapped[list[Checklist]] = relationship(
        back_populates="case_card", lazy="raise",
    )


from app.models.case import Case  # noqa: E402
from app.models.checklist import Checklist  # noqa: E402
from app.models.eligibility_result import EligibilityResult  # noqa: E402
