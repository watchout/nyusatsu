"""Case model — 案件マスタ (F-001)."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class LifecycleStage(enum.StrEnum):
    """17-value lifecycle stage enum (SSOT-4 §3-9)."""

    # Discovery
    discovered = "discovered"
    scored = "scored"
    under_review = "under_review"
    planned = "planned"
    skipped = "skipped"
    # Reading
    reading_queued = "reading_queued"
    reading_in_progress = "reading_in_progress"
    reading_completed = "reading_completed"
    reading_failed = "reading_failed"
    # Judging
    judging_queued = "judging_queued"
    judging_in_progress = "judging_in_progress"
    judging_completed = "judging_completed"
    judging_failed = "judging_failed"
    # Preparation
    checklist_generating = "checklist_generating"
    checklist_active = "checklist_active"
    checklist_completed = "checklist_completed"
    # Archive
    archived = "archived"


class Case(UUIDPrimaryKeyMixin, Base):
    """案件マスタ。全データソースから収集された案件の統合レコード。"""

    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_cases_source_source_id"),
    )

    # Source identification
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)

    # Case info
    case_name: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_org: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_org_code: Mapped[str | None] = mapped_column(String(50))
    bid_type: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    grade: Mapped[str | None] = mapped_column(String(10))

    # Dates
    submission_deadline: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    opening_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # URLs
    spec_url: Mapped[str | None] = mapped_column(Text)
    notice_url: Mapped[str | None] = mapped_column(Text)
    detail_url: Mapped[str | None] = mapped_column(Text)

    # Status & scoring
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'new'"),
    )
    skip_reason: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer)
    score_detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Lifecycle cache
    current_lifecycle_stage: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'discovered'"),
    )

    # Raw data
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Timestamps (custom — no TimestampMixin)
    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    case_cards: Mapped[list[CaseCard]] = relationship(
        back_populates="case", lazy="raise",
    )
    eligibility_results: Mapped[list[EligibilityResult]] = relationship(
        back_populates="case", lazy="raise",
    )
    checklists: Mapped[list[Checklist]] = relationship(
        back_populates="case", lazy="raise",
    )
    events: Mapped[list[CaseEvent]] = relationship(
        back_populates="case", lazy="raise",
    )


# Avoid circular import — resolve forward refs at module level
from app.models.case_card import CaseCard  # noqa: E402
from app.models.case_event import CaseEvent  # noqa: E402
from app.models.checklist import Checklist  # noqa: E402
from app.models.eligibility_result import EligibilityResult  # noqa: E402
