"""Tests for ScheduleCalculator (F-004)."""

from datetime import date, datetime, timezone

from app.services.checklist_gen.schedule_calculator import (
    ScheduleCalculator,
    _is_business_day,
    _reverse_business_days,
)


class TestScheduleCalculator:
    def test_standard_reverse_4_stages(self) -> None:
        """Standard 4-stage reverse schedule."""
        calc = ScheduleCalculator()
        # 2026-03-16 is a Monday
        deadline = datetime(2026, 3, 16, 17, 0, tzinfo=timezone.utc)
        stages = calc.calculate(deadline)

        assert len(stages) == 4
        assert stages[0]["stage"] == "準備開始"
        assert stages[1]["stage"] == "書類レビュー"
        assert stages[2]["stage"] == "最終確認"
        assert stages[3]["stage"] == "提出期限"
        assert stages[3]["date"] == "2026-03-16"

    def test_with_quote_deadline(self) -> None:
        """Quote deadline adds a 5th stage at the beginning."""
        calc = ScheduleCalculator()
        deadline = datetime(2026, 3, 16, 17, 0, tzinfo=timezone.utc)
        stages = calc.calculate(
            deadline, quote_deadline="2026-03-10T17:00:00+09:00",
        )

        assert len(stages) == 5
        assert stages[0]["stage"] == "見積書準備"

    def test_null_deadline(self) -> None:
        """Null deadline returns empty schedule."""
        calc = ScheduleCalculator()
        stages = calc.calculate(None)
        assert stages == []

    def test_past_deadline(self) -> None:
        """Past deadline still computes (for display purposes)."""
        calc = ScheduleCalculator()
        deadline = date(2020, 1, 6)  # Monday
        stages = calc.calculate(deadline)
        assert len(stages) == 4

    def test_holiday_crossing(self) -> None:
        """Schedule respects Japanese holidays."""
        calc = ScheduleCalculator()
        # 2026-01-05 is a Monday, and 2026-01-01 is 元日
        deadline = date(2026, 1, 5)
        stages = calc.calculate(deadline)

        # -1BD from 2026-01-05 (Mon) should be 2025-12-26 (Fri),
        # because 2025-12-31~2026-01-04 includes holidays and weekends
        finalize = next(s for s in stages if s["stage"] == "最終確認")
        finalize_date = date.fromisoformat(finalize["date"])
        assert _is_business_day(finalize_date)
        # Verify it's before the deadline
        assert finalize_date < deadline

    def test_business_day_calculation(self) -> None:
        """_is_business_day correctly identifies weekdays and holidays."""
        # Saturday
        assert _is_business_day(date(2026, 3, 14)) is False
        # Sunday
        assert _is_business_day(date(2026, 3, 15)) is False
        # Monday
        assert _is_business_day(date(2026, 3, 16)) is True
        # 元日 (New Year)
        assert _is_business_day(date(2026, 1, 1)) is False

    def test_weekend_skip(self) -> None:
        """Reverse business days skip weekends."""
        # 2026-03-16 Monday, -5BD should skip the previous weekend
        result = _reverse_business_days(date(2026, 3, 16), -5)
        assert result == date(2026, 3, 9)  # Previous Monday
        assert _is_business_day(result)
