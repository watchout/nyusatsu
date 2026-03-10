"""Chotatku Portal adapter — F-001.

Scrapes the government procurement portal (調達ポータル):
1. Fetch notice list page → extract case summary rows
2. For each row, fetch detail page → extract full case info

Uses @http_retry + rate limiting.
Parse methods are isolated for easy replacement when HTML changes.
"""

from __future__ import annotations

import asyncio
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from app.core.constants import HTTP_TIMEOUT_SEC, SCRAPE_RATE_LIMIT_SEC
from app.core.retry import http_retry
from app.services.case_fetch.base_adapter import BaseSourceAdapter, RawCase

logger = structlog.get_logger()


class ChotatkuPortalAdapter(BaseSourceAdapter):
    """Adapter for the Chotatku Portal (調達ポータル).

    Args:
        base_url: Portal base URL.
        list_path: Path to the notice list page.
        raw_dir: Directory for storing raw HTML files.
        rate_limit_sec: Minimum interval between requests.
    """

    def __init__(
        self,
        base_url: str = "https://www.chotatku.go.jp",
        list_path: str = "/notice/list",
        raw_dir: Path | None = None,
        rate_limit_sec: float = SCRAPE_RATE_LIMIT_SEC,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._list_path = list_path
        self._raw_dir = raw_dir
        self._rate_limit_sec = rate_limit_sec
        self._last_request_time: float = 0.0

        if self._raw_dir:
            self._raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_name(self) -> str:
        return "chotatku_portal"

    async def fetch(self) -> list[RawCase]:
        """Fetch cases from the portal.

        1. Get notice list page
        2. Parse case summary rows
        3. For each row, optionally fetch detail page

        Returns:
            List of RawCase objects.
        """
        list_url = f"{self._base_url}{self._list_path}"
        list_html = await self._fetch_with_rate_limit(list_url)
        self._save_raw("notice_list.html", list_html)

        # Parse list page
        summaries = self.parse_list_page(list_html)

        cases: list[RawCase] = []
        for summary in summaries:
            detail_url = summary.get("detail_url")
            if detail_url:
                # Make absolute URL
                if detail_url.startswith("/"):
                    detail_url = f"{self._base_url}{detail_url}"

                try:
                    detail_html = await self._fetch_with_rate_limit(detail_url)
                    self._save_raw(
                        f"notice_{summary['source_id']}.html",
                        detail_html,
                    )
                    detail = self.parse_detail_page(detail_html)
                    summary.update(detail)
                except Exception as exc:
                    logger.warning(
                        "detail_fetch_failed",
                        source_id=summary.get("source_id"),
                        error=str(exc),
                    )

            raw_case = RawCase(
                source=self.source_name,
                source_id=summary["source_id"],
                case_name=summary.get("case_name", ""),
                issuing_org=summary.get("issuing_org", ""),
                bid_type=summary.get("bid_type"),
                region=summary.get("region"),
                grade=summary.get("grade"),
                deadline=summary.get("deadline"),
                opening_date=summary.get("opening_date"),
                published_date=summary.get("published_date"),
                summary=summary.get("summary"),
                detail_url=detail_url,
                raw_data=summary,
            )
            cases.append(raw_case)

        return cases

    # ------------------------------------------------------------------
    # Parse methods (isolated for replacement)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_list_page(html: str) -> list[dict[str, Any]]:
        """Parse the notice list page.

        Args:
            html: HTML content of the list page.

        Returns:
            List of summary dicts with keys matching RawCase fields.
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="notice-list")
        if not table:
            return []

        tbody = table.find("tbody")
        if not tbody:
            return []

        results = []
        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 7:
                continue

            source_id = cells[0].get_text(strip=True)
            if not source_id:
                continue

            # Extract detail URL from link
            link = cells[6].find("a")
            detail_url = link["href"] if link else None

            summary = {
                "source_id": source_id,
                "case_name": cells[1].get_text(strip=True),
                "issuing_org": cells[2].get_text(strip=True),
                "bid_type": cells[3].get_text(strip=True) or None,
                "published_date": _parse_date_safe(
                    cells[4].get_text(strip=True),
                ),
                "deadline": _parse_date_safe(
                    cells[5].get_text(strip=True),
                ),
                "detail_url": detail_url,
            }
            results.append(summary)

        return results

    @staticmethod
    def parse_detail_page(html: str) -> dict[str, Any]:
        """Parse a notice detail page.

        Args:
            html: HTML content of the detail page.

        Returns:
            Dict with additional fields extracted from detail.
        """
        soup = BeautifulSoup(html, "html.parser")
        detail: dict[str, Any] = {}

        info_table = soup.find("table", class_="info-table")
        if not info_table:
            return detail

        for row_elem in info_table.find_all("tr"):
            th = row_elem.find("th")
            td = row_elem.find("td")
            if not th or not td:
                continue

            label = th.get_text(strip=True)
            value = td.get_text(strip=True)

            if label == "所在地":
                detail["region"] = value
            elif label == "等級":
                detail["grade"] = value
            elif label == "開札日":
                detail["opening_date"] = _parse_date_safe(value)
            elif label == "概要":
                detail["summary"] = value

        return detail

    # ------------------------------------------------------------------
    # HTTP + storage
    # ------------------------------------------------------------------

    async def _fetch_with_rate_limit(self, url: str) -> str:
        """Fetch with rate limiting."""
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

    def _save_raw(self, filename: str, content: str) -> None:
        """Save raw HTML for audit trail."""
        if self._raw_dir:
            (self._raw_dir / filename).write_text(content, encoding="utf-8")


def _parse_date_safe(text: str) -> date | None:
    """Parse date string, returning None on failure."""
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
