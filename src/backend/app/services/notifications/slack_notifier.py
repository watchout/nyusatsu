"""Slack notification formatter and sender for case alerts."""

from datetime import UTC, datetime
from typing import Any

import structlog

from app.models.case import Case
from app.services.notifications.slack_bot import SlackBotClient

logger = structlog.get_logger()

# Default score threshold for notifications (30 points)
DEFAULT_SCORE_THRESHOLD = 30


class SlackNotifier:
    """Formatter and sender for Slack notifications using Block Kit."""

    def __init__(
        self,
        slack_bot: SlackBotClient | None = None,
        score_threshold: int = DEFAULT_SCORE_THRESHOLD,
    ):
        """Initialize Slack notifier.

        Args:
            slack_bot: SlackBotClient instance (can be None for testing)
            score_threshold: Score threshold for high-priority notifications (0-100)
        """
        self.slack_bot = slack_bot
        self.score_threshold = max(0, min(100, score_threshold))

    @staticmethod
    def _get_score_color(score: int | None) -> str:
        """Get Slack color code based on score level.

        Returns:
            Hex color code for Slack message attachment
        """
        if score is None:
            return "#FF6B6B"  # Red
        if score >= 70:
            return "#FF6B6B"  # Red - High priority
        if score >= 40:
            return "#FFA94D"  # Orange - Medium priority
        return "#74B9FF"  # Blue - Low priority

    @staticmethod
    def _get_score_emoji(score: int | None) -> str:
        """Get emoji based on score level."""
        if score is None:
            return "🚨"
        if score >= 70:
            return "🔥"  # High score
        if score >= 40:
            return "⚡"  # Medium score
        return "⏰"  # Low score

    @staticmethod
    def _get_urgency_level(score: int | None) -> str:
        """Get urgency level description."""
        if score is None:
            return "アラート"
        if score >= 80:
            return "🚨 非常に高い"
        if score >= 60:
            return "⚠️ 高い"
        if score >= 40:
            return "📌 中程度"
        return "ℹ️ 低い"

    @staticmethod
    def format_case_alert_blocks(case: Case, threshold_exceeded: bool = False) -> list[dict]:
        """Format case as Slack Block Kit blocks.

        Args:
            case: Case to format
            threshold_exceeded: Whether the case exceeded score threshold

        Returns:
            List of Slack Block Kit block dictionaries
        """
        score_emoji = SlackNotifier._get_score_emoji(case.score)

        deadline_str = "未定"
        days_left = "不明"
        if case.submission_deadline:
            deadline_str = case.submission_deadline.strftime("%Y年%m月%d日 %H:%M")
            delta = case.submission_deadline - datetime.now(UTC)
            days_left = str(delta.days)
            if int(days_left) < 0:
                days_left = "期限切れ"

        header_emoji = "🚨" if threshold_exceeded else "📋"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{header_emoji} 案件アラート {score_emoji}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*案件名:*\n`{case.case_name}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*スコア:*\n{case.score or 'N/A'}/100",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*発注元:*\n{case.issuing_org}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*期限:*\n{deadline_str}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*カテゴリ:*\n{case.category or '未分類'}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*地域:*\n{case.region or '全国'}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*入札種類:*\n{case.bid_type or '一般'}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*状態:*\n{case.current_lifecycle_stage}",
                    },
                ],
            },
            {
                "type": "divider",
            },
        ]

        # Add context section
        context_blocks = []
        if case.detail_url:
            context_blocks.append(
                {
                    "type": "mrkdwn",
                    "text": f"<{case.detail_url}|詳細を見る>",
                }
            )

        if context_blocks:
            blocks.append(
                {
                    "type": "context",
                    "elements": context_blocks,
                }
            )

        return blocks

    @staticmethod
    def format_high_score_blocks(case: Case) -> list[dict]:
        """Format high-score case notification blocks.

        Args:
            case: Case with high score

        Returns:
            List of Slack Block Kit block dictionaries
        """
        urgency = SlackNotifier._get_urgency_level(case.score)

        deadline_str = "未定"
        if case.submission_deadline:
            deadline_str = case.submission_deadline.strftime("%Y年%m月%d日")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔥 高スコア案件発見！",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*案件名:* `{case.case_name}`\n*スコア:* "
                        f"`{case.score}/100` ({urgency})\n*発注元:* "
                        f"{case.issuing_org}\n*期限:* {deadline_str}\n"
                        f"*カテゴリ:* {case.category or '未分類'}\n\n"
                        "即対応を推奨します！"
                    ),
                },
            },
        ]

        if case.detail_url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "案件詳細を確認",
                                "emoji": True,
                            },
                            "url": case.detail_url,
                            "style": "danger",
                        }
                    ],
                }
            )

        return blocks

    @staticmethod
    def format_deadline_warning_blocks(case: Case, days_left: int) -> list[dict]:
        """Format deadline warning notification blocks.

        Args:
            case: Case with approaching deadline
            days_left: Days remaining until deadline

        Returns:
            List of Slack Block Kit block dictionaries
        """
        is_urgent = days_left <= 3
        urgency_emoji = "🚨" if is_urgent else "⚠️"

        deadline_str = "未定"
        if case.submission_deadline:
            deadline_str = case.submission_deadline.strftime("%Y年%m月%d日 %H:%M")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{urgency_emoji} 期限が近づいています",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*案件:* `{case.case_name}`\n*残り日数:* *{days_left}日*\n"
                        f"*期限:* {deadline_str}\n*発注元:* {case.issuing_org}\n"
                        f"*スコア:* {case.score}/100\n\n急いで対応してください！"
                    ),
                },
            },
        ]

        if case.detail_url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "案件を開く",
                                "emoji": True,
                            },
                            "url": case.detail_url,
                            "style": "primary" if is_urgent else "danger",
                        }
                    ],
                }
            )

        return blocks

    @staticmethod
    def format_batch_summary_blocks(
        new_cases: int,
        high_score_cases: int,
        deadline_warning_cases: int,
    ) -> list[dict]:
        """Format batch processing summary blocks.

        Args:
            new_cases: Count of new cases
            high_score_cases: Count of high-score cases
            deadline_warning_cases: Count of deadline warning cases

        Returns:
            List of Slack Block Kit block dictionaries
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✨ 新規案件処理完了",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"📊 *処理サマリ:*\n• 新規案件: *{new_cases}*件\n"
                        f"• 高スコア案件: *{high_score_cases}*件\n"
                        f"• 期限間近案件: *{deadline_warning_cases}*件\n\n"
                        "詳細はダッシュボードをご確認ください。"
                    ),
                },
            },
        ]

        return blocks

    async def notify_high_score_case(self, case: Case) -> bool:
        """Send notification for a high-score case.

        Args:
            case: Case with high score

        Returns:
            True if notification sent successfully
        """
        if not self.slack_bot or case.score is None:
            return False

        if case.score < self.score_threshold:
            logger.debug(
                "case_below_threshold",
                case_id=str(case.id),
                score=case.score,
                threshold=self.score_threshold,
            )
            return False

        try:
            blocks = self.format_high_score_blocks(case)
            success = self.slack_bot.send_blocks(blocks)

            if success:
                logger.info(
                    "high_score_notification_sent",
                    case_id=str(case.id),
                    score=case.score,
                )
            return success

        except Exception as e:
            logger.error(
                "high_score_notification_failed",
                case_id=str(case.id),
                error=str(e),
            )
            return False

    async def notify_deadline_warning(self, case: Case, days_left: int) -> bool:
        """Send notification for approaching deadline.

        Args:
            case: Case with approaching deadline
            days_left: Days remaining until deadline

        Returns:
            True if notification sent successfully
        """
        if not self.slack_bot:
            return False

        # Only notify if deadline is within 7 days
        if days_left > 7 or days_left < 0:
            return False

        try:
            blocks = self.format_deadline_warning_blocks(case, days_left)
            success = self.slack_bot.send_blocks(blocks)

            if success:
                logger.info(
                    "deadline_warning_sent",
                    case_id=str(case.id),
                    days_left=days_left,
                )
            return success

        except Exception as e:
            logger.error(
                "deadline_warning_failed",
                case_id=str(case.id),
                error=str(e),
            )
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
        if not self.slack_bot:
            return False

        try:
            blocks = self.format_batch_summary_blocks(
                new_cases,
                high_score_cases,
                deadline_warning_cases,
            )
            success = self.slack_bot.send_blocks(blocks)

            if success:
                logger.info(
                    "batch_summary_sent",
                    new_cases=new_cases,
                    high_score_cases=high_score_cases,
                    deadline_warning_cases=deadline_warning_cases,
                )
            return success

        except Exception as e:
            logger.error(
                "batch_summary_failed",
                error=str(e),
            )
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
        if not self.slack_bot:
            return False

        try:
            blocks = self.format_case_alert_blocks(case, threshold_exceeded=True)
            success = self.slack_bot.send_blocks(blocks)

            if success:
                logger.info(
                    "case_alert_sent",
                    case_id=str(case.id),
                    alert_type=alert_type,
                )
            return success

        except Exception as e:
            logger.error(
                "case_alert_failed",
                case_id=str(case.id),
                error=str(e),
            )
            return False

    def close(self) -> None:
        """Close notifier and cleanup resources."""
        if self.slack_bot:
            self.slack_bot.close()
