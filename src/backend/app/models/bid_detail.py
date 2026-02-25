"""BidDetail model — 公告詳細補完データ (F-005 Layer 2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import TIMESTAMP, BigInteger, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class BidDetail(UUIDPrimaryKeyMixin, Base):
    """公告詳細補完データ。スクレイピングで取得した追加情報。"""

    __tablename__ = "bid_details"

    base_bid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_bids.id"), nullable=False, unique=True,
    )

    num_participants: Mapped[int | None] = mapped_column(Integer)
    budget_amount: Mapped[int | None] = mapped_column(BigInteger)
    winning_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    bidder_details: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    raw_html: Mapped[str | None] = mapped_column(Text)

    scraped_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )

    # Relationships
    base_bid: Mapped[BaseBid] = relationship(back_populates="detail", lazy="raise")


from app.models.base_bid import BaseBid  # noqa: E402
