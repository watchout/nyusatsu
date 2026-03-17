"""Price analysis service — 相場データ分析と統計処理 (F-005)."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from statistics import mean, median, stdev
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Case, PriceHistory


class PriceAnalyzer:
    """相場データ分析。落札価格の統計、トレンド、スコアリング入力を生成。"""

    def __init__(self, session: AsyncSession):
        """初期化."""
        self.session = session

    async def get_price_stats(
        self,
        category: str | None = None,
        region: str | None = None,
        days_back: int = 90,
    ) -> dict[str, Any]:
        """
        カテゴリ・地域ごとの相場統計を取得。

        Args:
            category: 案件カテゴリ（None = 全体）
            region: 地域（None = 全体）
            days_back: 過去N日間のデータを対象

        Returns:
            {
                "count": 落札数,
                "avg_winning_bid": 平均落札価格,
                "median_winning_bid": 中央値,
                "std_dev": 標準偏差,
                "min": 最小,
                "max": 最大,
                "avg_bid_count": 平均入札件数,
                "avg_price_diff_rate": 平均乖離率,
            }
        """
        query = (
            sa.select(PriceHistory)
            .where(PriceHistory.winning_bid.is_not(None))
            .where(
                PriceHistory.recorded_at
                >= sa.func.now() - sa.cast(sa.literal(days_back), sa.Interval)
            )
        )

        # Apply filters
        if category:
            query = query.join(Case).where(Case.category == category)
        if region:
            query = query.join(Case).where(Case.region == region)

        result = await self.session.execute(query)
        price_histories = result.scalars().all()

        if not price_histories:
            return {
                "count": 0,
                "avg_winning_bid": None,
                "median_winning_bid": None,
                "std_dev": None,
                "min": None,
                "max": None,
                "avg_bid_count": None,
                "avg_price_diff_rate": None,
            }

        winning_bids = [
            float(ph.winning_bid) for ph in price_histories if ph.winning_bid
        ]
        bid_counts = [ph.total_bids for ph in price_histories if ph.total_bids]
        diff_rates = [
            float(ph.price_difference_rate)
            for ph in price_histories
            if ph.price_difference_rate
        ]

        stats = {
            "count": len(price_histories),
            "avg_winning_bid": (
                round(mean(winning_bids), 0) if winning_bids else None
            ),
            "median_winning_bid": (
                round(median(winning_bids), 0) if winning_bids else None
            ),
            "std_dev": (
                round(stdev(winning_bids), 0) if len(winning_bids) > 1 else None
            ),
            "min": min(winning_bids) if winning_bids else None,
            "max": max(winning_bids) if winning_bids else None,
            "avg_bid_count": (
                round(mean(bid_counts), 2) if bid_counts else None
            ),
            "avg_price_diff_rate": (
                round(mean(diff_rates), 2) if diff_rates else None
            ),
        }

        return stats

    async def analyze_price_for_case(
        self, case_id: str, category: str | None = None
    ) -> dict[str, Any]:
        """
        案件の相場データを分析。スコアリング用の相場スコアを生成。

        Args:
            case_id: 案件ID
            category: 案件カテゴリ（スタッツ取得用）

        Returns:
            {
                "recent_winning_bids": [最近の落札価格],
                "price_trend": "上昇" | "安定" | "低下",
                "competitive_level": "激戦" | "中程度" | "低競争",
                "price_score": 0-100,
                "confidence": 0-100,
                "details": {...}
            }
        """
        # Get price histories for this case
        query = sa.select(PriceHistory).where(
            PriceHistory.case_id == case_id
        ).order_by(PriceHistory.recorded_at.desc()).limit(10)

        result = await self.session.execute(query)
        histories = result.scalars().all()

        if not histories:
            return {
                "recent_winning_bids": [],
                "price_trend": "insufficient_data",
                "competitive_level": "insufficient_data",
                "price_score": 50,  # neutral
                "confidence": 0,
                "details": {"note": "no_price_data"},
            }

        winning_bids = [
            float(h.winning_bid) for h in histories if h.winning_bid
        ]
        bid_counts = [h.total_bids for h in histories if h.total_bids]

        # Determine trend (comparing first 5 vs last 5)
        if len(winning_bids) >= 2:
            recent_avg = mean(winning_bids[:5]) if len(winning_bids) >= 5 else mean(
                winning_bids
            )
            older_avg = mean(winning_bids[-5:]) if len(winning_bids) >= 5 else mean(
                winning_bids
            )
            trend_pct = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0

            if trend_pct > 5:
                price_trend = "上昇"
            elif trend_pct < -5:
                price_trend = "低下"
            else:
                price_trend = "安定"
        else:
            price_trend = "insufficient_data"

        # Determine competitiveness
        if bid_counts:
            avg_bids = mean(bid_counts)
            if avg_bids > 10:
                competitive_level = "激戦"
                price_score = 30  # High competition = lower score
            elif avg_bids > 5:
                competitive_level = "中程度"
                price_score = 60
            else:
                competitive_level = "低競争"
                price_score = 80  # Low competition = higher score
        else:
            competitive_level = "insufficient_data"
            price_score = 50

        return {
            "recent_winning_bids": winning_bids[:5],
            "price_trend": price_trend,
            "competitive_level": competitive_level,
            "price_score": price_score,
            "confidence": min(len(histories) * 10, 100),
            "details": {
                "count": len(histories),
                "avg_bid_count": round(mean(bid_counts), 2) if bid_counts else None,
                "avg_winning_bid": round(mean(winning_bids), 0) if winning_bids else None,
            },
        }

    async def import_price_data(
        self,
        case_id: str,
        price_data: dict[str, Any],
    ) -> PriceHistory:
        """
        相場データをDB に記録。

        Args:
            case_id: 案件ID
            price_data: {
                "budgeted_price": int,
                "winning_bid": int,
                "total_bids": int,
                "unique_bidders": int,
                "recorded_at": datetime,
                ...
            }

        Returns:
            PriceHistory instance
        """
        from datetime import datetime

        # Calculate price_difference_rate if needed
        price_diff_rate = None
        if (
            price_data.get("winning_bid")
            and price_data.get("budgeted_price")
        ):
            budgeted = Decimal(str(price_data["budgeted_price"]))
            winning = Decimal(str(price_data["winning_bid"]))
            if budgeted > 0:
                price_diff_rate = Decimal(
                    str(
                        round(
                            ((winning - budgeted) / budgeted * 100),
                            2,
                        )
                    )
                )

        # Create record
        history = PriceHistory(
            case_id=case_id,
            budgeted_price=(
                Decimal(str(price_data["budgeted_price"]))
                if price_data.get("budgeted_price")
                else None
            ),
            winning_bid=(
                Decimal(str(price_data["winning_bid"]))
                if price_data.get("winning_bid")
                else None
            ),
            lowest_bid=(
                Decimal(str(price_data["lowest_bid"]))
                if price_data.get("lowest_bid")
                else None
            ),
            estimated_price=(
                Decimal(str(price_data["estimated_price"]))
                if price_data.get("estimated_price")
                else None
            ),
            total_bids=price_data.get("total_bids"),
            unique_bidders=price_data.get("unique_bidders"),
            bid_rate=(
                Decimal(str(price_data["bid_rate"]))
                if price_data.get("bid_rate")
                else None
            ),
            price_difference_rate=price_diff_rate,
            data_source=price_data.get("data_source", "import"),
            recorded_at=price_data.get("recorded_at", datetime.now(UTC)),
            confidence_score=price_data.get("confidence_score", 80),
            raw_data=price_data.get("raw_data"),
        )

        self.session.add(history)
        await self.session.flush()
        return history
