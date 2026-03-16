"""CLI script: Extract and process case cards from cases in 'reading_completed' stage.

Usage:
    python -m app.scripts.run_case_card_extraction [--case-id UUID] [--batch-size INT]

Examples:
    # Process all cases pending card extraction
    python -m app.scripts.run_case_card_extraction

    # Process specific case
    python -m app.scripts.run_case_card_extraction --case-id abc123...

    # Batch mode with custom batch size
    python -m app.scripts.run_case_card_extraction --batch-size 10
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.logging import setup_logging
from app.models.case import Case
from app.models.case_card import CaseCard
from app.services.case_card_service import CaseCardService
from app.services.llm.factory import get_llm_provider
from app.services.reading.reading_service import ReadingService

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def extract_case_card(
    db: AsyncSession,
    case_id: UUID,
) -> bool:
    """Extract and store case card for a single case.
    
    Returns:
        True if extraction succeeded, False otherwise.
    """
    case = await db.get(Case, case_id)
    if not case:
        logger.warning(f"Case {case_id} not found")
        return False

    if case.current_lifecycle_stage != "reading_completed":
        logger.info(
            f"Skipping {case_id}: stage is {case.current_lifecycle_stage}, "
            "expected 'reading_completed'"
        )
        return False

    # Check if current card already exists
    existing = (
        await db.execute(
            select(CaseCard)
            .where(CaseCard.case_id == case_id)
            .where(CaseCard.is_current)
        )
    ).scalar_one_or_none()

    if existing:
        logger.info(f"Case {case_id} already has current card version {existing.version}")
        return False

    try:
        service = CaseCardService(db)
        card = await service.extract_and_store_card(
            case_id=case_id,
            notice_html=case.notice_html,
            spec_pdf_url=case.spec_pdf_url,
        )
        logger.info(
            f"✓ Extracted card for case {case_id} "
            f"(version {card.version}, confidence: {card.confidence_score})"
        )
        return True
    except Exception as e:
        logger.error(f"✗ Failed to extract card for {case_id}: {e}", exc_info=True)
        return False


async def extract_batch(
    db: AsyncSession,
    batch_size: int = 10,
) -> dict[str, int]:
    """Extract cards for all cases in 'reading_completed' stage without current cards.
    
    Returns:
        Summary dict with success/failure counts.
    """
    # Query: reading_completed, no current card
    cases = (
        await db.execute(
            select(Case)
            .where(Case.current_lifecycle_stage == "reading_completed")
            .where(
                ~Case.id.in_(
                    select(CaseCard.case_id).where(CaseCard.is_current)
                )
            )
            .limit(batch_size)
        )
    ).scalars().all()

    logger.info(f"Found {len(cases)} cases pending card extraction")

    success_count = 0
    failure_count = 0

    for case in cases:
        if await extract_case_card(db, case.id):
            success_count += 1
        else:
            failure_count += 1
        await db.commit()

    return {
        "total": len(cases),
        "success": success_count,
        "failure": failure_count,
    }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract case cards from 'reading_completed' cases"
    )
    parser.add_argument(
        "--case-id",
        type=str,
        help="Extract card for specific case UUID",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for bulk extraction (default: 10)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    async with async_session_maker() as db:
        try:
            if args.case_id:
                # Single case mode
                logger.info(f"Extracting card for case {args.case_id}...")
                success = await extract_case_card(db, UUID(args.case_id))
                await db.commit()
                sys.exit(0 if success else 1)
            else:
                # Batch mode
                logger.info(f"Batch extraction (batch_size={args.batch_size})...")
                result = await extract_batch(db, batch_size=args.batch_size)
                logger.info(
                    f"✓ Completed: {result['success']}/{result['total']} "
                    f"({result['failure']} failures)"
                )
                sys.exit(0 if result["failure"] == 0 else 1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
