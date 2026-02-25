"""BaseBid model — 落札実績ベースデータ (F-005 Layer 1)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import TIMESTAMP, BigInteger, Date, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class BaseBid(UUIDPrimaryKeyMixin, Base):
    """落札実績ベースデータ。オープンデータから取得した基本情報。"""

    __tablename__ = "base_bids"

    source_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    case_name: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_org: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_org_code: Mapped[str | None] = mapped_column(String(50))
    bid_type: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(String(100))

    # Financial
    winning_amount: Mapped[int | None] = mapped_column(BigInteger)
    winning_bidder: Mapped[str | None] = mapped_column(String(200))

    # Dates
    opening_date: Mapped[date | None] = mapped_column(Date)
    contract_date: Mapped[date | None] = mapped_column(Date)

    # URLs & raw data
    detail_url: Mapped[str | None] = mapped_column(Text)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Timestamp
    imported_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )

    # Relationships
    detail: Mapped[BidDetail | None] = relationship(
        back_populates="base_bid", lazy="raise", uselist=False,
    )


from app.models.bid_detail import BidDetail  # noqa: E402
