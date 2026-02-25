"""Tests for TASK-12: LLM Circuit Breaker."""

from __future__ import annotations

from app.core.circuit_breaker import CircuitState, LLMCircuitBreaker


class TestLLMCircuitBreaker:
    """Validate circuit breaker behavior per SSOT-5 §3-4a."""

    def test_initial_state_closed(self):
        cb = LLMCircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_open is False
        assert cb.consecutive_failures == 0

    def test_opens_after_threshold_failures(self):
        """3 consecutive failures → state=OPEN (threshold=3)."""
        cb = LLMCircuitBreaker(threshold=3)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_open is True

    def test_success_resets_counter(self):
        """Success after 2 failures resets counter to 0."""
        cb = LLMCircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.consecutive_failures == 2
        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.state == CircuitState.CLOSED

    def test_open_remains_open_after_success(self):
        """Once OPEN, record_success resets counter but does NOT close."""
        cb = LLMCircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.is_open is True  # Still OPEN

    def test_reset_closes_circuit(self):
        """reset() returns to CLOSED state."""
        cb = LLMCircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_open is False
        assert cb.consecutive_failures == 0

    def test_custom_threshold(self):
        """Custom threshold=5 requires 5 failures to open."""
        cb = LLMCircuitBreaker(threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.is_open is False

        cb.record_failure()  # 5th failure
        assert cb.is_open is True

    def test_consecutive_failures_count(self):
        """consecutive_failures property tracks accurately."""
        cb = LLMCircuitBreaker()
        assert cb.consecutive_failures == 0
        cb.record_failure()
        assert cb.consecutive_failures == 1
        cb.record_failure()
        assert cb.consecutive_failures == 2
        cb.record_success()
        assert cb.consecutive_failures == 0
