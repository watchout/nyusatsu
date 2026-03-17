"""Telegram Bot integration for sending notifications."""

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class TelegramBotClient:
    """Telegram Bot API client for sending messages."""

    def __init__(self, bot_token: str, chat_id: str | int):
        """Initialize Telegram bot client.

        Args:
            bot_token: Telegram bot token (from BotFather)
            chat_id: Target chat/channel ID for notifications
        """
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.api_base_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
    ) -> dict[str, Any]:
        """Send a message to the configured chat.

        Args:
            text: Message content (supports HTML formatting)
            parse_mode: "HTML" or "Markdown"
            disable_web_page_preview: Disable link previews

        Returns:
            API response dict

        Raises:
            httpx.RequestError: Network error
            ValueError: Invalid response from Telegram API
        """
        url = f"{self.api_base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                error_msg = data.get("description", "Unknown error")
                logger.error(
                    "telegram_send_failed",
                    error=error_msg,
                    response=data,
                )
                raise ValueError(f"Telegram API error: {error_msg}")

            logger.info(
                "telegram_message_sent",
                chat_id=self.chat_id,
                message_id=data.get("result", {}).get("message_id"),
            )
            return data.get("result", {})

        except httpx.RequestError as e:
            logger.error(
                "telegram_request_error",
                error=str(e),
                chat_id=self.chat_id,
            )
            raise

    async def close(self) -> None:
        """Close the async HTTP client."""
        await self.client.aclose()

    def __del__(self) -> None:
        """Cleanup on deletion."""
        try:
            # Only attempt sync close if event loop is still running
            import asyncio

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return

            # If we get here, try to schedule async close
            asyncio.create_task(self.close())
        except Exception:
            pass
