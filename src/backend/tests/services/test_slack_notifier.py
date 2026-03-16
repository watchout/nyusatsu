"""Tests for Slack notifier with Block Kit formatting."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.models.case import Case
from app.services.notifications.slack_notifier import SlackNotifier


@pytest.fixture
def mock_slack_bot():
    """Create a mock Slack bot."""
    return MagicMock()


@pytest.fixture
def sample_case():
    """Create a sample case for testing."""
    return Case(
        id="550e8400-e29b-41d4-a716-446655440000",
        case_name="テスト案件A",
        issuing_org="発注元A",
        score=75,
        category="建築工事",
        region="東京都",
        bid_type="一般競争入札",
        submission_deadline=datetime.now(UTC) + timedelta(days=5),
        current_lifecycle_stage="公開中",
        detail_url="https://example.com/case/1",
    )


class TestSlackNotifierFormatting:
    """Test Block Kit formatting methods."""

    def test_get_score_color_high(self):
        """Test color for high score."""
        color = SlackNotifier._get_score_color(75)
        assert color == "#FF6B6B"

    def test_get_score_color_medium(self):
        """Test color for medium score."""
        color = SlackNotifier._get_score_color(50)
        assert color == "#FFA94D"

    def test_get_score_color_low(self):
        """Test color for low score."""
        color = SlackNotifier._get_score_color(25)
        assert color == "#74B9FF"

    def test_get_score_emoji_high(self):
        """Test emoji for high score."""
        emoji = SlackNotifier._get_score_emoji(75)
        assert emoji == "🔥"

    def test_get_score_emoji_medium(self):
        """Test emoji for medium score."""
        emoji = SlackNotifier._get_score_emoji(50)
        assert emoji == "⚡"

    def test_format_case_alert_blocks(self, sample_case):
        """Test case alert block formatting."""
        blocks = SlackNotifier.format_case_alert_blocks(sample_case)

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        assert "📋" in blocks[0]["text"]["text"]

    def test_format_high_score_blocks(self, sample_case):
        """Test high-score notification block formatting."""
        blocks = SlackNotifier.format_high_score_blocks(sample_case)

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        assert "🔥" in blocks[0]["text"]["text"]

    def test_format_batch_summary_blocks(self):
        """Test batch summary block formatting."""
        blocks = SlackNotifier.format_batch_summary_blocks(
            new_cases=5,
            high_score_cases=2,
            deadline_warning_cases=1,
        )

        assert isinstance(blocks, list)
        assert blocks[0]["type"] == "header"
        assert "✨" in blocks[0]["text"]["text"]


@pytest.mark.asyncio
class TestSlackNotifierAsync:
    """Test async notification methods."""

    async def test_notify_high_score_case_success(self, sample_case, mock_slack_bot):
        """Test successful high-score notification."""
        mock_slack_bot.send_blocks.return_value = True
        notifier = SlackNotifier(slack_bot=mock_slack_bot, score_threshold=30)

        result = await notifier.notify_high_score_case(sample_case)

        assert result is True
        mock_slack_bot.send_blocks.assert_called_once()

    async def test_notify_high_score_case_no_bot(self, sample_case):
        """Test high-score notification without bot."""
        notifier = SlackNotifier(slack_bot=None)

        result = await notifier.notify_high_score_case(sample_case)

        assert result is False

    async def test_notify_deadline_warning_success(self, sample_case, mock_slack_bot):
        """Test successful deadline warning."""
        mock_slack_bot.send_blocks.return_value = True
        notifier = SlackNotifier(slack_bot=mock_slack_bot)

        result = await notifier.notify_deadline_warning(sample_case, days_left=3)

        assert result is True
        mock_slack_bot.send_blocks.assert_called_once()

    async def test_notify_batch_summary_success(self, mock_slack_bot):
        """Test successful batch summary notification."""
        mock_slack_bot.send_blocks.return_value = True
        notifier = SlackNotifier(slack_bot=mock_slack_bot)

        result = await notifier.notify_batch_summary(
            new_cases=5,
            high_score_cases=2,
            deadline_warning_cases=1,
        )

        assert result is True
        mock_slack_bot.send_blocks.assert_called_once()

    def test_close(self, mock_slack_bot):
        """Test closing notifier."""
        notifier = SlackNotifier(slack_bot=mock_slack_bot)
        notifier.close()

        mock_slack_bot.close.assert_called_once()
