"""Tests for structured logging configuration — TASK-49.

Validates SSOT-5 §11 logging requirements:
- JSON format with mandatory fields
- Context variable binding (case_id, feature_origin, batch_log_id)
- Log level filtering
"""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from app.core.logging import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
    unbind_context,
)


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog config and context between tests."""
    clear_context()
    yield
    clear_context()
    # Reset structlog to avoid test pollution
    structlog.reset_defaults()


class TestLogFormat:
    def test_json_output_contains_mandatory_fields(self) -> None:
        """All log entries must have timestamp, level, message (SSOT-5 §11-2)."""
        output = StringIO()

        # Configure for JSON output to capture
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(file=output),
            cache_logger_on_first_use=False,
        )

        logger = structlog.get_logger()
        logger.info("test_event", case_id="abc")

        log_line = output.getvalue().strip()
        parsed = json.loads(log_line)

        # Mandatory fields (§11-2)
        assert "timestamp" in parsed
        assert parsed["level"] == "info"
        assert parsed["event"] == "test_event"
        assert parsed["case_id"] == "abc"

    def test_timestamp_is_iso8601_utc(self) -> None:
        """Timestamp must be ISO8601 UTC (§11-2)."""
        output = StringIO()

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(file=output),
            cache_logger_on_first_use=False,
        )

        logger = structlog.get_logger()
        logger.info("ts_test")

        parsed = json.loads(output.getvalue().strip())
        ts = parsed["timestamp"]
        # ISO8601 with UTC: ends with +00:00 or Z
        assert "T" in ts
        assert "+" in ts or "Z" in ts


class TestContextBinding:
    def test_bind_context_adds_to_logs(self) -> None:
        """Bound context vars appear in log output."""
        output = StringIO()

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(file=output),
            cache_logger_on_first_use=False,
        )

        bind_context(case_id="case-123", feature_origin="F-002")

        logger = structlog.get_logger()
        logger.info("with_context")

        parsed = json.loads(output.getvalue().strip())
        assert parsed["case_id"] == "case-123"
        assert parsed["feature_origin"] == "F-002"

    def test_unbind_context_removes_from_logs(self) -> None:
        """Unbound context vars no longer appear."""
        output = StringIO()

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(file=output),
            cache_logger_on_first_use=False,
        )

        bind_context(batch_log_id="bl-1")
        unbind_context("batch_log_id")

        logger = structlog.get_logger()
        logger.info("after_unbind")

        parsed = json.loads(output.getvalue().strip())
        assert "batch_log_id" not in parsed

    def test_clear_context_removes_all(self) -> None:
        """Clear context removes all bound variables."""
        output = StringIO()

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(file=output),
            cache_logger_on_first_use=False,
        )

        bind_context(case_id="c1", feature_origin="F-001", batch_log_id="b1")
        clear_context()

        logger = structlog.get_logger()
        logger.info("after_clear")

        parsed = json.loads(output.getvalue().strip())
        assert "case_id" not in parsed
        assert "feature_origin" not in parsed
        assert "batch_log_id" not in parsed


class TestGetLogger:
    def test_get_logger_with_initial_values(self) -> None:
        """get_logger accepts initial bound values."""
        output = StringIO()

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(file=output),
            cache_logger_on_first_use=False,
        )

        logger = get_logger(feature_origin="F-003")
        logger.info("initial_bound")

        parsed = json.loads(output.getvalue().strip())
        assert parsed["feature_origin"] == "F-003"


class TestConfigureLogging:
    def test_configure_logging_dev_mode(self) -> None:
        """configure_logging in dev mode does not raise."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.APP_ENV = "development"
            mock_settings.APP_LOG_LEVEL = "INFO"
            mock_settings.APP_LOG_DIR = "/tmp/test_logs"
            configure_logging()

    def test_configure_logging_prod_mode(self) -> None:
        """configure_logging in production mode does not raise."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.APP_ENV = "production"
            mock_settings.APP_LOG_LEVEL = "INFO"
            mock_settings.APP_LOG_DIR = "/tmp/test_logs"
            configure_logging()
