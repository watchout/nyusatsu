"""Price history model — 相場データ追跡 (F-005)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class PriceHistory(UUIDPrimaryKeyMixin, Base):
    """相場データ。案件の落札価格・予定価格・入札数などを追跡。"""

    __tablename__ = "price_histories"
    __table_args__ = (
        UniqueConstraint(
            "case_id", "recorded_at", name="uq_price_history_case_recorded"
        ),
    )

    # Reference to case
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Price data (JPY)
    budgeted_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 0), comment="予定価格"
    )
    winning_bid: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 0), comment="落札価格"
    )
    lowest_bid: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 0), comment="最低入札価格"
    )
    estimated_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 0), comment="予定価格推定値"
    )

    # Bid statistics
    total_bids: Mapped[int | None] = mapped_column(comment="入札件数")
    unique_bidders: Mapped[int | None] = mapped_column(comment="入札者数")
    bid_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), comment="入札率（%）"
    )
    price_difference_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), comment="予定価格との乖離率（%）"
    )

    # Metadata
    data_source: Mapped[str | None] = mapped_column(
        String(50), comment="データソース（e.g., 自動スクレイプ、手動入力）"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, comment="データ記録日時"
    )
    confidence_score: Mapped[int | None] = mapped_column(
        comment="信頼度スコア（0-100）"
    )

    # Raw and processed data
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    analysis_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    def __repr__(self) -> str:
        return (
            f"<PriceHistory case_id={self.case_id} "
            f"winning_bid={self.winning_bid} "
            f"recorded_at={self.recorded_at}>"
        )
