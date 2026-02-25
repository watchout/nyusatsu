"""Tests for TASK-18: CaseNormalizer."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.case_fetch.base_adapter import RawCase
from app.services.case_fetch.normalizer import CaseNormalizer


class TestCaseNormalizer:
    """Test case normalisation."""

    def test_normalise_basic(self):
        """Basic normalisation with all fields."""
        normalizer = CaseNormalizer()
        raw = RawCase(
            source="test",
            source_id="NORM-001",
            case_name="情報システム運用保守業務",
            issuing_org="総務省",
            bid_type="一般競争入札",
            region="東京都",
            deadline=date(2025, 4, 30),
        )
        result = normalizer.normalise(raw)

        assert result.data["source"] == "test"
        assert result.data["source_id"] == "NORM-001"
        assert result.data["case_name"] == "情報システム運用保守業務"
        assert result.data["current_lifecycle_stage"] == "discovered"
        assert "submission_deadline" in result.data
        assert result.warnings == []

    def test_fullwidth_to_halfwidth(self):
        """NFKC normalisation: full-width → half-width."""
        normalizer = CaseNormalizer()
        raw = RawCase(
            source="test",
            source_id="NORM-002",
            case_name="ＡＢＣ　１２３",  # Full-width
            issuing_org="テスト省",
        )
        result = normalizer.normalise(raw)

        assert result.data["case_name"] == "ABC 123"

    def test_required_field_missing(self):
        """Missing required field → ValueError."""
        normalizer = CaseNormalizer()
        raw = RawCase(
            source="test",
            source_id="NORM-003",
            case_name="",  # Empty
            issuing_org="テスト省",
        )
        with pytest.raises(ValueError, match="case_name"):
            normalizer.normalise(raw)


class TestDiffDetection:
    """Test difference detection."""

    def test_detect_diff(self):
        """Changed fields are detected."""
        normalizer = CaseNormalizer()
        old = {
            "source": "test",
            "source_id": "DIFF-001",
            "case_name": "旧名称",
            "submission_deadline": date(2025, 4, 30),
        }
        new = {
            "source": "test",
            "source_id": "DIFF-001",
            "case_name": "新名称",
            "submission_deadline": date(2025, 5, 15),
        }
        diff = normalizer.detect_diff(old, new)

        assert "case_name" in diff
        assert diff["case_name"] == ("旧名称", "新名称")
        assert "submission_deadline" in diff
        # source and source_id should not be in diff
        assert "source" not in diff
        assert "source_id" not in diff

    def test_no_diff(self):
        """Identical data → empty diff."""
        normalizer = CaseNormalizer()
        data = {
            "source": "test",
            "source_id": "DIFF-002",
            "case_name": "同じ名前",
        }
        diff = normalizer.detect_diff(data, data)
        assert diff == {}
