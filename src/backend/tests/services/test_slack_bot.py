"""Tests for Slack bot client."""

from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from app.services.notifications.slack_bot import SlackBotClient, validate_bot_credentials


class TestSlackBotClient:
    """Test SlackBotClient initialization and message sending."""

    def test_init_valid_credentials(self):
        """Test initialization with valid credentials."""
        with patch("app.services.notifications.slack_bot.WebClient"):
            client = SlackBotClient("test-token", "C123456")
            assert client.bot_token == "test-token"
            assert client.channel_id == "C123456"

    def test_init_missing_token(self):
        """Test initialization fails without bot token."""
        with pytest.raises(ValueError):
            SlackBotClient("", "C123456")

    def test_init_missing_channel(self):
        """Test initialization fails without channel ID."""
        with pytest.raises(ValueError):
            SlackBotClient("test-token", "")

    def test_send_message_success(self):
        """Test successful message send."""
        with patch("app.services.notifications.slack_bot.WebClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = SlackBotClient("test-token", "C123456")
            result = client.send_message("Test message")

            assert result is True
            mock_instance.chat_postMessage.assert_called_once_with(
                channel="C123456",
                text="Test message",
            )

    def test_send_message_empty(self):
        """Test sending empty message is ignored."""
        with patch("app.services.notifications.slack_bot.WebClient"):
            client = SlackBotClient("test-token", "C123456")
            result = client.send_message("")

            assert result is False

    def test_send_message_slack_error(self):
        """Test handling of Slack API errors."""
        with patch("app.services.notifications.slack_bot.WebClient") as mock_client:
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            error = SlackApiError("Unauthorized", response=mock_response)
            mock_instance.chat_postMessage.side_effect = error
            mock_client.return_value = mock_instance

            client = SlackBotClient("test-token", "C123456")
            result = client.send_message("Test message")

            assert result is False

    def test_send_blocks_success(self):
        """Test successful blocks send."""
        with patch("app.services.notifications.slack_bot.WebClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = SlackBotClient("test-token", "C123456")
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
            result = client.send_blocks(blocks)

            assert result is True
            mock_instance.chat_postMessage.assert_called_once_with(
                channel="C123456",
                blocks=blocks,
            )

    def test_send_blocks_empty(self):
        """Test sending empty blocks is ignored."""
        with patch("app.services.notifications.slack_bot.WebClient"):
            client = SlackBotClient("test-token", "C123456")
            result = client.send_blocks([])

            assert result is False

    def test_close(self):
        """Test closing bot session."""
        with patch("app.services.notifications.slack_bot.WebClient"):
            client = SlackBotClient("test-token", "C123456")
            client.close()  # Should not raise


class TestValidateBotCredentials:
    """Test bot credential validation."""

    def test_validate_success(self):
        """Test successful validation."""
        with patch("app.services.notifications.slack_bot.WebClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.auth_test.return_value = {
                "user_id": "U123456",
                "team_id": "T123456",
            }
            mock_client.return_value = mock_instance

            result = validate_bot_credentials("test-token", "C123456")

            assert result is True

    def test_validate_fail(self):
        """Test failed validation with invalid token."""
        with patch("app.services.notifications.slack_bot.WebClient") as mock_client:
            mock_instance = MagicMock()
            mock_response = MagicMock()
            error = SlackApiError("Invalid token", response=mock_response)
            mock_instance.auth_test.side_effect = error
            mock_client.return_value = mock_instance

            result = validate_bot_credentials("invalid-token", "C123456")

            assert result is False
