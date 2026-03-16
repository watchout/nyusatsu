"""Telegram bot client for sending notifications."""

import structlog
from telegram import Bot
from telegram.error import TelegramError

logger = structlog.get_logger()


class TelegramBotClient:
    """Client for sending messages via Telegram bot."""

    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram bot client.

        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Target chat ID for notifications

        Raises:
            ValueError: If bot_token or chat_id is empty
        """
        if not bot_token or not chat_id:
            raise ValueError("bot_token and chat_id must be provided")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        logger.info("telegram_bot_initialized", chat_id=chat_id)

    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured chat.

        Args:
            message: Message text (supports HTML formatting)
            parse_mode: Parse mode for message formatting (HTML or Markdown)

        Returns:
            True if message sent successfully, False otherwise
        """
        if not message or not message.strip():
            logger.warning("empty_message_not_sent")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
            )
            logger.debug("message_sent", chat_id=self.chat_id, length=len(message))
            return True

        except TelegramError as e:
            logger.error(
                "telegram_send_failed",
                chat_id=self.chat_id,
                error=str(e),
                error_code=getattr(e, "status_code", None),
            )
            return False

        except Exception as e:
            logger.error(
                "telegram_send_unexpected_error",
                chat_id=self.chat_id,
                error=str(e),
            )
            return False

    async def send_photo(
        self,
        photo_url: str,
        caption: str = "",
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a photo to the configured chat.

        Args:
            photo_url: URL or file path of photo
            caption: Optional caption (supports HTML formatting)
            parse_mode: Parse mode for caption formatting

        Returns:
            True if photo sent successfully, False otherwise
        """
        try:
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo_url,
                caption=caption,
                parse_mode=parse_mode,
            )
            logger.debug("photo_sent", chat_id=self.chat_id)
            return True

        except TelegramError as e:
            logger.error(
                "telegram_send_photo_failed",
                chat_id=self.chat_id,
                error=str(e),
            )
            return False

        except Exception as e:
            logger.error(
                "telegram_send_photo_error",
                chat_id=self.chat_id,
                error=str(e),
            )
            return False

    async def send_document(
        self,
        document_path: str,
        caption: str = "",
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a document to the configured chat.

        Args:
            document_path: File path of document to send
            caption: Optional caption (supports HTML formatting)
            parse_mode: Parse mode for caption formatting

        Returns:
            True if document sent successfully, False otherwise
        """
        try:
            with open(document_path, "rb") as doc:
                await self.bot.send_document(
                    chat_id=self.chat_id,
                    document=doc,
                    caption=caption,
                    parse_mode=parse_mode,
                )
            logger.debug("document_sent", chat_id=self.chat_id, path=document_path)
            return True

        except FileNotFoundError:
            logger.error("document_not_found", path=document_path)
            return False

        except TelegramError as e:
            logger.error(
                "telegram_send_document_failed",
                chat_id=self.chat_id,
                error=str(e),
            )
            return False

        except Exception as e:
            logger.error(
                "telegram_send_document_error",
                chat_id=self.chat_id,
                error=str(e),
            )
            return False

    async def close(self) -> None:
        """Close bot session and cleanup resources."""
        try:
            await self.bot.session.close()
            logger.info("telegram_bot_closed")
        except Exception as e:
            logger.error("telegram_bot_close_error", error=str(e))


async def validate_bot_credentials(bot_token: str, chat_id: str) -> bool:
    """Validate Telegram bot credentials by fetching bot info.

    Args:
        bot_token: Telegram bot token
        chat_id: Target chat ID

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        bot = Bot(token=bot_token)
        bot_user = await bot.get_me()
        logger.info("bot_validated", bot_username=bot_user.username)
        await bot.session.close()
        return True

    except TelegramError as e:
        logger.error("bot_validation_failed", error=str(e))
        return False

    except Exception as e:
        logger.error("bot_validation_error", error=str(e))
        return False
