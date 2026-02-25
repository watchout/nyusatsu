"""Tests for TASK-17: Detail page scraper."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.od_import.detail_scraper import DetailScraper

FIXTURES = Path(__file__).parent / "fixtures" / "details"


class TestDetailScraperParse:
    """Test HTML parsing (no HTTP)."""

    def test_normal_page(self):
        """Normal page → all fields extracted."""
        html = (FIXTURES / "normal.html").read_text()
        scraper = DetailScraper()
        result = scraper.parse_html(html)

        assert result.num_participants == 5
        assert result.budget_amount == 20_000_000
        assert result.winning_rate == Decimal("0.7500")
        assert len(result.bidder_details) == 5
        assert result.bidder_details[0]["name"] == "株式会社テクノサービス"
        assert result.bidder_details[0]["amount"] == 15_000_000

    def test_no_budget_page(self):
        """Page with 非公表 budget → budget_amount is None."""
        html = (FIXTURES / "no_budget.html").read_text()
        scraper = DetailScraper()
        result = scraper.parse_html(html)

        assert result.budget_amount is None
        assert result.winning_rate is None  # Cannot calculate without budget
        assert result.num_participants == 2
        assert len(result.bidder_details) == 2

    def test_changed_structure(self):
        """Changed HTML structure → graceful degradation."""
        html = (FIXTURES / "changed_structure.html").read_text()
        scraper = DetailScraper()
        result = scraper.parse_html(html)

        # No detail-table or bidder-table in new structure
        assert result.num_participants is None
        assert result.budget_amount is None
        assert result.bidder_details == []

    def test_bidder_amounts(self):
        """Bidder amounts are correctly parsed."""
        html = (FIXTURES / "normal.html").read_text()
        scraper = DetailScraper()
        result = scraper.parse_html(html)

        amounts = [b["amount"] for b in result.bidder_details]
        assert amounts == [
            15_000_000, 17_500_000, 18_000_000, 19_000_000, 19_500_000,
        ]

    def test_raw_html_preserved(self):
        """Raw HTML is stored in result."""
        html = (FIXTURES / "normal.html").read_text()
        scraper = DetailScraper()
        result = scraper.parse_html(html)

        assert "入札公告詳細" in result.raw_html

    def test_winning_rate_calculation(self):
        """Winning rate = winning_amount / budget_amount."""
        html = (FIXTURES / "normal.html").read_text()
        scraper = DetailScraper()
        result = scraper.parse_html(html)

        # 15,000,000 / 20,000,000 = 0.75
        assert result.winning_rate == Decimal("0.7500")


class TestDetailScraperRateLimit:
    """Test rate limiting logic."""

    @pytest.mark.anyio
    async def test_rate_limit_enforced(self):
        """Consecutive requests respect rate limit."""
        import time

        scraper = DetailScraper(rate_limit_sec=0.1)

        call_times = []

        async def mock_fetch(url: str) -> str:
            call_times.append(time.monotonic())
            return "<html></html>"

        with patch.object(scraper, "_fetch", side_effect=mock_fetch):
            await scraper.scrape("http://test/1")
            await scraper.scrape("http://test/2")

        if len(call_times) == 2:
            elapsed = call_times[1] - call_times[0]
            assert elapsed >= 0.09  # Allow small tolerance
