"""Price history model — 価格履歴データ (F-005)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, TIMESTAMP, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.case import Case


class PriceHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """価格履歴レコード。案件ごとの相場変動を追跡。F-005相場データベース層。"""

    __tablename__ = "price_history"
    __table_args__ = (
        Index("idx_price_history_case_id", "case_id"),
        Index("idx_price_history_recorded_at", "recorded_at"),
        Index("idx_price_history_case_recorded", "case_id", "recorded_at"),
        UniqueConstraint("case_id", "source", "recorded_at", name="uq_price_history_unique_entry"),
    )

    # Foreign key
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Price data
    asking_price: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=True)
    estimated_price: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=True)
    lowest_bid: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=True)
    highest_bid: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=True)

    # Metadata
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="相場情報の出典 (public_data, internal, external_partner)",
    )
    data_source: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="具体的なデータソース (URL、システム名など)",
    )
    currency: Mapped[str] = mapped_column(String(3), default="JPY", nullable=False)
    confidence_score: Mapped[float] = mapped_column(DECIMAL(3, 2), nullable=True, comment="データ信頼度 (0.00-1.00)")

    # Historical tracking
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="データが記録された日時",
    )
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships (lazy loading, no circular import)
    case: Mapped[Case] = relationship("Case", foreign_keys=[case_id])


class SuccessfulBids(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """落札実績。過去の成約価格を記録し分析の基準として使用。"""

    __tablename__ = "successful_bids"
    __table_args__ = (
        Index("idx_successful_bids_case_id", "case_id"),
        Index("idx_successful_bids_bid_date", "bid_date"),
        Index("idx_successful_bids_case_date", "case_id", "bid_date"),
    )

    # Foreign key
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Bid data
    final_price: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=False)
    number_of_bidders: Mapped[int] = mapped_column(Integer, nullable=True)
    winning_company: Mapped[str] = mapped_column(String(255), nullable=True)

    # Temporal data
    bid_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="入札実施日時",
    )
    contract_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="契約成立日時",
    )

    # Metadata
    source: Mapped[str] = mapped_column(String(50), nullable=False, comment="成約情報の出典")
    currency: Mapped[str] = mapped_column(String(3), default="JPY", nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships (lazy loading, no circular import)
    case: Mapped[Case] = relationship("Case", foreign_keys=[case_id])
