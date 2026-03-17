"""PriceHistory ORM model for F-005 price analysis."""

from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PriceHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Price history record for cases (F-005).
    
    Tracks budgeted price, winning bid, lowest bid, and analysis results.
    """

    __tablename__ = "price_histories"

    # Foreign key
    case_id = Column(String(36), nullable=False, index=True)

    # Price data
    budgeted_price = Column(Numeric(15, 0), nullable=True)
    winning_bid = Column(Numeric(15, 0), nullable=True)
    lowest_bid = Column(Numeric(15, 0), nullable=True)
    estimated_price = Column(Numeric(15, 0), nullable=True)

    # Statistics
    total_bids = Column(Integer(), nullable=True)
    unique_bidders = Column(Integer(), nullable=True)
    bid_rate = Column(Numeric(5, 2), nullable=True)
    price_difference_rate = Column(Numeric(5, 2), nullable=True)

    # Metadata
    data_source = Column(String(50), nullable=True)
    recorded_at = Column(TIMESTAMP(timezone=True), nullable=False)
    confidence_score = Column(Integer(), nullable=True)

    # Raw and analysis data
    raw_data = Column(JSONB(), nullable=True)
    analysis_result = Column(JSONB(), nullable=True)

    def __repr__(self) -> str:
        return f"<PriceHistory(case_id={self.case_id}, recorded_at={self.recorded_at})>"
