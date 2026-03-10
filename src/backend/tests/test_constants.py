"""Tests for TASK-15: Constants management.

Validates all 31 constants from SSOT-5 §12-2 are defined with correct
types and values.
"""

from __future__ import annotations

from app.core import constants

# All 31 constant names from SSOT-5 §12-2
EXPECTED_CONSTANTS = [
    # HTTP / Scraping (3)
    "HTTP_TIMEOUT_SEC",
    "PDF_DOWNLOAD_TIMEOUT_SEC",
    "SCRAPE_RATE_LIMIT_SEC",
    # LLM (5 + 1 from env)
    "LLM_API_TIMEOUT_SEC",
    "LLM_RETRY_MAX",
    "LLM_RETRY_BACKOFF_SEC",
    "LLM_PARSE_RETRY_MAX",
    "LLM_CIRCUIT_BREAKER_THRESHOLD",
    "LLM_DAILY_TOKEN_LIMIT",
    # DB (3)
    "DB_CONNECT_TIMEOUT_SEC",
    "DB_RETRY_MAX",
    "DB_RETRY_BACKOFF_SEC",
    # HTTP Retry (2)
    "HTTP_RETRY_MAX",
    "HTTP_RETRY_BACKOFF_SEC",
    # Stuck Detection (4)
    "READING_STUCK_TIMEOUT_MIN",
    "READING_STUCK_TIMEOUT_SCANNED_MIN",
    "JUDGING_STUCK_TIMEOUT_MIN",
    "CHECKLIST_STUCK_TIMEOUT_MIN",
    # Batch (4)
    "BATCH_CASE_FETCH_TIMEOUT_MIN",
    "BATCH_OD_IMPORT_TIMEOUT_MIN",
    "BATCH_DETAIL_SCRAPE_TIMEOUT_MIN",
    "CASCADE_FAILURE_THRESHOLD",
    # AI Quality (5)
    "CONFIDENCE_THRESHOLD",
    "SCANNED_PDF_CHAR_THRESHOLD",
    "CHUNK_SPLIT_TOKEN_THRESHOLD",
    "EVIDENCE_MATCH_STRONG",
    "EVIDENCE_MATCH_CANDIDATE",
    # Schedule (3)
    "SCHEDULE_REVERSE_START_BD",
    "SCHEDULE_REVERSE_REVIEW_BD",
    "SCHEDULE_REVERSE_FINALIZE_BD",
    # Frontend (1)
    "POLLING_INTERVAL_SEC",
]


class TestConstants:
    """Verify constants match SSOT-5 §12-2."""

    def test_all_31_constants_defined(self):
        """All 31 constants must exist in the constants module."""
        for name in EXPECTED_CONSTANTS:
            assert hasattr(constants, name), f"Missing constant: {name}"
        assert len(EXPECTED_CONSTANTS) == 31

    def test_constant_types(self):
        """Each constant has correct type."""
        # int constants
        int_names = [
            "HTTP_TIMEOUT_SEC", "PDF_DOWNLOAD_TIMEOUT_SEC",
            "LLM_API_TIMEOUT_SEC", "LLM_RETRY_MAX", "LLM_PARSE_RETRY_MAX",
            "LLM_CIRCUIT_BREAKER_THRESHOLD", "LLM_DAILY_TOKEN_LIMIT",
            "DB_CONNECT_TIMEOUT_SEC", "DB_RETRY_MAX",
            "HTTP_RETRY_MAX",
            "READING_STUCK_TIMEOUT_MIN", "READING_STUCK_TIMEOUT_SCANNED_MIN",
            "JUDGING_STUCK_TIMEOUT_MIN", "CHECKLIST_STUCK_TIMEOUT_MIN",
            "BATCH_CASE_FETCH_TIMEOUT_MIN", "BATCH_OD_IMPORT_TIMEOUT_MIN",
            "BATCH_DETAIL_SCRAPE_TIMEOUT_MIN", "CASCADE_FAILURE_THRESHOLD",
            "SCANNED_PDF_CHAR_THRESHOLD", "CHUNK_SPLIT_TOKEN_THRESHOLD",
            "SCHEDULE_REVERSE_START_BD", "SCHEDULE_REVERSE_REVIEW_BD",
            "SCHEDULE_REVERSE_FINALIZE_BD",
            "POLLING_INTERVAL_SEC",
        ]
        for name in int_names:
            assert isinstance(getattr(constants, name), int), f"{name} should be int"

        # float constants
        float_names = [
            "SCRAPE_RATE_LIMIT_SEC",
            "CONFIDENCE_THRESHOLD",
            "EVIDENCE_MATCH_STRONG", "EVIDENCE_MATCH_CANDIDATE",
        ]
        for name in float_names:
            assert isinstance(getattr(constants, name), float), f"{name} should be float"

        # list constants
        list_names = [
            "LLM_RETRY_BACKOFF_SEC", "DB_RETRY_BACKOFF_SEC",
            "HTTP_RETRY_BACKOFF_SEC",
        ]
        for name in list_names:
            val = getattr(constants, name)
            assert isinstance(val, list), f"{name} should be list"
            assert all(isinstance(x, int) for x in val), f"{name} items should be int"

    def test_retry_backoff_lengths(self):
        """Backoff arrays have correct number of elements per SSOT-5 §12-2."""
        assert len(constants.HTTP_RETRY_BACKOFF_SEC) == 3
        assert len(constants.LLM_RETRY_BACKOFF_SEC) == 2
        assert len(constants.DB_RETRY_BACKOFF_SEC) == 3

    def test_no_negative_timeouts(self):
        """All timeout/threshold values are positive (except schedule offsets)."""
        positive_names = [
            "HTTP_TIMEOUT_SEC", "PDF_DOWNLOAD_TIMEOUT_SEC",
            "LLM_API_TIMEOUT_SEC", "DB_CONNECT_TIMEOUT_SEC",
            "READING_STUCK_TIMEOUT_MIN", "READING_STUCK_TIMEOUT_SCANNED_MIN",
            "JUDGING_STUCK_TIMEOUT_MIN", "CHECKLIST_STUCK_TIMEOUT_MIN",
            "BATCH_CASE_FETCH_TIMEOUT_MIN", "BATCH_OD_IMPORT_TIMEOUT_MIN",
            "BATCH_DETAIL_SCRAPE_TIMEOUT_MIN",
            "CONFIDENCE_THRESHOLD", "SCRAPE_RATE_LIMIT_SEC",
            "EVIDENCE_MATCH_STRONG", "EVIDENCE_MATCH_CANDIDATE",
            "POLLING_INTERVAL_SEC",
        ]
        for name in positive_names:
            assert getattr(constants, name) > 0, f"{name} must be positive"

    def test_constants_match_ssot5_spot_check(self):
        """Spot-check key values against SSOT-5 §12-2."""
        assert constants.HTTP_TIMEOUT_SEC == 30
        assert constants.PDF_DOWNLOAD_TIMEOUT_SEC == 60
        assert constants.LLM_API_TIMEOUT_SEC == 60
        assert constants.LLM_RETRY_MAX == 2
        assert constants.HTTP_RETRY_MAX == 3
        assert constants.DB_RETRY_MAX == 3
        assert constants.CONFIDENCE_THRESHOLD == 0.6
        assert constants.LLM_CIRCUIT_BREAKER_THRESHOLD == 3
        assert constants.BATCH_CASE_FETCH_TIMEOUT_MIN == 30
        assert constants.SCHEDULE_REVERSE_START_BD == -5

    def test_llm_daily_token_limit_from_settings(self):
        """LLM_DAILY_TOKEN_LIMIT matches settings value (overridable)."""
        from app.core.config import settings
        assert constants.LLM_DAILY_TOKEN_LIMIT == settings.LLM_DAILY_TOKEN_LIMIT
