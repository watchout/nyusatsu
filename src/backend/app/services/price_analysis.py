"""Price analysis service for F-005 (Price Analysis)."""

from datetime import UTC, datetime
from decimal import Decimal
from statistics import median, stdev
from uuid import uuid4

from sqlalchemy import desc, select
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
        stmt = (
            select(PriceHistory)
            .filter(PriceHistory.case_id == case_id)
            .order_by(desc(PriceHistory.recorded_at))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_price_stats(self) -> dict:
        """Get price statistics across all records."""
        stmt = select(PriceHistory)
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return {
                "count": 0,
                "avg_winning_bid": None,
                "median_winning_bid": None,
                "std_dev": None,
                "avg_bid_count": None,
            }

        winning_bids = [
            float(r.winning_bid) for r in records if r.winning_bid is not None
        ]
        total_bids = [r.total_bids or 0 for r in records]

        return {
            "count": len(records),
            "avg_winning_bid": sum(winning_bids) / len(winning_bids) if winning_bids else None,
            "median_winning_bid": median(winning_bids) if winning_bids else None,
            "std_dev": stdev(winning_bids) if len(winning_bids) > 1 else None,
            "avg_bid_count": sum(total_bids) / len(total_bids) if total_bids else None,
        }

    async def analyze_price_for_case(self, case_id: str, category: str | None = None) -> dict:
        """Analyze price data for a specific case."""
        stmt = (
            select(PriceHistory)
            .filter(PriceHistory.case_id == case_id)
            .order_by(desc(PriceHistory.recorded_at))
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return {
                "recent_winning_bids": [],
                "price_trend": "insufficient_data",
                "confidence": 0,
                "price_score": 50,
            }

        # Get recent bids (last 3 months)
        recent_bids = [r.winning_bid for r in records if r.winning_bid is not None]

        # Detect price trend
        price_trend = "安定"  # stable
        if len(recent_bids) >= 2:
            if recent_bids[0] > recent_bids[-1] * 1.02:
                price_trend = "低下"  # decreasing
            elif recent_bids[0] < recent_bids[-1] * 0.98:
                price_trend = "上昇"  # increasing

        # Calculate confidence (based on number of records)
        confidence = min(100, len(records) * 20)

        # Calculate price score (100 = most favorable)
        price_score = 50
        if records:
            avg_bid_rate = sum(
                r.bid_rate or 0 for r in records if r.bid_rate is not None
            ) / len([r for r in records if r.bid_rate is not None])
            # Lower bid rate = better price (higher score)
            price_score = max(0, min(100, int(100 - avg_bid_rate)))

        return {
            "recent_winning_bids": [float(b) for b in recent_bids[:5]],
            "price_trend": price_trend,
            "confidence": confidence,
            "price_score": price_score,
        }

    async def import_price_data(self, case_id: str, data: dict) -> PriceHistory:
        """Import and store price data for a case."""
        budgeted_price = data.get("budgeted_price")
        winning_bid = data.get("winning_bid")
        lowest_bid = data.get("lowest_bid")
        estimated_price = data.get("estimated_price")
        total_bids = data.get("total_bids")
        unique_bidders = data.get("unique_bidders")
        recorded_at = data.get("recorded_at", datetime.now(UTC))

        # Calculate metrics
        bid_rate = None
        price_difference_rate = None
        confidence_score = 75  # Default confidence

        if winning_bid and budgeted_price and budgeted_price != 0:
            bid_rate = float((Decimal(winning_bid) / Decimal(budgeted_price)) * 100)
            price_difference_rate = float(
                ((Decimal(budgeted_price) - Decimal(winning_bid)) / Decimal(budgeted_price)) * 100
            )

        # Create price history record
        price_history = PriceHistory(
            id=uuid4(),
            case_id=case_id,
            budgeted_price=Decimal(str(budgeted_price)) if budgeted_price else None,
            winning_bid=Decimal(str(winning_bid)) if winning_bid else None,
            lowest_bid=Decimal(str(lowest_bid)) if lowest_bid else None,
            estimated_price=Decimal(str(estimated_price)) if estimated_price else None,
            total_bids=total_bids,
            unique_bidders=unique_bidders,
            bid_rate=bid_rate,
            price_difference_rate=price_difference_rate,
            recorded_at=recorded_at,
            confidence_score=confidence_score,
        )

        self.session.add(price_history)
        await self.session.flush()

        return price_history

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
