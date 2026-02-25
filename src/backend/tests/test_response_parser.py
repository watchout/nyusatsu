"""Tests for ResponseParser (F-002 Stage 2)."""

import json

import pytest

from app.schemas.evidence import AssertionType
from app.schemas.extraction import CaseCardExtraction
from app.services.reading.response_parser import ParseError, ResponseParser


class TestResponseParser:
    def test_parse_valid_json(self) -> None:
        parser = ResponseParser()
        data = {
            "eligibility": {
                "unified_qualification": True,
                "grade": "C",
                "business_category": "物品の販売",
                "region": "関東・甲信越",
            },
            "schedule": {
                "submission_deadline": "2026-03-15T17:00:00+09:00",
            },
            "business_content": {
                "summary": "コピー用紙購入",
            },
            "submission_items": {
                "bid_time_items": [
                    {"name": "入札書", "assertion_type": "fact"},
                ],
            },
            "risk_factors": [],
        }
        result = parser.parse(json.dumps(data))
        assert isinstance(result, CaseCardExtraction)
        assert result.eligibility.grade == "C"
        assert result.schedule.submission_deadline == "2026-03-15T17:00:00+09:00"
        assert result.business_content.summary == "コピー用紙購入"
        assert len(result.submission_items.bid_time_items) == 1

    def test_parse_json_in_markdown_block(self) -> None:
        parser = ResponseParser()
        raw = '```json\n{"eligibility": {"unified_qualification": true}}\n```'
        result = parser.parse(raw)
        assert result.eligibility.unified_qualification is True

    def test_invalid_json_raises_parse_error(self) -> None:
        parser = ResponseParser()
        with pytest.raises(ParseError, match="Invalid JSON"):
            parser.parse("this is not json")

    def test_non_dict_raises_parse_error(self) -> None:
        parser = ResponseParser()
        with pytest.raises(ParseError, match="Expected JSON object"):
            parser.parse("[1, 2, 3]")

    def test_invalid_assertion_type_fixed_to_inferred(self) -> None:
        parser = ResponseParser()
        data = {
            "submission_items": {
                "bid_time_items": [
                    {"name": "入札書", "assertion_type": "UNKNOWN_TYPE"},
                ],
            },
        }
        result = parser.parse(json.dumps(data))
        assert result.submission_items.bid_time_items[0].assertion_type == AssertionType.INFERRED

    def test_partial_null_fields(self) -> None:
        parser = ResponseParser()
        data = {
            "eligibility": None,
            "schedule": None,
            "business_content": None,
            "submission_items": None,
            "risk_factors": [],
        }
        result = parser.parse(json.dumps(data))
        assert result.eligibility is None
        assert result.schedule is None
        assert result.risk_factors == []

    def test_all_five_categories(self) -> None:
        parser = ResponseParser()
        data = {
            "eligibility": {
                "unified_qualification": True,
                "grade": "D",
                "business_category": "役務の提供",
                "region": "関東・甲信越",
                "additional_requirements": [
                    {"name": "Pマーク", "type": "certification", "assertion_type": "fact"},
                ],
            },
            "schedule": {
                "submission_deadline": "2026-04-01T17:00:00+09:00",
                "opening_date": "2026-04-05T10:00:00+09:00",
                "quote_deadline": "2026-03-25T17:00:00+09:00",
            },
            "business_content": {
                "business_type": "役務の提供",
                "summary": "清掃業務",
                "items": [{"name": "清掃", "quantity": "年間"}],
                "delivery_locations": [{"address": "東京都千代田区"}],
                "has_quote_requirement": True,
            },
            "submission_items": {
                "bid_time_items": [
                    {"name": "入札書", "assertion_type": "fact"},
                    {"name": "資格審査結果通知書写し", "assertion_type": "fact"},
                ],
                "performance_time_items": [
                    {"name": "業務計画書", "assertion_type": "inferred"},
                ],
            },
            "risk_factors": [
                {
                    "risk_type": "quote_deadline_urgent",
                    "label": "見積もり期限迫り",
                    "severity": "high",
                    "description": "期限が5日以内",
                    "assertion_type": "fact",
                },
            ],
        }
        result = parser.parse(json.dumps(data))
        assert result.eligibility is not None
        assert result.schedule is not None
        assert result.business_content is not None
        assert result.submission_items is not None
        assert len(result.risk_factors) == 1

    def test_json_with_surrounding_text(self) -> None:
        """Parser should extract JSON even with surrounding text."""
        parser = ResponseParser()
        raw = 'Here is the extraction:\n{"eligibility": {"unified_qualification": true}}\nDone.'
        result = parser.parse(raw)
        assert result.eligibility.unified_qualification is True
