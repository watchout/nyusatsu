"""BatchLog model — バッチ実行ログ (F-001 / F-005)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class BatchLog(UUIDPrimaryKeyMixin, Base):
    """バッチ実行ログ。データ取得パイプラインの監査証跡。"""

    __tablename__ = "batch_logs"

    source: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_origin: Mapped[str] = mapped_column(String(10), nullable=False)
    batch_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Status & counts
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'running'"),
    )
    total_fetched: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    new_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    updated_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    unchanged_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    error_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )

    # Details
    error_details: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB,
    )
