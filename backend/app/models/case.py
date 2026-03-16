"""
Case モデル - 入札案件
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    case_name: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_org: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_org_code: Mapped[Optional[str]] = mapped_column(String(50))
    bid_type: Mapped[Optional[str]] = mapped_column(String(50))
    category: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    grade: Mapped[Optional[str]] = mapped_column(String(10))
    submission_deadline: Mapped[Optional[datetime]]
    opening_date: Mapped[Optional[datetime]]
    spec_url: Mapped[Optional[str]] = mapped_column(Text)
    notice_url: Mapped[Optional[str]] = mapped_column(Text)
    detail_url: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new")
    skip_reason: Mapped[Optional[str]] = mapped_column(Text)
    score: Mapped[Optional[int]] = mapped_column(Integer)
    score_detail: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    first_seen_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
    archived_at: Mapped[Optional[datetime]]

    __table_args__ = (
        Index("idx_cases_status", "status"),
        Index("idx_cases_score", "score"),
        Index("idx_cases_submission_deadline", "submission_deadline"),
        {"extend_existing": True},
    )
