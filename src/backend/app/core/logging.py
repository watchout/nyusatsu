"""Structured JSON logging configuration (SSOT-5 §11, TASK-49).

All logs are output as structured JSON with these mandatory fields:
- timestamp (ISO8601 UTC)
- level (DEBUG/INFO/WARN/ERROR)
- logger (module path)
- message

Optional context fields (bound per-request or per-batch):
- case_id, feature_origin, batch_log_id, trace_id, duration_ms

Usage:
    from app.core.logging import configure_logging, get_logger

    configure_logging()  # Called once at app startup
    logger = get_logger()
    logger.info("something_happened", case_id="...", feature_origin="F-002")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog
import structlog.contextvars

from app.core.config import settings


def _add_logger_name(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Add 'logger' field with the structlog logger name."""
    if "logger" not in event_dict:
        event_dict["logger"] = event_dict.get("_logger_name", "app")
    return event_dict


def _filter_by_level(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Filter log events below configured log level."""
    level_map = {"DEBUG": 10, "INFO": 20, "WARN": 30, "WARNING": 30, "ERROR": 40}
    configured_level = level_map.get(settings.APP_LOG_LEVEL, 20)
    event_level = level_map.get(event_dict.get("level", "INFO").upper(), 20)

    if event_level < configured_level:
        raise structlog.DropEvent

    return event_dict


def configure_logging() -> None:
    """Configure structlog for structured JSON output.

    - Development: colored console output + JSON file
    - Production: JSON file only
    """
    # Ensure log directory exists
    log_dir = Path(settings.APP_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Shared processors (SSOT-5 §11-1, §11-2)
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_logger_name,
        _filter_by_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.APP_ENV == "development":
        # Dev: pretty console + JSON file
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Production: JSON to stdout (and optionally file)
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.JSONRenderer(
                    ensure_ascii=False,
                    sort_keys=False,
                ),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.APP_LOG_LEVEL, logging.INFO),
    )


def get_logger(**initial_values: object) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger with optional initial context values.

    Example:
        logger = get_logger(feature_origin="F-002")
        logger.info("processing_started", case_id="abc")
    """
    return structlog.get_logger(**initial_values)


def bind_context(**kwargs: object) -> None:
    """Bind context variables for the current async task.

    These values will be included in all subsequent log entries
    until explicitly unbound.

    Example:
        bind_context(case_id="abc", batch_log_id="xyz")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """Remove context variables.

    Example:
        unbind_context("case_id", "batch_log_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
