"""Notification service for case alerts and updates."""

from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.config import settings
from app.models.case import Case
from app.services.notifications.slack_bot import SlackBotClient
from app.services.notifications.slack_notifier import SlackNotifier
from app.services.notifications.telegram_bot import TelegramBotClient

logger = structlog.get_logger()

# Default score threshold for notifications (30 points)
DEFAULT_SCORE_THRESHOLD = 30

# Emoji mapping for case statuses and scores
EMOJI_MAP = {
    "high_score": "🔥",  # 70+
    "medium_score": "⚡",  # 40-69
    "low_score": "⏰",  # < 40
    "alert": "🚨",  # Alert
    "new": "✨",  # New case
    "deadline": "⏰",  # Deadline approaching
    "success": "✅",
}


class NotificationFormatter:
    """Format case information for notification messages."""

    @staticmethod
    def format_score_emoji(score: int | None) -> str:
        """Get emoji based on score level."""
        if score is None:
            return EMOJI_MAP["alert"]
        if score >= 70:
            return EMOJI_MAP["high_score"]
        if score >= 40:
            return EMOJI_MAP["medium_score"]
        return EMOJI_MAP["low_score"]

    @staticmethod
    def format_case_alert(case: Case, threshold_exceeded: bool = False) -> str:
        """Format case as an alert message.

        Args:
            case: Case to format
            threshold_exceeded: Whether the case exceeded score threshold

        Returns:
            Formatted HTML message
        """
        emoji = EMOJI_MAP["alert"] if threshold_exceeded else "📋"
        score_emoji = NotificationFormatter.format_score_emoji(case.score)

        deadline_str = "未定"
        days_left = "不明"
        if case.submission_deadline:
            deadline_str = case.submission_deadline.strftime("%Y年%m月%d日 %H:%M")
            days_left = str((case.submission_deadline - datetime.now(UTC)).days)
            if int(days_left) < 0:
                days_left = "期限切れ"

        message = f"""<b>{emoji} 案件アラート {score_emoji}</b>

<b>案件名:</b> {case.case_name}

<b>発注元:</b> {case.issuing_org}
<b>スコア:</b> {case.score or 'N/A'}/100
<b>期限:</b> {deadline_str}
<b>残余:</b> {days_left}日

<b>カテゴリ:</b> {case.category or '未分類'}
<b>地域:</b> {case.region or '全国'}
<b>入札種類:</b> {case.bid_type or '一般'}

<b>状態:</b> {case.current_lifecycle_stage}
"""

        if case.detail_url:
            message += f"\n<a href=\"{case.detail_url}\">詳細を見る</a>"

        return message

    @staticmethod
    def format_high_score_notification(case: Case) -> str:
        """Format notification for high-score case discovery."""
        message = f"""<b>{EMOJI_MAP['high_score']} 高スコア案件発見！</b>

<b>案件名:</b> <code>{case.case_name}</code>

<b>スコア:</b> <b>{case.score}/100</b> ({NotificationFormatter._score_description(case.score)})
<b>発注元:</b> {case.issuing_org}

<b>期限:</b> {case.submission_deadline.strftime('%Y年%m月%d日') if case.submission_deadline else '未定'}
<b>カテゴリ:</b> {case.category or '未分類'}

即対応を推奨します！
"""
        if case.detail_url:
            message += f"\n<a href=\"{case.detail_url}\">案件詳細を確認</a>"

        return message

    @staticmethod
    def format_deadline_warning(case: Case, days_left: int) -> str:
        """Format notification for approaching deadline."""
        urgency = "🚨 緊急" if days_left <= 3 else "⚠️ 注意"

        message = f"""<b>{urgency} 期限が近づいています</b>

<b>案件:</b> <code>{case.case_name}</code>

<b>残り日数:</b> <b>{days_left}日</b>
<b>期限:</b> {case.submission_deadline.strftime('%Y年%m月%d日 %H:%M') if case.submission_deadline else 'N/A'}

<b>発注元:</b> {case.issuing_org}
<b>スコア:</b> {case.score}/100

急いで対応してください！
"""
        if case.detail_url:
            message += f"\n<a href=\"{case.detail_url}\">案件を開く</a>"

        return message

    @staticmethod
    def format_batch_summary(
        new_cases: int,
        high_score_cases: int,
        deadline_warning_cases: int,
    ) -> str:
        """Format batch processing summary."""
        return f"""<b>{EMOJI_MAP['new']} 新規案件処理完了</b>

📊 <b>処理サマリ:</b>
• 新規案件: <b>{new_cases}</b>件
• 高スコア案件: <b>{high_score_cases}</b>件
• 期限間近案件: <b>{deadline_warning_cases}</b>件

詳細はダッシュボードをご確認ください。
"""

    @staticmethod
    def _score_description(score: int | None) -> str:
        """Get human description of score."""
        if score is None:
            return "スコア未計算"
        if score >= 80:
            return "非常に優先度が高い"
        if score >= 60:
            return "優先度が高い"
        if score >= 40:
            return "中程度"
        return "低い"


class NotificationService:
    """Service for managing case notifications and alerts."""

    def __init__(
        self,
        telegram_bot: TelegramBotClient | None = None,
        slack_bot: SlackBotClient | None = None,
        score_threshold: int = DEFAULT_SCORE_THRESHOLD,
    ):
        """Initialize notification service.

        Args:
            telegram_bot: TelegramBotClient instance (can be None for testing)
            slack_bot: SlackBotClient instance (can be None for testing)
            score_threshold: Score threshold for high-priority notifications (0-100)
        """
        self.telegram_bot = telegram_bot
        self.slack_bot = slack_bot
        self.slack_notifier = SlackNotifier(slack_bot=slack_bot, score_threshold=score_threshold)
        self.score_threshold = max(0, min(100, score_threshold))
        self.formatter = NotificationFormatter()

    async def notify_high_score_case(self, case: Case) -> bool:
        """Send notification for a high-score case.

        Args:
            case: Case with high score

        Returns:
            True if notification sent successfully
        """
        if case.score is None:
            return False

        if case.score < self.score_threshold:
            logger.debug(
                "case_below_threshold",
                case_id=str(case.id),
                score=case.score,
                threshold=self.score_threshold,
            )
            return False

        results = []

        # Send via Telegram if available
        if self.telegram_bot:
            try:
                message = self.formatter.format_high_score_notification(case)
                result = await self.telegram_bot.send_message(message)
                results.append(result)
            except Exception as e:
                logger.error(
                    "telegram_high_score_notification_failed",
                    case_id=str(case.id),
                    error=str(e),
                )

        # Send via Slack if available
        if self.slack_bot:
            try:
                result = await self.slack_notifier.notify_high_score_case(case)
                results.append(result)
            except Exception as e:
                logger.error(
                    "slack_high_score_notification_failed",
                    case_id=str(case.id),
                    error=str(e),
                )

        if results:
            logger.info(
                "high_score_notification_sent",
                case_id=str(case.id),
                score=case.score,
                channels=len(results),
            )
            return any(results)
        return False

    async def notify_deadline_warning(self, case: Case, days_left: int) -> bool:
        """Send notification for approaching deadline.

        Args:
            case: Case with approaching deadline
            days_left: Days remaining until deadline

        Returns:
            True if notification sent successfully
        """
        # Only notify if deadline is within 7 days
        if days_left > 7 or days_left < 0:
            return False

        results = []

        # Send via Telegram if available
        if self.telegram_bot:
            try:
                message = self.formatter.format_deadline_warning(case, days_left)
                result = await self.telegram_bot.send_message(message)
                results.append(result)
            except Exception as e:
                logger.error(
                    "telegram_deadline_warning_failed",
                    case_id=str(case.id),
                    error=str(e),
                )

        # Send via Slack if available
        if self.slack_bot:
            try:
                result = await self.slack_notifier.notify_deadline_warning(case, days_left)
                results.append(result)
            except Exception as e:
                logger.error(
                    "slack_deadline_warning_failed",
                    case_id=str(case.id),
                    error=str(e),
                )

        if results:
            logger.info(
                "deadline_warning_sent",
                case_id=str(case.id),
                days_left=days_left,
                channels=len(results),
            )
            return any(results)
        return False

    async def notify_batch_summary(
        self,
        new_cases: int,
        high_score_cases: int,
        deadline_warning_cases: int,
    ) -> bool:
        """Send batch processing summary notification.

        Args:
            new_cases: Count of new cases discovered
            high_score_cases: Count of high-score cases
            deadline_warning_cases: Count of deadline warning cases

        Returns:
            True if notification sent successfully
        """
        results = []

        # Send via Telegram if available
        if self.telegram_bot:
            try:
                message = self.formatter.format_batch_summary(
                    new_cases,
                    high_score_cases,
                    deadline_warning_cases,
                )
                result = await self.telegram_bot.send_message(message)
                results.append(result)
            except Exception as e:
                logger.error(
                    "telegram_batch_summary_failed",
                    error=str(e),
                )

        # Send via Slack if available
        if self.slack_bot:
            try:
                result = await self.slack_notifier.notify_batch_summary(
                    new_cases,
                    high_score_cases,
                    deadline_warning_cases,
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "slack_batch_summary_failed",
                    error=str(e),
                )

        if results:
            logger.info(
                "batch_summary_sent",
                new_cases=new_cases,
                high_score_cases=high_score_cases,
                deadline_warning_cases=deadline_warning_cases,
                channels=len(results),
            )
            return any(results)
        return False

    async def notify_case_alert(
        self,
        case: Case,
        alert_type: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Send a custom case alert.

        Args:
            case: Case to alert about
            alert_type: Type of alert (e.g., 'lifecycle_change', 'status_update')
            payload: Additional context

        Returns:
            True if notification sent successfully
        """
        results = []

        # Send via Telegram if available
        if self.telegram_bot:
            try:
                message = self.formatter.format_case_alert(case, threshold_exceeded=True)
                if payload and "message_suffix" in payload:
                    message += f"\n\n<i>{payload['message_suffix']}</i>"

                result = await self.telegram_bot.send_message(message)
                results.append(result)
            except Exception as e:
                logger.error(
                    "telegram_case_alert_failed",
                    case_id=str(case.id),
                    error=str(e),
                )

        # Send via Slack if available
        if self.slack_bot:
            try:
                result = await self.slack_notifier.notify_case_alert(case, alert_type, payload)
                results.append(result)
            except Exception as e:
                logger.error(
                    "slack_case_alert_failed",
                    case_id=str(case.id),
                    error=str(e),
                )

        if results:
            logger.info(
                "case_alert_sent",
                case_id=str(case.id),
                alert_type=alert_type,
                channels=len(results),
            )
            return any(results)
        return False

    async def close(self) -> None:
        """Close notification service and cleanup resources."""
        if self.telegram_bot:
            await self.telegram_bot.close()
        if self.slack_bot:
            self.slack_bot.close()


def get_notification_service() -> NotificationService:
    """Factory function to create NotificationService with configured Telegram and Slack bots.

    Returns:
        Configured NotificationService instance with available notification channels

    Note:
        Reads from settings:
        - TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID for Telegram
        - SLACK_BOT_TOKEN and SLACK_CHANNEL_ID for Slack
        Returns a service with available channels, or a disabled service if none configured.
    """
    telegram_bot = None
    slack_bot = None

    # Initialize Telegram if configured
    telegram_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    telegram_chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if telegram_token and telegram_chat_id:
        try:
            telegram_bot = TelegramBotClient(telegram_token, telegram_chat_id)
            logger.info("telegram_bot_initialized")
        except Exception as e:
            logger.error("failed_to_initialize_telegram_bot", error=str(e))
    else:
        logger.debug("telegram_not_configured")

    # Initialize Slack if configured
    slack_token = getattr(settings, "SLACK_BOT_TOKEN", None)
    slack_channel_id = getattr(settings, "SLACK_CHANNEL_ID", None)

    if slack_token and slack_channel_id:
        try:
            slack_bot = SlackBotClient(slack_token, slack_channel_id)
            logger.info("slack_bot_initialized")
        except Exception as e:
            logger.error("failed_to_initialize_slack_bot", error=str(e))
    else:
        logger.debug("slack_not_configured")

    if not telegram_bot and not slack_bot:
        logger.warning("no_notification_channels_configured, notifications disabled")

    return NotificationService(telegram_bot=telegram_bot, slack_bot=slack_bot)
