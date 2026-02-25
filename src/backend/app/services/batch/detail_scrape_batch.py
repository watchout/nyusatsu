"""Detail scrape batch runner — F-005 Layer 2.

Finds base_bids that have a detail_url but no corresponding bid_details
record, scrapes the detail page, and stores in bid_details.

Implements BaseBatchRunner for use with BatchRunner.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base_bid import BaseBid
from app.models.bid_detail import BidDetail
from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import (
    BatchConfig,
    BatchItemResult,
    ItemStatus,
)
from app.services.od_import.detail_scraper import DetailScraper

logger = structlog.get_logger()


class DetailScrapeBatch(BaseBatchRunner):
    """Batch runner for scraping detail pages.

    Args:
        scraper: DetailScraper instance (injectable for testing).
    """

    def __init__(self, scraper: DetailScraper | None = None) -> None:
        self._scraper = scraper or DetailScraper()

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source="open_data",
            batch_type="detail_scrape",
            feature_origin="F-005",
        )

    async def fetch_items(
        self, db: AsyncSession,
    ) -> AsyncIterator[BaseBid]:
        """Yield base_bids needing detail scraping.

        Criteria:
        - detail_url is not NULL
        - No corresponding bid_details record exists
        """
        stmt = (
            select(BaseBid)
            .outerjoin(BidDetail, BidDetail.base_bid_id == BaseBid.id)
            .where(
                BaseBid.detail_url.isnot(None),
                BaseBid.detail_url != "",
                BidDetail.id.is_(None),  # No detail yet
            )
            .order_by(BaseBid.imported_at)
        )
        result = await db.execute(stmt)
        for bid in result.scalars():
            yield bid

    async def process_item(
        self, db: AsyncSession, item: Any,
    ) -> BatchItemResult:
        """Scrape detail page and store in bid_details."""
        bid: BaseBid = item

        detail_result = await self._scraper.scrape(bid.detail_url)

        # Create bid_detail record
        detail = BidDetail(
            base_bid_id=bid.id,
            num_participants=detail_result.num_participants,
            budget_amount=detail_result.budget_amount,
            winning_rate=detail_result.winning_rate,
            bidder_details=detail_result.bidder_details or None,
            raw_html=detail_result.raw_html,
        )
        db.add(detail)
        await db.flush()

        logger.debug(
            "detail_scraped",
            base_bid_id=str(bid.id),
            source_id=bid.source_id,
            num_participants=detail_result.num_participants,
        )

        return BatchItemResult(
            item_id=bid.source_id,
            status=ItemStatus.SUCCESS,
        )
