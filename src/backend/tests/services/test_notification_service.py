"""Tests for notification services."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.notifications.telegram_bot import TelegramBotClient

from app.models.case import Case
from app.services.notifications.notification_service import (
    NotificationFormatter,
    NotificationService,
    get_notification_service,
)


class TestNotificationFormatter:
    """Test NotificationFormatter formatting methods."""

    def test_format_score_emoji_high(self):
        """Test emoji selection for high score."""
        emoji = NotificationFormatter.format_score_emoji(80)
        assert emoji == "🔥"

    def test_format_score_emoji_medium(self):
        """Test emoji selection for medium score."""
        emoji = NotificationFormatter.format_score_emoji(55)
        assert emoji == "⚡"

    def test_format_score_emoji_low(self):
        """Test emoji selection for low score."""
        emoji = NotificationFormatter.format_score_emoji(20)
        assert emoji == "⏰"

    def test_format_score_emoji_none(self):
        """Test emoji selection for None score."""
        emoji = NotificationFormatter.format_score_emoji(None)
        assert emoji == "🚨"

    def test_format_case_alert_basic(self):
        """Test basic case alert formatting."""
        case = MagicMock(spec=Case)
        case.case_name = "テスト案件"
        case.issuing_org = "テスト発注元"
        case.score = 50
        case.category = "建設工事"
        case.region = "東京都"
        case.bid_type = "一般競争入札"
        case.current_lifecycle_stage = "discovered"
        case.submission_deadline = datetime.now(UTC) + timedelta(days=5)
        case.detail_url = "https://example.com/case/1"

        message = NotificationFormatter.format_case_alert(case)
        assert "テスト案件" in message
        assert "テスト発注元" in message
        assert "50" in message
        assert "建設工事" in message
        assert "https://example.com/case/1" in message

    def test_format_case_alert_without_url(self):
        """Test case alert formatting without detail URL."""
        case = MagicMock(spec=Case)
        case.case_name = "案件A"
        case.issuing_org = "発注元A"
        case.score = 75
        case.category = None
        case.region = None
        case.bid_type = None
        case.current_lifecycle_stage = "scored"
        case.submission_deadline = None
        case.detail_url = None

        message = NotificationFormatter.format_case_alert(case)
        assert "案件A" in message
        assert "発注元A" in message
        assert "href=" not in message  # No link

    def test_format_high_score_notification(self):
        """Test high-score notification formatting."""
        case = MagicMock(spec=Case)
        case.case_name = "高スコア案件"
        case.issuing_org = "発注元B"
        case.score = 85
        case.category = "建築工事"
        case.submission_deadline = datetime.now(UTC) + timedelta(days=10)
        case.detail_url = "https://example.com/case/2"

        message = NotificationFormatter.format_high_score_notification(case)
        assert "高スコア案件発見" in message
        assert "高スコア案件" in message
        assert "85" in message
        assert "発注元B" in message

    def test_format_deadline_warning_urgent(self):
        """Test deadline warning formatting for urgent deadline."""
        case = MagicMock(spec=Case)
        case.case_name = "期限間近案件"
        case.issuing_org = "発注元C"
        case.score = 60
        case.submission_deadline = datetime.now(UTC) + timedelta(days=2)
        case.detail_url = "https://example.com/case/3"

        message = NotificationFormatter.format_deadline_warning(case, days_left=2)
        assert "🚨 緊急" in message
        assert "期限が近づいています" in message
        assert "2" in message

    def test_format_deadline_warning_caution(self):
        """Test deadline warning formatting for caution deadline."""
        case = MagicMock(spec=Case)
        case.case_name = "案件D"
        case.issuing_org = "発注元D"
        case.score = 45
        case.submission_deadline = datetime.now(UTC) + timedelta(days=5)
        case.detail_url = None

        message = NotificationFormatter.format_deadline_warning(case, days_left=5)
        assert "⚠️ 注意" in message
        assert "5" in message

    def test_format_batch_summary(self):
        """Test batch summary formatting."""
        message = NotificationFormatter.format_batch_summary(
            new_cases=10,
            high_score_cases=3,
            deadline_warning_cases=2,
        )
        assert "新規案件処理完了" in message
        assert "10" in message
        assert "3" in message
        assert "2" in message

    def test_score_description(self):
        """Test score description generation."""
        assert "非常に優先度が高い" in NotificationFormatter._score_description(90)
        assert "優先度が高い" in NotificationFormatter._score_description(70)
        assert "中程度" in NotificationFormatter._score_description(50)
        assert "低い" in NotificationFormatter._score_description(20)
        assert "未計算" in NotificationFormatter._score_description(None)


class TestNotificationService:
    """Test NotificationService methods."""

    @pytest.fixture
    def mock_telegram_bot(self):
        """Create mock Telegram bot."""
        bot = AsyncMock(spec=TelegramBotClient)
        bot.send_message = AsyncMock(return_value={"message_id": 123})
        return bot

    @pytest.fixture
    def notification_service(self, mock_telegram_bot):
        """Create notification service with mock bot."""
        return NotificationService(
            telegram_bot=mock_telegram_bot,
            score_threshold=30,
        )

    @pytest.fixture
    def sample_case(self):
        """Create a sample case for testing."""
        case = MagicMock(spec=Case)
        case.id = "test-case-id"
        case.case_name = "テスト案件"
        case.issuing_org = "テスト発注元"
        case.score = 75
        case.category = "建設工事"
        case.region = "東京都"
        case.bid_type = "一般競争入札"
        case.current_lifecycle_stage = "discovered"
        case.submission_deadline = datetime.now(UTC) + timedelta(days=5)
        case.detail_url = "https://example.com/case/1"
        return case

    @pytest.mark.asyncio
    async def test_notify_high_score_case_success(
        self, notification_service, sample_case
    ):
        """Test successful high-score notification."""
        result = await notification_service.notify_high_score_case(sample_case)
        assert result is True
        notification_service.telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_high_score_case_below_threshold(
        self, notification_service, sample_case
    ):
        """Test that low-score case doesn't trigger notification."""
        sample_case.score = 20
        result = await notification_service.notify_high_score_case(sample_case)
        assert result is False
        notification_service.telegram_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_high_score_case_no_score(
        self, notification_service, sample_case
    ):
        """Test that case without score doesn't trigger notification."""
        sample_case.score = None
        result = await notification_service.notify_high_score_case(sample_case)
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_high_score_case_telegram_error(
        self, notification_service, sample_case
    ):
        """Test handling of Telegram API errors."""
        notification_service.telegram_bot.send_message.side_effect = Exception(
            "API error"
        )
        result = await notification_service.notify_high_score_case(sample_case)
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_deadline_warning_success(
        self, notification_service, sample_case
    ):
        """Test successful deadline warning."""
        result = await notification_service.notify_deadline_warning(
            sample_case, days_left=5
        )
        assert result is True
        notification_service.telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_deadline_warning_outside_window(
        self, notification_service, sample_case
    ):
        """Test that deadline outside window doesn't trigger notification."""
        result = await notification_service.notify_deadline_warning(
            sample_case, days_left=10
        )
        assert result is False
        notification_service.telegram_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_deadline_warning_past_deadline(
        self, notification_service, sample_case
    ):
        """Test that past deadline doesn't trigger notification."""
        result = await notification_service.notify_deadline_warning(
            sample_case, days_left=-1
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_batch_summary_success(self, notification_service):
        """Test successful batch summary notification."""
        result = await notification_service.notify_batch_summary(
            new_cases=5,
            high_score_cases=2,
            deadline_warning_cases=1,
        )
        assert result is True
        notification_service.telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_case_alert_success(
        self, notification_service, sample_case
    ):
        """Test successful case alert."""
        result = await notification_service.notify_case_alert(
            sample_case,
            alert_type="lifecycle_change",
        )
        assert result is True
        notification_service.telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_case_alert_with_payload(
        self, notification_service, sample_case
    ):
        """Test case alert with additional payload."""
        result = await notification_service.notify_case_alert(
            sample_case,
            alert_type="status_update",
            payload={"message_suffix": "カスタムメッセージ"},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_notify_high_score_case_no_bot(self, sample_case):
        """Test notification with no Telegram bot configured."""
        service = NotificationService(telegram_bot=None)
        result = await service.notify_high_score_case(sample_case)
        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, notification_service):
        """Test closing the notification service."""
        await notification_service.close()
        notification_service.telegram_bot.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_bot(self):
        """Test closing service without bot."""
        service = NotificationService(telegram_bot=None)
        await service.close()  # Should not raise


class TestTelegramBotClient:
    """Test TelegramBotClient."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message send."""
        with patch("app.services.notifications.telegram_bot.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": True,
                "result": {"message_id": 123},
            }
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = TelegramBotClient("test_token", "test_chat_id")
            result = await client.send_message("Test message")

            assert result == {"message_id": 123}
            mock_client.post.assert_called_once()

            await client.close()

    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        """Test handling of Telegram API errors."""
        with patch("app.services.notifications.telegram_bot.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": False,
                "description": "Invalid chat_id",
            }
            mock_response.raise_for_status.side_effect = None
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = TelegramBotClient("test_token", "invalid_id")

            with pytest.raises(ValueError, match="Telegram API error"):
                await client.send_message("Test message")

            await client.close()

    @pytest.mark.asyncio
    async def test_send_message_network_error(self):
        """Test handling of network errors."""
        import httpx

        with patch("app.services.notifications.telegram_bot.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("Network error")
            mock_client_class.return_value = mock_client

            client = TelegramBotClient("test_token", "test_chat_id")

            with pytest.raises(httpx.RequestError):
                await client.send_message("Test message")

            await client.close()


class TestGetNotificationService:
    """Test get_notification_service factory function."""

    def test_get_notification_service_configured(self):
        """Test creating service with configured settings."""
        with patch("app.services.notifications.notification_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"
            mock_settings.TELEGRAM_CHAT_ID = "test_chat_id"

            with patch.object(
                NotificationService,
                "__init__",
                return_value=None,
            ) as _:
                service = get_notification_service()
                # Service should be created
                assert service is not None

    def test_get_notification_service_not_configured(self):
        """Test creating service without Telegram configuration."""
        with patch("app.services.notifications.notification_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = ""
            mock_settings.TELEGRAM_CHAT_ID = ""

            service = get_notification_service()
            assert service.telegram_bot is None
