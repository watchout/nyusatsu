"""Tests for TASK-12: Retry decorators."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.core.retry import db_retry, http_retry, llm_retry


@pytest.fixture(autouse=True)
def _fast_retry(monkeypatch):
    """Replace backoff schedules with zero-wait for fast tests.

    Each decorator reads module-level constants when applied inside test
    methods, so monkeypatch takes effect before @http_retry etc. execute.
    """
    monkeypatch.setattr("app.core.retry.HTTP_RETRY_BACKOFF_SEC", [0, 0, 0])
    monkeypatch.setattr("app.core.retry.LLM_RETRY_BACKOFF_SEC", [0, 0])
    monkeypatch.setattr("app.core.retry.DB_RETRY_BACKOFF_SEC", [0, 0, 0])


class TestHttpRetry:
    """Test http_retry decorator."""

    @pytest.mark.anyio
    async def test_succeeds_on_first_attempt(self):
        call_count = 0

        @http_retry
        async def _always_ok():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await _always_ok()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.anyio
    async def test_retries_on_timeout(self):
        call_count = 0

        @http_retry
        async def _fail_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("timeout")
            return "ok"

        result = await _fail_then_ok()
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.anyio
    async def test_raises_after_max_retries(self):
        call_count = 0

        @http_retry
        async def _always_fail():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("timeout")

        with pytest.raises(httpx.TimeoutException):
            await _always_fail()
        # HTTP_RETRY_MAX=3, so 3+1=4 total attempts
        assert call_count == 4

    @pytest.mark.anyio
    async def test_does_not_retry_unexpected_errors(self):
        call_count = 0

        @http_retry
        async def _value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await _value_error()
        assert call_count == 1  # No retry


class TestLlmRetry:
    """Test llm_retry decorator."""

    @pytest.mark.anyio
    async def test_retries_on_timeout(self):
        call_count = 0

        @llm_retry
        async def _fail_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("timeout")
            return "ok"

        result = await _fail_then_ok()
        assert result == "ok"
        assert call_count == 2


class TestDbRetry:
    """Test db_retry decorator."""

    @pytest.mark.anyio
    async def test_retries_on_operational_error(self):
        call_count = 0

        @db_retry
        async def _fail_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("test", {}, Exception("conn lost"))
            return "ok"

        result = await _fail_then_ok()
        assert result == "ok"
        assert call_count == 2
