"""Price analysis view model — 価格分析ビュー (F-005)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, TIMESTAMP, Integer, String, literal_column, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PriceAnalysis(Base):
    """価格分析ビュー。price_historyとsuccessful_bidsを統合し、
    相場トレンド・変動率・入札競争度を可視化。
    
    Example columns:
    - case_id: 案件ID
    - avg_asking_price: 平均予定価格
    - avg_bid_price: 平均落札価格
    - price_variance_rate: 価格変動率（%）
    - avg_bidders: 平均入札社数
    - competition_index: 競争指数
    """

    __tablename__ = "price_analysis"
    __table_args__ = {"info": {"is_view": True}}

    # View columns (read-only)
    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    total_records: Mapped[int] = mapped_column(Integer)
    avg_asking_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    min_asking_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    max_asking_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    avg_bid_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    min_bid_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    max_bid_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    price_variance_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2))
    avg_bidders: Mapped[Decimal] = mapped_column(DECIMAL(8, 2))
    latest_updated: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
