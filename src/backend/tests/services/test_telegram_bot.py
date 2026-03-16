"""Tests for Telegram bot client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram.error import TelegramError

from app.services.notifications.telegram_bot import (
    TelegramBotClient,
    validate_bot_credentials,
)


class TestTelegramBotClient:
    """Test TelegramBotClient initialization and methods."""

    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            client = TelegramBotClient("test_token_123", "987654321")
            assert client.bot_token == "test_token_123"
            assert client.chat_id == "987654321"
            mock_bot_class.assert_called_once_with(token="test_token_123")

    def test_init_with_empty_token(self):
        """Test initialization fails with empty token."""
        with pytest.raises(ValueError, match="bot_token and chat_id must be provided"):
            TelegramBotClient("", "987654321")

    def test_init_with_empty_chat_id(self):
        """Test initialization fails with empty chat_id."""
        with pytest.raises(ValueError, match="bot_token and chat_id must be provided"):
            TelegramBotClient("test_token", "")

    def test_init_with_none_token(self):
        """Test initialization fails with None token."""
        with pytest.raises(ValueError):
            TelegramBotClient(None, "987654321")

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message send."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=123))
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            result = await client.send_message("Test message")

            assert result is True
            mock_bot.send_message.assert_called_once_with(
                chat_id="chat_id",
                text="Test message",
                parse_mode="HTML",
            )

    @pytest.mark.asyncio
    async def test_send_message_with_markdown(self):
        """Test sending message with Markdown parse mode."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=123))
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            result = await client.send_message("**Bold text**", parse_mode="Markdown")

            assert result is True
            mock_bot.send_message.assert_called_once_with(
                chat_id="chat_id",
                text="**Bold text**",
                parse_mode="Markdown",
            )

    @pytest.mark.asyncio
    async def test_send_empty_message(self):
        """Test that empty message is not sent."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            result = await client.send_message("")

            assert result is False
            mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_telegram_error(self):
        """Test handling of Telegram API errors."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_message.side_effect = TelegramError("Invalid chat_id")
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "invalid_chat_id")
            result = await client.send_message("Test message")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_unexpected_error(self):
        """Test handling of unexpected errors."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_message.side_effect = RuntimeError("Unexpected error")
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            result = await client.send_message("Test message")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_photo_success(self):
        """Test successful photo send."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_photo = AsyncMock(return_value=MagicMock(message_id=124))
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            result = await client.send_photo(
                "https://example.com/photo.jpg",
                caption="Test caption",
            )

            assert result is True
            mock_bot.send_photo.assert_called_once_with(
                chat_id="chat_id",
                photo="https://example.com/photo.jpg",
                caption="Test caption",
                parse_mode="HTML",
            )

    @pytest.mark.asyncio
    async def test_send_photo_telegram_error(self):
        """Test handling of Telegram API errors on photo send."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_photo.side_effect = TelegramError("Invalid photo URL")
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            result = await client.send_photo("invalid_url")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_document_success(self):
        """Test successful document send."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_document = AsyncMock(return_value=MagicMock(message_id=125))
            mock_bot_class.return_value = mock_bot

            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file

                client = TelegramBotClient("token", "chat_id")
                result = await client.send_document(
                    "/path/to/document.pdf",
                    caption="Document",
                )

                assert result is True
                mock_bot.send_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_document_file_not_found(self):
        """Test handling of missing document file."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            with patch("builtins.open", side_effect=FileNotFoundError()):
                client = TelegramBotClient("token", "chat_id")
                result = await client.send_document("/nonexistent/file.pdf")

                assert result is False

    @pytest.mark.asyncio
    async def test_send_document_telegram_error(self):
        """Test handling of Telegram API errors on document send."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_document.side_effect = TelegramError("Document too large")
            mock_bot_class.return_value = mock_bot

            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file

                client = TelegramBotClient("token", "chat_id")
                result = await client.send_document("/path/to/file.pdf")

                assert result is False

    @pytest.mark.asyncio
    async def test_close_success(self):
        """Test closing bot session."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_session = AsyncMock()
            mock_bot.session = mock_session
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            await client.close()

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_error_handling(self):
        """Test handling of errors during close."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_session = AsyncMock()
            mock_session.close.side_effect = RuntimeError("Close error")
            mock_bot.session = mock_session
            mock_bot_class.return_value = mock_bot

            client = TelegramBotClient("token", "chat_id")
            await client.close()  # Should not raise


class TestValidateBotCredentials:
    """Test bot credential validation."""

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self):
        """Test successful credential validation."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_user = MagicMock()
            mock_user.username = "test_bot"
            mock_bot.get_me.return_value = mock_user
            mock_session = AsyncMock()
            mock_bot.session = mock_session
            mock_bot_class.return_value = mock_bot

            result = await validate_bot_credentials("token_123", "chat_id")

            assert result is True
            mock_bot.get_me.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid_token(self):
        """Test credential validation with invalid token."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.side_effect = TelegramError("Unauthorized")
            mock_session = AsyncMock()
            mock_bot.session = mock_session
            mock_bot_class.return_value = mock_bot

            result = await validate_bot_credentials("invalid_token", "chat_id")

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_credentials_unexpected_error(self):
        """Test credential validation with unexpected error."""
        with patch("app.services.notifications.telegram_bot.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.side_effect = RuntimeError("Network error")
            mock_session = AsyncMock()
            mock_bot.session = mock_session
            mock_bot_class.return_value = mock_bot

            result = await validate_bot_credentials("token", "chat_id")

            assert result is False
