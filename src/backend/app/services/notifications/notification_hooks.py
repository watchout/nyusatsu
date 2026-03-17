"""Hooks for integrating notifications into case workflows."""

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.services.notifications.notification_service import NotificationService

logger = structlog.get_logger()


async def notify_on_case_scored(
    case: Case,
    notification_service: NotificationService,
) -> None:
    """Send notification when case is scored and exceeds threshold.

    Called after scoring but before lifecycle transition to 'scored'.

    Args:
        case: Case that was just scored
        notification_service: NotificationService instance
    """
    if not case.score:
        logger.debug("case_scored_no_score", case_id=str(case.id))
        return

    try:
        await notification_service.notify_high_score_case(case)
    except Exception as e:
        logger.error(
            "notification_on_case_scored_failed",
            case_id=str(case.id),
            error=str(e),
        )


async def notify_on_lifecycle_transition(
    case: Case,
    from_stage: str,
    to_stage: str,
    notification_service: NotificationService,
) -> None:
    """Send notification on important lifecycle transitions.

    Args:
        case: Case undergoing transition
        from_stage: Previous stage
        to_stage: New stage
        notification_service: NotificationService instance
    """
    important_transitions = {
        ("discovered", "scored"): "新規案件がスコアリングされました",
        ("under_review", "planned"): "案件が計画段階に進行しました",
        ("reading_queued", "reading_in_progress"): "資料読み込みを開始しました",
        ("judging_queued", "judging_in_progress"): "適格性判定を開始しました",
        ("checklist_active", "checklist_completed"): "チェックリストが完了しました",
    }

    transition_key = (from_stage, to_stage)
    if transition_key not in important_transitions:
        return

    try:
        message_suffix = important_transitions[transition_key]
        await notification_service.notify_case_alert(
            case,
            alert_type="lifecycle_transition",
            payload={"message_suffix": message_suffix},
        )
    except Exception as e:
        logger.error(
            "notification_on_lifecycle_transition_failed",
            case_id=str(case.id),
            transition=f"{from_stage}->{to_stage}",
            error=str(e),
        )


def check_deadline_warning(case: Case) -> int | None:
    """Check if case deadline is approaching and return days left.

    Args:
        case: Case to check

    Returns:
        Days left until deadline (1-7), or None if no warning needed
    """
    if not case.submission_deadline:
        return None

    now = datetime.now(UTC)
    time_diff = case.submission_deadline - now
    days_left = time_diff.days

    # Only warn if 1-7 days left
    if 0 <= days_left <= 7:
        return days_left

    return None


async def notify_on_deadline_check(
    case: Case,
    notification_service: NotificationService,
) -> None:
    """Send notification if case deadline is approaching.

    Args:
        case: Case to check
        notification_service: NotificationService instance
    """
    days_left = check_deadline_warning(case)
    if days_left is None:
        return

    try:
        await notification_service.notify_deadline_warning(case, days_left)
    except Exception as e:
        logger.error(
            "notification_on_deadline_check_failed",
            case_id=str(case.id),
            error=str(e),
        )


async def notify_batch_completion(
    db: AsyncSession,
    new_cases_count: int,
    high_score_threshold: int,
    notification_service: NotificationService,
) -> None:
    """Send summary notification after batch processing.

    Args:
        db: Database session
        new_cases_count: Count of newly discovered cases
        high_score_threshold: Score threshold for high-score detection
        notification_service: NotificationService instance
    """
    if not notification_service.telegram_bot:
        return

    try:
        from sqlalchemy import and_, func, select

        # Count high-score cases discovered today
        from app.models.case import Case

        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        high_score_query = select(func.count(Case.id)).where(
            and_(
                Case.score >= high_score_threshold,
                Case.first_seen_at >= today_start,
            ),
        )
        high_score_count = await db.scalar(high_score_query) or 0

        # Count deadline warnings (1-7 days left)
        warning_query = select(func.count(Case.id)).where(
            and_(
                Case.submission_deadline.isnot(None),
                Case.current_lifecycle_stage != "archived",
            ),
        )
        # This is a rough count; actual filtering happens in notify_on_deadline_check
        warning_count = await db.scalar(warning_query) or 0

        await notification_service.notify_batch_summary(
            new_cases=new_cases_count,
            high_score_cases=high_score_count,
            deadline_warning_cases=warning_count,
        )

    except Exception as e:
        logger.error(
            "notification_batch_completion_failed",
            error=str(e),
        )
