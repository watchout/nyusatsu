"""Scoring algorithm v2 — 相場データを組み込んだスコアリング (F-005)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.price_analysis import PriceAnalyzer

if TYPE_CHECKING:
    from app.models import Case


class ScoringV2:
    """
    相場データ統合スコアリング。

    スコア構成:
    - 期限余裕スコア（30%）
    - 相場スコア（40%）
    - カテゴリ適合度（20%）
    - ボーナス（10%）
    """

    def __init__(self, session: AsyncSession):
        """初期化."""
        self.session = session
        self.price_analyzer = PriceAnalyzer(session)

    async def calculate_comprehensive_score(
        self, case: Case
    ) -> dict[str, Any]:
        """
        包括的スコア算出。複数の要因を組み合わせてスコア化。

        Args:
            case: Case instance

        Returns:
            {
                "score": 0-100,
                "score_breakdown": {
                    "deadline_score": int,
                    "price_score": int,
                    "category_score": int,
                    "bonus_score": int,
                },
                "factors": {
                    "days_left": int,
                    "price_trend": str,
                    "competitive_level": str,
                    "category": str,
                },
                "recommendation": "推奨" | "検討" | "非推奨",
                "confidence": 0-100,
            }
        """
        scores = {}

        # 1. Deadline score (30%)
        deadline_score = self._calculate_deadline_score(case)
        scores["deadline_score"] = deadline_score

        # 2. Price score (40%)
        price_analysis = await self.price_analyzer.analyze_price_for_case(
            case.id, category=case.category
        )
        price_score = price_analysis.get("price_score", 50)
        scores["price_score"] = price_score

        # 3. Category score (20%)
        category_score = self._calculate_category_score(case)
        scores["category_score"] = category_score

        # 4. Bonus score (10%)
        bonus_score = self._calculate_bonus_score(case)
        scores["bonus_score"] = bonus_score

        # Weighted calculation
        weighted_score = (
            deadline_score * 0.30
            + price_score * 0.40
            + category_score * 0.20
            + bonus_score * 0.10
        )

        overall_score = int(round(weighted_score))

        # Determine recommendation
        if overall_score >= 70:
            recommendation = "推奨"
        elif overall_score >= 50:
            recommendation = "検討"
        else:
            recommendation = "非推奨"

        return {
            "score": overall_score,
            "score_breakdown": scores,
            "factors": {
                "days_left": self._get_days_left(case),
                "price_trend": price_analysis.get("price_trend"),
                "competitive_level": price_analysis.get("competitive_level"),
                "category": case.category,
            },
            "recommendation": recommendation,
            "confidence": price_analysis.get("confidence", 0),
        }

    def _calculate_deadline_score(self, case: Case) -> int:
        """期限までの日数でスコア化（0-100）."""
        if not case.submission_deadline:
            return 50  # default

        deadline = case.submission_deadline
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)

        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        days_left = (deadline - now).days

        # Adjusted scale for F-005
        if days_left >= 21:
            return 100
        elif days_left >= 14:
            return 85
        elif days_left >= 10:
            return 70
        elif days_left >= 7:
            return 55
        elif days_left >= 4:
            return 40
        elif days_left >= 1:
            return 20
        else:
            return 0

    def _calculate_category_score(self, case: Case) -> int:
        """
        カテゴリ別の適合度スコア。
        ハードコードとしてシンプルに。実装時は動的化。
        """
        # Simplified: categories with higher priority get higher scores
        category_map = {
            "建築": 90,
            "土木": 85,
            "設計": 80,
            "コンサル": 75,
            "その他": 50,
        }
        return category_map.get(case.category or "その他", 50)

    def _calculate_bonus_score(self, case: Case) -> int:
        """ボーナススコア（特定条件で加点）."""
        bonus = 50  # base

        # Late-opening (more time to prepare)
        if case.submission_deadline and case.opening_date:
            prep_time = (case.submission_deadline - case.opening_date).days
            if prep_time > 30:
                bonus = min(bonus + 20, 100)

        # Government-issued (more reliable)
        if case.issuing_org:
            if any(
                keyword in case.issuing_org
                for keyword in ["国", "都道府県", "市区町村"]
            ):
                bonus = min(bonus + 15, 100)

        return bonus

    def _get_days_left(self, case: Case) -> int | None:
        """期限までの日数を計算."""
        if not case.submission_deadline:
            return None

        deadline = case.submission_deadline
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)

        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        return (deadline - now).days


async def calculate_score_for_case(
    session: AsyncSession, case: Case
) -> dict[str, Any]:
    """
    便利関数。案件に対して v2 スコアを計算。

    Args:
        session: AsyncSession
        case: Case instance

    Returns:
        Score details dict
    """
    scorer = ScoringV2(session)
    return await scorer.calculate_comprehensive_score(case)
