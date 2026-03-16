"""
BatchLog モデル - バッチ実行ログ
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class BatchLog(Base):
    __tablename__ = "batch_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime]
    finished_at: Mapped[Optional[datetime]]
    status: Mapped[str] = mapped_column(String(20))
    total_fetched: Mapped[Optional[int]] = mapped_column(Integer)
    new_count: Mapped[Optional[int]] = mapped_column(Integer)
    updated_count: Mapped[Optional[int]] = mapped_column(Integer)
    unchanged_count: Mapped[Optional[int]] = mapped_column(Integer)
    error_count: Mapped[Optional[int]] = mapped_column(Integer)
    error_details: Mapped[Optional[dict]] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_batch_logs_source", "source"),
        Index("idx_batch_logs_started_at", "started_at"),
        {"extend_existing": True},
    )
