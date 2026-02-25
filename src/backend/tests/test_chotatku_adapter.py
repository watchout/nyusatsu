"""Tests for TASK-18: ChotatkuPortalAdapter."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.services.case_fetch.chotatku_adapter import ChotatkuPortalAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "portal"


class TestChotatkuListParse:
    """Test list page parsing (no HTTP)."""

    def test_parse_list_page(self):
        """3-row list → 3 summaries with correct fields."""
        html = (FIXTURES / "notice_list.html").read_text()
        summaries = ChotatkuPortalAdapter.parse_list_page(html)

        assert len(summaries) == 3

        first = summaries[0]
        assert first["source_id"] == "PORTAL-2025-001"
        assert first["case_name"] == "情報システム運用保守業務"
        assert first["issuing_org"] == "総務省"
        assert first["bid_type"] == "一般競争入札"
        assert first["deadline"] == date(2025, 4, 30)
        assert first["detail_url"] == "/notice/001"

    def test_parse_list_all_source_ids(self):
        """All source_ids are extracted."""
        html = (FIXTURES / "notice_list.html").read_text()
        summaries = ChotatkuPortalAdapter.parse_list_page(html)
        ids = [s["source_id"] for s in summaries]
        assert ids == [
            "PORTAL-2025-001",
            "PORTAL-2025-002",
            "PORTAL-2025-003",
        ]


class TestChotatkuDetailParse:
    """Test detail page parsing (no HTTP)."""

    def test_parse_detail_page(self):
        """Detail page → region, grade, opening_date, summary."""
        html = (FIXTURES / "notice_detail.html").read_text()
        detail = ChotatkuPortalAdapter.parse_detail_page(html)

        assert detail["region"] == "東京都千代田区"
        assert detail["grade"] == "A"
        assert detail["opening_date"] == date(2025, 5, 15)
        assert "運用及び保守" in detail["summary"]

    def test_parse_changed_detail(self):
        """Changed detail page → updated fields."""
        html = (FIXTURES / "notice_changed.html").read_text()
        detail = ChotatkuPortalAdapter.parse_detail_page(html)

        assert detail["opening_date"] == date(2025, 5, 20)
        assert "仕様変更" in detail["summary"]


class TestChotatkuRawStorage:
    """Test raw HTML storage."""

    def test_save_raw(self, tmp_path: Path):
        """Raw HTML is saved to disk."""
        adapter = ChotatkuPortalAdapter(
            raw_dir=tmp_path / "portal",
        )
        adapter._save_raw("test.html", "<html>test</html>")

        saved = (tmp_path / "portal" / "test.html").read_text()
        assert saved == "<html>test</html>"
