"""Slack bot client for sending notifications."""

import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = structlog.get_logger()


class SlackBotClient:
    """Client for sending messages via Slack bot."""

    def __init__(self, bot_token: str, channel_id: str):
        """Initialize Slack bot client.

        Args:
            bot_token: Slack bot token from Slack App
            channel_id: Target channel ID for notifications

        Raises:
            ValueError: If bot_token or channel_id is empty
        """
        if not bot_token or not channel_id:
            raise ValueError("bot_token and channel_id must be provided")

        self.bot_token = bot_token
        self.channel_id = channel_id
        self.client = WebClient(token=bot_token)
        logger.info("slack_bot_initialized", channel_id=channel_id)

    def send_message(self, message: str) -> bool:
        """Send a message to the configured channel.

        Args:
            message: Message text (plain text)

        Returns:
            True if message sent successfully, False otherwise
        """
        if not message or not message.strip():
            logger.warning("empty_message_not_sent")
            return False

        try:
            self.client.chat_postMessage(
                channel=self.channel_id,
                text=message,
            )
            logger.debug("message_sent", channel_id=self.channel_id, length=len(message))
            return True

        except SlackApiError as e:
            logger.error(
                "slack_send_failed",
                channel_id=self.channel_id,
                error=str(e),
                error_code=getattr(e.response, "status_code", None),
            )
            return False

        except Exception as e:
            logger.error(
                "slack_send_unexpected_error",
                channel_id=self.channel_id,
                error=str(e),
            )
            return False

    def send_blocks(self, blocks: list[dict]) -> bool:
        """Send a formatted message with Slack Block Kit to the configured channel.

        Args:
            blocks: List of Slack Block Kit blocks

        Returns:
            True if message sent successfully, False otherwise
        """
        if not blocks:
            logger.warning("empty_blocks_not_sent")
            return False

        try:
            self.client.chat_postMessage(
                channel=self.channel_id,
                blocks=blocks,
            )
            logger.debug("blocks_sent", channel_id=self.channel_id, block_count=len(blocks))
            return True

        except SlackApiError as e:
            logger.error(
                "slack_send_blocks_failed",
                channel_id=self.channel_id,
                error=str(e),
            )
            return False

        except Exception as e:
            logger.error(
                "slack_send_blocks_error",
                channel_id=self.channel_id,
                error=str(e),
            )
            return False

    def send_file(
        self,
        file_path: str,
        title: str = "",
        initial_comment: str = "",
    ) -> bool:
        """Send a file to the configured channel.

        Args:
            file_path: Local file path to upload
            title: Title for the file
            initial_comment: Initial message for the file

        Returns:
            True if file sent successfully, False otherwise
        """
        try:
            with open(file_path, "rb") as f:
                self.client.files_upload_v2(
                    channel=self.channel_id,
                    file=f,
                    title=title,
                    initial_comment=initial_comment,
                )
            logger.debug("file_sent", channel_id=self.channel_id, path=file_path)
            return True

        except FileNotFoundError:
            logger.error("file_not_found", path=file_path)
            return False

        except SlackApiError as e:
            logger.error(
                "slack_send_file_failed",
                channel_id=self.channel_id,
                error=str(e),
            )
            return False

        except Exception as e:
            logger.error(
                "slack_send_file_error",
                channel_id=self.channel_id,
                error=str(e),
            )
            return False

    def close(self) -> None:
        """Close bot session and cleanup resources."""
        try:
            # Slack SDK doesn't require explicit closing for synchronous client
            logger.info("slack_bot_closed")
        except Exception as e:
            logger.error("slack_bot_close_error", error=str(e))


def validate_bot_credentials(bot_token: str, channel_id: str) -> bool:
    """Validate Slack bot credentials by fetching bot info.

    Args:
        bot_token: Slack bot token
        channel_id: Target channel ID

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        client = WebClient(token=bot_token)
        response = client.auth_test()
        logger.info("bot_validated", bot_id=response["user_id"], team_id=response["team_id"])
        return True

    except SlackApiError as e:
        logger.error("bot_validation_failed", error=str(e))
        return False

    except Exception as e:
        logger.error("bot_validation_error", error=str(e))
        return False
