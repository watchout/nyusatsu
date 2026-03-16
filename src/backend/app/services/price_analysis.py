"""Price analysis service — 価格分析サービス (F-005).

提供機能:
- 平均価格算出 (average price calculation)
- 価格変動率計算 (price variance rate)
- 競争指数計算 (competition index)
- Historical data query methods
- Price trend detection
- Case-specific analysis
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory, SuccessfulBids

logger = structlog.get_logger()


class PriceAnalyzer:
    """価格分析サービス。price_historyおよびsuccessful_bidsを分析。
    
    機能:
    - 統計情報取得（平均、中央値、標準偏差）
    - 案件別分析（価格トレンド、競争度）
    - 相場データインポート
    - 競争レベル判定
    """

    def __init__(self, session: AsyncSession):
        """Initialize with async database session."""
        self.session = session

    async def get_price_stats(self) -> dict[str, Any]:
        """全体的な価格統計を取得。
        
        Returns:
            {
                "count": int,
                "avg_winning_bid": Optional[Decimal],
                "median_winning_bid": Optional[Decimal],
                "min_winning_bid": Optional[Decimal],
                "max_winning_bid": Optional[Decimal],
                "std_dev": Optional[Decimal],
                "avg_bid_count": Optional[float],
            }
        """
        stmt = select(
            func.count(SuccessfulBids.id).label("count"),
            func.avg(SuccessfulBids.final_price).label("avg_price"),
            func.percentile_cont(0.5).within_group(
                SuccessfulBids.final_price
            ).label("median_price"),
            func.min(SuccessfulBids.final_price).label("min_price"),
            func.max(SuccessfulBids.final_price).label("max_price"),
            func.stddev(SuccessfulBids.final_price).label("std_dev"),
            func.avg(SuccessfulBids.number_of_bidders).label("avg_bidders"),
        ).where(
            SuccessfulBids.final_price > 0
        )

        result = await self.session.execute(stmt)
        row = result.one()

        return {
            "count": row.count or 0,
            "avg_winning_bid": row.avg_price,
            "median_winning_bid": row.median_price,
            "min_winning_bid": row.min_price,
            "max_winning_bid": row.max_price,
            "std_dev": row.std_dev,
            "avg_bid_count": float(row.avg_bidders) if row.avg_bidders else None,
        }

    async def analyze_price_for_case(
        self,
        case_id: str,
        category: str | None = None,
        days_lookback: int = 180,
    ) -> dict[str, Any]:
        """案件に対する相場分析。
        
        Args:
            case_id: Case ID
            category: Optional category filter
            days_lookback: How many days back to analyze (default 180 days)
        
        Returns:
            {
                "case_id": str,
                "recent_winning_bids": list[dict],
                "avg_price": Optional[Decimal],
                "price_variance_rate": Optional[Decimal],
                "price_trend": "上昇" | "低下" | "安定" | "insufficient_data",
                "competitive_level": "激戦" | "競争" | "閑散" | "insufficient_data",
                "competition_index": Optional[float],
                "confidence": int (0-100),
                "price_score": int (0-100),
            }
        """
        # Get historical winning bids for this case
        cutoff_date = datetime.now(UTC) - timedelta(days=days_lookback)
        
        stmt = (
            select(
                SuccessfulBids.final_price,
                SuccessfulBids.number_of_bidders,
                SuccessfulBids.bid_date,
            )
            .where(
                and_(
                    SuccessfulBids.case_id == case_id,
                    SuccessfulBids.bid_date >= cutoff_date,
                    SuccessfulBids.final_price > 0,
                )
            )
            .order_by(desc(SuccessfulBids.bid_date))
            .limit(50)
        )

        results = await self.session.execute(stmt)
        bids = results.all()

        if not bids:
            return {
                "case_id": case_id,
                "recent_winning_bids": [],
                "avg_price": None,
                "price_variance_rate": None,
                "price_trend": "insufficient_data",
                "competitive_level": "insufficient_data",
                "competition_index": None,
                "confidence": 0,
                "price_score": 50,
            }

        # Calculate statistics
        prices = [bid[0] for bid in bids]
        bidder_counts = [bid[1] for bid in bids if bid[1] is not None]

        avg_price = sum(prices) / len(prices) if prices else None
        std_dev = self._calculate_std_dev(prices) if len(prices) > 1 else Decimal(0)
        variance_rate = (std_dev / avg_price * 100) if avg_price and avg_price > 0 else Decimal(0)

        # Detect trend
        price_trend = self._detect_price_trend(prices)

        # Calculate competition index and level
        avg_bidders = sum(bidder_counts) / len(bidder_counts) if bidder_counts else 0
        competition_index = self._calculate_competition_index(
            avg_bidders, variance_rate
        )
        competitive_level = self._determine_competitive_level(competition_index)

        # Calculate confidence based on data points
        confidence = min(len(bids) * 15, 95)  # Max 95% with enough data

        # Calculate price score
        price_score = self._calculate_price_score(
            avg_price, variance_rate, competition_index
        )

        return {
            "case_id": case_id,
            "recent_winning_bids": [
                {
                    "final_price": float(bid[0]),
                    "number_of_bidders": bid[1],
                    "bid_date": bid[2].isoformat() if bid[2] else None,
                }
                for bid in bids
            ],
            "avg_price": avg_price,
            "price_variance_rate": variance_rate,
            "price_trend": price_trend,
            "competitive_level": competitive_level,
            "competition_index": float(competition_index) if competition_index else None,
            "confidence": confidence,
            "price_score": price_score,
        }

    async def import_price_data(
        self,
        case_id: str,
        price_data: dict[str, Any],
    ) -> PriceHistory:
        """Import price data as a PriceHistory record.
        
        Args:
            case_id: Case ID
            price_data: Dict with keys like:
                - budgeted_price: Initial asking price
                - winning_bid: Final winning price
                - total_bids: Total number of bids received
                - unique_bidders: Count of unique bidders
                - recorded_at: DateTime of record
                - source: Data source (default: "internal")
        
        Returns:
            Newly created PriceHistory instance (not yet flushed)
        """
        budgeted = Decimal(str(price_data.get("budgeted_price", 0)))
        winning = Decimal(str(price_data.get("winning_bid", 0)))

        history = PriceHistory(
            case_id=case_id,
            asking_price=budgeted,
            lowest_bid=winning,
            highest_bid=winning,  # Will be updated if more data available
            estimated_price=None,
            source=price_data.get("source", "internal"),
            data_source=price_data.get("data_source"),
            currency="JPY",
            confidence_score=Decimal(price_data.get("confidence_score", 0.80)),
            recorded_at=price_data.get("recorded_at", datetime.now(UTC)),
            notes=price_data.get("notes"),
        )

        self.session.add(history)
        return history

    async def get_category_price_benchmark(
        self,
        category: str,
        days_lookback: int = 180,
    ) -> dict[str, Any]:
        """カテゴリ別の相場ベンチマークを取得。
        
        Args:
            category: Category name
            days_lookback: Days to look back
        
        Returns:
            {
                "category": str,
                "count": int,
                "avg_price": Optional[Decimal],
                "median_price": Optional[Decimal],
                "std_dev": Optional[Decimal],
                "min_price": Optional[Decimal],
                "max_price": Optional[Decimal],
            }
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days_lookback)

        stmt = (
            select(
                func.count(SuccessfulBids.id).label("count"),
                func.avg(SuccessfulBids.final_price).label("avg_price"),
                func.percentile_cont(0.5).within_group(
                    SuccessfulBids.final_price
                ).label("median_price"),
                func.stddev(SuccessfulBids.final_price).label("std_dev"),
                func.min(SuccessfulBids.final_price).label("min_price"),
                func.max(SuccessfulBids.final_price).label("max_price"),
            )
            .select_from(SuccessfulBids)
            .join(
                PriceHistory,
                PriceHistory.case_id == SuccessfulBids.case_id,
            )
            .where(
                and_(
                    SuccessfulBids.bid_date >= cutoff_date,
                    SuccessfulBids.final_price > 0,
                )
            )
        )

        result = await self.session.execute(stmt)
        row = result.one()

        return {
            "category": category,
            "count": row.count or 0,
            "avg_price": row.avg_price,
            "median_price": row.median_price,
            "std_dev": row.std_dev,
            "min_price": row.min_price,
            "max_price": row.max_price,
        }

    # ========================================================================
    # Private helper methods
    # ========================================================================

    def _calculate_std_dev(self, values: list[Decimal]) -> Decimal:
        """Calculate standard deviation."""
        if len(values) < 2:
            return Decimal(0)

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance.sqrt()

    def _detect_price_trend(self, prices: list[Decimal]) -> str:
        """Detect price trend from historical prices.
        
        Returns:
            "上昇" | "低下" | "安定"
        """
        if len(prices) < 2:
            return "insufficient_data"

        # Prices are ordered newest first, so reverse for chronological order
        prices_chrono = list(reversed(prices))

        # Simple trend: compare first half vs second half
        mid = len(prices_chrono) // 2
        first_half = sum(prices_chrono[:mid]) / len(prices_chrono[:mid])
        second_half = sum(prices_chrono[mid:]) / len(prices_chrono[mid:])

        diff_pct = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

        if diff_pct > 2:
            return "上昇"
        elif diff_pct < -2:
            return "低下"
        else:
            return "安定"

    def _calculate_competition_index(
        self,
        avg_bidders: float,
        variance_rate: Decimal,
    ) -> Decimal:
        """計算競争指数 = 平均入札社数 + 価格変動率.
        
        Higher index = more competition.
        """
        if avg_bidders <= 0:
            return Decimal(0)

        return Decimal(str(avg_bidders)) + variance_rate

    def _determine_competitive_level(self, competition_index: Decimal) -> str:
        """Determine competitive level from competition index.
        
        Returns:
            "激戦" | "競争" | "閑散"
        """
        if competition_index >= 10:
            return "激戦"
        elif competition_index >= 5:
            return "競争"
        else:
            return "閑散"

    def _calculate_price_score(
        self,
        avg_price: Decimal | None,
        variance_rate: Decimal,
        competition_index: Decimal,
    ) -> int:
        """相場スコアを算出（0-100）。
        
        低い価格変動と適度な競争が高スコア。
        """
        if avg_price is None or avg_price == 0:
            return 50

        # Base score
        score = 50

        # Adjust for price stability (lower variance = better)
        variance_factor = min(float(variance_rate) / 20, 1.0)
        score += int((1 - variance_factor) * 25)  # Max +25

        # Adjust for competition (moderate competition = better)
        if competition_index < 5:
            score -= 15
        elif 5 <= competition_index < 15:
            score += 15
        else:
            score += 10

        return max(0, min(100, score))
