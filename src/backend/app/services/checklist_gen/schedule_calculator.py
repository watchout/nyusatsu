"""Schedule calculator for F-004.

Computes 4-stage reverse schedule from the submission deadline,
using business day calculation with Japanese holidays.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import jpholiday
import structlog

from app.core.constants import (
    SCHEDULE_REVERSE_FINALIZE_BD,
    SCHEDULE_REVERSE_REVIEW_BD,
    SCHEDULE_REVERSE_START_BD,
)

logger = structlog.get_logger()


def _is_business_day(d: date) -> bool:
    """Check if a date is a business day (not weekend, not Japanese holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return not jpholiday.is_holiday(d)


def _reverse_business_days(base_date: date, offset: int) -> date:
    """Go back `offset` business days from base_date.

    offset should be negative (e.g., -5 = 5 business days before).
    """
    if offset >= 0:
        return base_date

    current = base_date
    remaining = abs(offset)
    while remaining > 0:
        current -= timedelta(days=1)
        if _is_business_day(current):
            remaining -= 1
    return current


class ScheduleCalculator:
    """Calculate reverse schedule from deadline."""

    def calculate(
        self,
        deadline_at: datetime | date | None,
        *,
        quote_deadline: str | None = None,
    ) -> list[dict[str, Any]]:
        """Calculate 4-stage reverse schedule.

        Stages:
          1. 準備開始 (-5BD from deadline)
          2. 書類レビュー (-2BD)
          3. 最終確認 (-1BD)
          4. 提出期限 (0BD = deadline)

        Args:
            deadline_at: The submission deadline.
            quote_deadline: Optional separate quote deadline string.

        Returns:
            List of schedule stage dicts.
        """
        if deadline_at is None:
            return []

        base = deadline_at.date() if isinstance(deadline_at, datetime) else deadline_at

        stages: list[dict[str, Any]] = []

        # Stage 1: Start preparation
        start = _reverse_business_days(base, SCHEDULE_REVERSE_START_BD)
        stages.append({
            "stage": "準備開始",
            "date": start.isoformat(),
            "offset_bd": SCHEDULE_REVERSE_START_BD,
            "description": "必要書類の収集・作成を開始",
        })

        # Stage 2: Document review
        review = _reverse_business_days(base, SCHEDULE_REVERSE_REVIEW_BD)
        stages.append({
            "stage": "書類レビュー",
            "date": review.isoformat(),
            "offset_bd": SCHEDULE_REVERSE_REVIEW_BD,
            "description": "作成書類の最終レビュー",
        })

        # Stage 3: Final check
        finalize = _reverse_business_days(base, SCHEDULE_REVERSE_FINALIZE_BD)
        stages.append({
            "stage": "最終確認",
            "date": finalize.isoformat(),
            "offset_bd": SCHEDULE_REVERSE_FINALIZE_BD,
            "description": "封入・発送準備の最終確認",
        })

        # Stage 4: Submission deadline
        stages.append({
            "stage": "提出期限",
            "date": base.isoformat(),
            "offset_bd": 0,
            "description": "入札書提出締切",
        })

        # Optional: Quote deadline
        if quote_deadline:
            try:
                qd = datetime.fromisoformat(quote_deadline).date()
                q_prep = _reverse_business_days(qd, -2)
                stages.insert(0, {
                    "stage": "見積書準備",
                    "date": q_prep.isoformat(),
                    "offset_bd": -2,
                    "description": "下見積もり書の作成・提出",
                    "reference_deadline": qd.isoformat(),
                })
            except (ValueError, TypeError):
                logger.warning("invalid_quote_deadline", raw=quote_deadline)

        return stages
