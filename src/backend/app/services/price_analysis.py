"""Price analysis service for F-005 (Price Analysis)."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PriceHistory


class PriceAnalyzer:
    """Service for analyzing and managing price data for cases."""

    def __init__(self, session: AsyncSession):
        """Initialize the analyzer with a database session."""
        self.session = session

    async def analyze_case_price(
        self,
        case_id: str,
        budgeted_price: Decimal | None = None,
        winning_bid: Decimal | None = None,
        lowest_bid: Decimal | None = None,
        estimated_price: Decimal | None = None,
        total_bids: int | None = None,
        data_source: str = "manual",
    ) -> PriceHistory:
        """Analyze price data for a case and store the result.
        
        Args:
            case_id: The case ID to analyze
            budgeted_price: Budgeted price
            winning_bid: Winning bid amount
            lowest_bid: Lowest bid amount
            estimated_price: Estimated price
            total_bids: Total number of bids
            data_source: Source of the price data
            
        Returns:
            PriceHistory: The created price history record
        """
        # Calculate metrics
        bid_rate = None
        price_difference_rate = None
        confidence_score = 75  # Default confidence

        if winning_bid and budgeted_price and budgeted_price != 0:
            bid_rate = (winning_bid / budgeted_price) * 100
            price_difference_rate = ((budgeted_price - winning_bid) / budgeted_price) * 100

        # Create price history record
        price_history = PriceHistory(
            case_id=case_id,
            budgeted_price=budgeted_price,
            winning_bid=winning_bid,
            lowest_bid=lowest_bid,
            estimated_price=estimated_price,
            total_bids=total_bids,
            bid_rate=bid_rate,
            price_difference_rate=price_difference_rate,
            data_source=data_source,
            recorded_at=datetime.now(UTC),
            confidence_score=confidence_score,
        )

        self.session.add(price_history)
        await self.session.flush()

        return price_history

    async def get_latest_price_for_case(self, case_id: str) -> PriceHistory | None:
        """Retrieve the latest price history for a case."""
        from sqlalchemy import desc, select

        stmt = (
            select(PriceHistory)
            .filter(PriceHistory.case_id == case_id)
            .order_by(desc(PriceHistory.recorded_at))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def calculate_bid_statistics(self, case_id: str) -> dict:
        """Calculate bidding statistics for a case."""
        from sqlalchemy import select

        # Get all price records for the case
        stmt = select(PriceHistory).filter(PriceHistory.case_id == case_id)
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return {}

        # Calculate averages
        total_bids = sum(r.total_bids or 0 for r in records)
        avg_bid_rate = (
            sum(r.bid_rate or 0 for r in records) / len(records) if records else None
        )

        return {
            "record_count": len(records),
            "total_bids": total_bids,
            "avg_bid_rate": avg_bid_rate,
            "latest_record": records[0] if records else None,
        }
