#!/usr/bin/env python3
"""Historical price data import — F-005."""

import asyncio
import logging

# Setup path for imports
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models import Case, PriceHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def import_sample_price_data(session: AsyncSession) -> None:
    """
    サンプル相場データをインポート。

    実装時には以下ソースから取得:
    - スクレイプ済みPDF
    - 落札情報サイト
    - ユーザー入力
    """

    # Get sample cases
    result = await session.execute(select(Case).limit(10))
    cases = result.scalars().all()

    if not cases:
        logger.warning("No cases found. Skipping price data import.")
        return

    for case in cases:
        # Generate sample price data for last 6 months
        for days_ago in [30, 60, 90, 120, 150, 180]:
            recorded_at = datetime.now(UTC) - timedelta(days=days_ago)

            # Deterministic sample prices based on case
            base_price = hash(case.id) % 5000000 + 1000000
            variation = hash((case.id, days_ago)) % 500000

            winning_bid = Decimal(str(base_price + variation))
            budgeted_price = Decimal(str(base_price + variation + 100000))
            total_bids = (hash((case.id, days_ago)) % 15) + 2

            # Check if already exists
            existing = await session.execute(
                select(PriceHistory).where(
                    (PriceHistory.case_id == case.id)
                    & (PriceHistory.recorded_at == recorded_at)
                )
            )

            if existing.scalars().first():
                continue

            # Create price history
            price_diff = (
                ((winning_bid - budgeted_price) / budgeted_price * 100)
                if budgeted_price > 0
                else Decimal("0")
            )

            history = PriceHistory(
                case_id=case.id,
                budgeted_price=budgeted_price,
                winning_bid=winning_bid,
                lowest_bid=Decimal(str(int(winning_bid) - 50000)),
                total_bids=total_bids,
                unique_bidders=total_bids - 1,
                bid_rate=Decimal("85.0"),
                price_difference_rate=Decimal(str(round(price_diff, 2))),
                data_source="sample_import",
                recorded_at=recorded_at,
                confidence_score=75,
                raw_data={
                    "source": "sample",
                    "category": case.category,
                    "region": case.region,
                },
            )

            session.add(history)
            logger.info(
                f"Added price history for case {case.case_name} "
                f"(winning_bid={winning_bid})"
            )

    await session.commit()
    logger.info("Price data import completed.")


async def main() -> None:
    """Main entry point."""
    engine = create_async_engine(
        settings.DATABASE_URL, echo=False, future=True
    )

    async with sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        try:
            await import_sample_price_data(session)
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    asyncio.run(main())
