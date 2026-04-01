"""Tests for notification hooks integration."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.case import Case
from app.services.notifications.notification_hooks import (
    check_deadline_warning,
    notify_on_case_scored,
    notify_on_deadline_check,
    notify_on_lifecycle_transition,
)
from app.services.notifications.notification_service import NotificationService


class TestNotificationHooks:
    """Test notification hook functions."""

    @pytest.fixture
    def mock_notification_service(self):
        """Create mock notification service."""
        service = AsyncMock(spec=NotificationService)
        service.notify_high_score_case = AsyncMock(return_value=True)
        service.notify_deadline_warning = AsyncMock(return_value=True)
        service.notify_case_alert = AsyncMock(return_value=True)
        return service

    @pytest.fixture
    def sample_case(self):
        """Create a sample case."""
        case = MagicMock(spec=Case)
        case.id = "test-case-id"
        case.case_name = "テスト案件"
        case.score = 75
        case.submission_deadline = datetime.now(UTC) + timedelta(days=5)
        case.current_lifecycle_stage = "discovered"
        return case

    @pytest.mark.asyncio
    async def test_notify_on_case_scored_with_score(
        self, sample_case, mock_notification_service
    ):
        """Test notification triggered when case is scored."""
        await notify_on_case_scored(sample_case, mock_notification_service)
        mock_notification_service.notify_high_score_case.assert_called_once_with(
            sample_case
        )

    @pytest.mark.asyncio
    async def test_notify_on_case_scored_without_score(
        self, sample_case, mock_notification_service
    ):
        """Test no notification when case has no score."""
        sample_case.score = None
        await notify_on_case_scored(sample_case, mock_notification_service)
        mock_notification_service.notify_high_score_case.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_on_case_scored_error_handling(
        self, sample_case, mock_notification_service
    ):
        """Test error handling in case scoring notification."""
        mock_notification_service.notify_high_score_case.side_effect = Exception(
            "API error"
        )
        # Should not raise
        await notify_on_case_scored(sample_case, mock_notification_service)

    @pytest.mark.asyncio
    async def test_notify_on_lifecycle_transition_important(
        self, sample_case, mock_notification_service
    ):
        """Test notification for important lifecycle transition."""
        await notify_on_lifecycle_transition(
            sample_case,
            from_stage="discovered",
            to_stage="scored",
            notification_service=mock_notification_service,
        )
        mock_notification_service.notify_case_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_on_lifecycle_transition_unimportant(
        self, sample_case, mock_notification_service
    ):
        """Test no notification for unimportant transitions."""
        await notify_on_lifecycle_transition(
            sample_case,
            from_stage="discovered",
            to_stage="under_review",
            notification_service=mock_notification_service,
        )
        mock_notification_service.notify_case_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_on_lifecycle_transition_reading(
        self, sample_case, mock_notification_service
    ):
        """Test notification for reading lifecycle transition."""
        await notify_on_lifecycle_transition(
            sample_case,
            from_stage="reading_queued",
            to_stage="reading_in_progress",
            notification_service=mock_notification_service,
        )
        mock_notification_service.notify_case_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_on_lifecycle_transition_error_handling(
        self, sample_case, mock_notification_service
    ):
        """Test error handling in lifecycle transition notification."""
        mock_notification_service.notify_case_alert.side_effect = Exception(
            "API error"
        )
        # Should not raise
        await notify_on_lifecycle_transition(
            sample_case,
            from_stage="discovered",
            to_stage="scored",
            notification_service=mock_notification_service,
        )

    def test_check_deadline_warning_within_window(self, sample_case):
        """Test deadline warning check within notification window."""
        sample_case.submission_deadline = datetime.now(UTC) + timedelta(days=5, hours=12)
        days_left = check_deadline_warning(sample_case)
        assert days_left == 5

    def test_check_deadline_warning_urgent(self, sample_case):
        """Test deadline warning check for urgent deadline."""
        sample_case.submission_deadline = datetime.now(UTC) + timedelta(days=1, hours=12)
        days_left = check_deadline_warning(sample_case)
        assert days_left == 1

    def test_check_deadline_warning_today(self, sample_case):
        """Test deadline warning check for today deadline."""
        sample_case.submission_deadline = datetime.now(UTC) + timedelta(hours=1)
        days_left = check_deadline_warning(sample_case)
        assert days_left == 0

    def test_check_deadline_warning_outside_window_future(self, sample_case):
        """Test no warning for deadline beyond 7 days."""
        sample_case.submission_deadline = datetime.now(UTC) + timedelta(days=10)
        days_left = check_deadline_warning(sample_case)
        assert days_left is None

    def test_check_deadline_warning_outside_window_past(self, sample_case):
        """Test no warning for past deadline."""
        sample_case.submission_deadline = datetime.now(UTC) - timedelta(days=1)
        days_left = check_deadline_warning(sample_case)
        assert days_left is None

    def test_check_deadline_warning_no_deadline(self, sample_case):
        """Test no warning when deadline is not set."""
        sample_case.submission_deadline = None
        days_left = check_deadline_warning(sample_case)
        assert days_left is None

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_notify_on_deadline_check_success(
        self, sample_case, mock_notification_service
    ):
        """Test successful deadline warning notification."""
        sample_case.submission_deadline = datetime.now(UTC) + timedelta(days=3, hours=12)
        await notify_on_deadline_check(sample_case, mock_notification_service)
        mock_notification_service.notify_deadline_warning.assert_called_once_with(
            sample_case, 3
        )

    @pytest.mark.asyncio
    async def test_notify_on_deadline_check_outside_window(
        self, sample_case, mock_notification_service
    ):
        """Test no notification outside warning window."""
        sample_case.submission_deadline = datetime.now(UTC) + timedelta(days=10)
        await notify_on_deadline_check(sample_case, mock_notification_service)
        mock_notification_service.notify_deadline_warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_on_deadline_check_error_handling(
        self, sample_case, mock_notification_service
    ):
        """Test error handling in deadline check."""
        sample_case.submission_deadline = datetime.now(UTC) + timedelta(days=3)
        mock_notification_service.notify_deadline_warning.side_effect = Exception(
            "API error"
        )
        # Should not raise
        await notify_on_deadline_check(sample_case, mock_notification_service)
