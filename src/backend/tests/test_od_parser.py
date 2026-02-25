"""Tests for TASK-16: OD CSV parser."""

from __future__ import annotations

from pathlib import Path

from app.services.od_import.parser import ODParser, ParseError, ParsedRow

FIXTURES = Path(__file__).parent / "fixtures" / "od"


class TestODParserFull:
    """Parse a well-formed 5-row CSV."""

    def test_parse_full_csv(self):
        """5 rows → 5 ParsedRow, 0 errors."""
        parser = ODParser()
        results = list(parser.parse_file(FIXTURES / "sample_full.csv"))

        assert len(results) == 5
        assert all(isinstance(r, ParsedRow) for r in results)

    def test_parsed_fields(self):
        """First row has correct normalised values."""
        parser = ODParser()
        results = list(parser.parse_file(FIXTURES / "sample_full.csv"))
        first = results[0]
        assert isinstance(first, ParsedRow)

        assert first.data["source_id"] == "OD-2025-001"
        assert first.data["case_name"] == "サーバー保守業務委託"
        assert first.data["issuing_org"] == "防衛省"
        assert first.data["winning_amount"] == 15_000_000
        assert first.data["opening_date"].isoformat() == "2025-04-01"
        assert first.data["detail_url"] == "https://example.go.jp/detail/001"

    def test_raw_data_preserved(self):
        """raw_data JSONB contains all original CSV columns."""
        parser = ODParser()
        results = list(parser.parse_file(FIXTURES / "sample_full.csv"))
        first = results[0]
        assert isinstance(first, ParsedRow)

        assert first.data["raw_data"]["案件番号"] == "OD-2025-001"
        assert first.data["raw_data"]["落札金額"] == "15000000"


class TestODParserInvalid:
    """Parse CSV with invalid rows."""

    def test_invalid_rows_yield_errors(self):
        """Invalid rows → ParseError; valid rows → ParsedRow."""
        parser = ODParser()
        results = list(parser.parse_file(FIXTURES / "sample_invalid.csv"))

        parsed = [r for r in results if isinstance(r, ParsedRow)]
        errors = [r for r in results if isinstance(r, ParseError)]

        # Row 1 = good, Row 2 = empty (skipped), Row 3 = no name, Row 4 = bad amount, Row 5 = bad date
        assert len(parsed) == 1
        assert parsed[0].data["source_id"] == "OD-2025-GOOD"
        assert len(errors) == 3  # no name, bad amount, bad date

    def test_error_has_row_number(self):
        """ParseError includes the row number."""
        parser = ODParser()
        results = list(parser.parse_file(FIXTURES / "sample_invalid.csv"))
        errors = [r for r in results if isinstance(r, ParseError)]

        assert all(e.row_number >= 2 for e in errors)


class TestODParserEmpty:
    """Parse an empty CSV (header only)."""

    def test_empty_csv_yields_nothing(self):
        """Header-only CSV → 0 results."""
        parser = ODParser()
        results = list(parser.parse_file(FIXTURES / "sample_empty.csv"))
        assert results == []


class TestODParserAmounts:
    """Test amount parsing edge cases."""

    def test_amount_with_commas(self):
        """Amounts with commas are handled."""
        parser = ODParser()
        assert parser._parse_amount("15,000,000") == 15_000_000

    def test_amount_zero(self):
        """Zero amount is valid."""
        parser = ODParser()
        assert parser._parse_amount("0") == 0

    def test_amount_with_yen_sign(self):
        """Yen symbol is stripped."""
        parser = ODParser()
        assert parser._parse_amount("￥1000") == 1000

    def test_empty_amount_returns_none(self):
        """Empty string → None."""
        parser = ODParser()
        assert parser._parse_amount("") is None


class TestODParserBOM:
    """Test UTF-8 BOM handling."""

    def test_bom_text(self):
        """UTF-8 BOM in text is handled correctly."""
        parser = ODParser()
        bom_text = "\ufeff案件番号,案件名称,発注機関,発注機関コード,入札方式,分類,落札金額,落札者,開札日,契約日,公告URL\nBOM-001,BOMテスト,テスト省,999,一般,役務,1000,テスト社,2025-01-01,,"
        results = list(parser.parse_text(bom_text))

        assert len(results) == 1
        assert isinstance(results[0], ParsedRow)
        assert results[0].data["source_id"] == "BOM-001"
