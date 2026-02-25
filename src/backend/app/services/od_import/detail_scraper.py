"""Detail page scraper — F-005 Layer 2.

Scrapes bid announcement detail pages to extract supplementary data:
- num_participants (参加社数)
- budget_amount (予定価格)
- bidder_details (応札者一覧)
- winning_rate (落札率) — auto-calculated if budget_amount available

Uses @http_retry + rate limiting (SCRAPE_RATE_LIMIT_SEC).
Parse methods are isolated for easy replacement when HTML changes.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from app.core.constants import HTTP_TIMEOUT_SEC, SCRAPE_RATE_LIMIT_SEC
from app.core.retry import http_retry

logger = structlog.get_logger()


@dataclass
class DetailResult:
    """Parsed detail page data, ready for bid_details upsert."""

    num_participants: int | None = None
    budget_amount: int | None = None
    winning_rate: Decimal | None = None
    bidder_details: list[dict[str, Any]] = field(default_factory=list)
    raw_html: str = ""


class DetailScraper:
    """Scrape bid detail pages with rate limiting.

    Args:
        rate_limit_sec: Minimum interval between requests.
    """

    def __init__(
        self, rate_limit_sec: float = SCRAPE_RATE_LIMIT_SEC,
    ) -> None:
        self._rate_limit_sec = rate_limit_sec
        self._last_request_time: float = 0.0

    async def scrape(self, url: str) -> DetailResult:
        """Fetch and parse a detail page.

        Args:
            url: Detail page URL.

        Returns:
            DetailResult with extracted fields.
        """
        html = await self._fetch_with_rate_limit(url)
        return self.parse_html(html)

    def parse_html(self, html: str) -> DetailResult:
        """Parse detail page HTML into structured data.

        This method is isolated so it can be overridden or replaced
        when the portal changes its HTML structure.
        """
        soup = BeautifulSoup(html, "html.parser")
        result = DetailResult(raw_html=html)

        # Extract from detail-table
        detail_table = soup.find("table", class_="detail-table")
        if detail_table:
            result.num_participants = self._extract_participants(detail_table)
            result.budget_amount = self._extract_budget(detail_table)

        # Extract bidder details
        bidder_table = soup.find("table", class_="bidder-table")
        if bidder_table:
            result.bidder_details = self._extract_bidders(bidder_table)
            # Override num_participants from actual bidder count if available
            if result.bidder_details and result.num_participants is None:
                result.num_participants = len(result.bidder_details)

        # Calculate winning rate
        if result.budget_amount and result.budget_amount > 0:
            winning_amount = self._extract_winning_amount(detail_table)
            if winning_amount is not None:
                rate = Decimal(str(winning_amount)) / Decimal(str(result.budget_amount))
                result.winning_rate = rate.quantize(Decimal("0.0001"))

        return result

    # ------------------------------------------------------------------
    # Extraction helpers (isolated for easy replacement)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_participants(table: Any) -> int | None:
        """Extract participant count from detail table."""
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "参加者" in th.get_text():
                match = re.search(r"(\d+)", td.get_text())
                if match:
                    return int(match.group(1))
        return None

    @staticmethod
    def _extract_budget(table: Any) -> int | None:
        """Extract budget amount from detail table."""
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "予定価格" in th.get_text():
                text = td.get_text()
                if "非公表" in text or "未定" in text:
                    return None
                cleaned = re.sub(r"[^\d]", "", text)
                if cleaned:
                    return int(cleaned)
        return None

    @staticmethod
    def _extract_winning_amount(table: Any) -> int | None:
        """Extract winning amount from detail table."""
        if table is None:
            return None
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "落札金額" in th.get_text():
                cleaned = re.sub(r"[^\d]", "", td.get_text())
                if cleaned:
                    return int(cleaned)
        return None

    @staticmethod
    def _extract_bidders(table: Any) -> list[dict[str, Any]]:
        """Extract bidder details from bidder table."""
        bidders = []
        tbody = table.find("tbody")
        if not tbody:
            return bidders

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                name = cells[0].get_text(strip=True)
                amount_text = cells[1].get_text(strip=True)
                amount_cleaned = re.sub(r"[^\d]", "", amount_text)
                bidders.append({
                    "name": name,
                    "amount": int(amount_cleaned) if amount_cleaned else None,
                })

        return bidders

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _fetch_with_rate_limit(self, url: str) -> str:
        """Fetch URL with rate limiting between requests."""
        import time

        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_sec:
            await asyncio.sleep(self._rate_limit_sec - elapsed)

        html = await self._fetch(url)
        self._last_request_time = time.monotonic()
        return html

    @http_retry
    async def _fetch(self, url: str) -> str:
        """HTTP GET with retry."""
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
