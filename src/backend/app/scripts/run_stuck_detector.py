"""Run stuck case detector — standalone script.

Detects cases stuck in *_in_progress stages for too long and
transitions them to *_failed.

Usage:
    python -m app.scripts.run_stuck_detector
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select

from app.core.database import async_session
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.scripts.health_check import STUCK_STAGES

logger = structlog.get_logger()

# Timeout: cases stuck longer than this are considered failed
STUCK_TIMEOUT_MINUTES = 10

# Mapping: in_progress stage → failed stage
STAGE_TO_FAILED = {
    "reading_in_progress": "reading_failed",
    "judging_in_progress": "judging_failed",
    "checklist_generating": "checklist_active",  # fallback to active, not a failed state
}


async def main() -> int:
    logger.info("script_started", script="run_stuck_detector")
    threshold = datetime.now(UTC) - timedelta(minutes=STUCK_TIMEOUT_MINUTES)

    async with async_session() as db:
        # Find stuck cases
        stmt = (
            select(Case)
            .where(
                Case.current_lifecycle_stage.in_(STUCK_STAGES),
                Case.last_updated_at < threshold,
            )
        )
        result = await db.execute(stmt)
        stuck_cases = result.scalars().all()

        if not stuck_cases:
            logger.info("no_stuck_cases_found", script="run_stuck_detector")
            return 0

        logger.warning(
            "stuck_cases_detected",
            count=len(stuck_cases),
            case_ids=[str(c.id) for c in stuck_cases],
        )

        for case in stuck_cases:
            from_stage = case.current_lifecycle_stage
            to_stage = STAGE_TO_FAILED.get(from_stage, "reading_failed")

            # Transition to failed
            case.current_lifecycle_stage = to_stage
            case.last_updated_at = datetime.now(UTC)

            # Record event
            import uuid

            event = CaseEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                event_type="stuck_recovery",
                from_status=from_stage,
                to_status=to_stage,
                triggered_by="system",
                actor_id="stuck_detector",
                feature_origin="F-002",
                payload={
                    "error_type": "timeout",
                    "stuck_since": case.last_updated_at.isoformat() if case.last_updated_at else None,
                    "timeout_minutes": STUCK_TIMEOUT_MINUTES,
                },
            )
            db.add(event)

            logger.info(
                "stuck_case_recovered",
                case_id=str(case.id),
                from_stage=from_stage,
                to_stage=to_stage,
            )

        await db.commit()
        logger.info(
            "script_completed",
            script="run_stuck_detector",
            recovered=len(stuck_cases),
        )
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
