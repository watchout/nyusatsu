"""Retry decorators using tenacity — SSOT-5 §3-4.

Three pre-configured decorators for different failure domains.
Each uses constants from core/constants.py.

Usage:
    @http_retry
    async def fetch_page(url: str) -> str: ...

    @llm_retry
    async def call_llm(prompt: str) -> dict: ...
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import httpx
import structlog
from sqlalchemy.exc import OperationalError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.core.constants import (
    DB_RETRY_BACKOFF_SEC,
    DB_RETRY_MAX,
    HTTP_RETRY_BACKOFF_SEC,
    HTTP_RETRY_MAX,
    LLM_RETRY_BACKOFF_SEC,
    LLM_RETRY_MAX,
)

logger = structlog.get_logger()


def _log_retry(retry_state: Any) -> None:
    """Log retry attempts at WARN level per SSOT-5 §11-4."""
    logger.warning(
        "retry_attempt",
        attempt=retry_state.attempt_number,
        outcome=str(retry_state.outcome),
    )


def _make_wait_from_backoff(backoff_sec: list[int]) -> Any:
    """Create a wait strategy from a backoff schedule.

    Uses the schedule values for the first N retries, then the last value.
    """
    def _wait(retry_state: Any) -> float:
        attempt = retry_state.attempt_number - 1  # 0-indexed
        if attempt < len(backoff_sec):
            return float(backoff_sec[attempt])
        return float(backoff_sec[-1])
    return _wait


# HTTP retry exceptions
_HTTP_RETRY_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ConnectTimeout,
)


def http_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for HTTP requests (F-001, F-005 scraping).

    Max 3 retries, backoff [30s, 60s, 120s].
    Retries on httpx timeout/connection errors.
    """
    @retry(
        stop=stop_after_attempt(HTTP_RETRY_MAX + 1),  # +1 because first attempt counts
        wait=_make_wait_from_backoff(HTTP_RETRY_BACKOFF_SEC),
        retry=retry_if_exception_type(_HTTP_RETRY_EXCEPTIONS),
        before_sleep=_log_retry,
        reraise=True,
    )
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)
    return wrapper


def llm_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for LLM API calls (F-002).

    Max 2 retries, backoff [10s, 30s].
    Retries on httpx timeout/connection errors.
    """
    @retry(
        stop=stop_after_attempt(LLM_RETRY_MAX + 1),
        wait=_make_wait_from_backoff(LLM_RETRY_BACKOFF_SEC),
        retry=retry_if_exception_type(_HTTP_RETRY_EXCEPTIONS),
        before_sleep=_log_retry,
        reraise=True,
    )
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)
    return wrapper


def db_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for DB connections.

    Max 3 retries, backoff [1s, 2s, 4s].
    Retries on SQLAlchemy OperationalError.
    """
    @retry(
        stop=stop_after_attempt(DB_RETRY_MAX + 1),
        wait=_make_wait_from_backoff(DB_RETRY_BACKOFF_SEC),
        retry=retry_if_exception_type(OperationalError),
        before_sleep=_log_retry,
        reraise=True,
    )
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)
    return wrapper
