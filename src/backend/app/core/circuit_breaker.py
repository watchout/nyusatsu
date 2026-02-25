"""LLM Circuit Breaker — SSOT-5 §3-4a.

Tracks consecutive LLM failures within a batch/cascade run.
When threshold is reached, enters OPEN state and rejects further calls.

Per-batch instance: create a new LLMCircuitBreaker per batch run.
SSOT-5 §3-4a: "next batch auto-reset" = new instance.
"""

from __future__ import annotations

import structlog

from app.core.constants import LLM_CIRCUIT_BREAKER_THRESHOLD

logger = structlog.get_logger()


class CircuitState:
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Threshold exceeded, rejecting calls


class LLMCircuitBreaker:
    """Per-batch circuit breaker for LLM API calls.

    Usage:
        cb = LLMCircuitBreaker()   # New instance per batch
        if cb.is_open:
            skip_llm_call()
        try:
            result = await llm_call()
            cb.record_success()
        except LLMError:
            cb.record_failure()
    """

    def __init__(
        self, threshold: int = LLM_CIRCUIT_BREAKER_THRESHOLD,
    ) -> None:
        self._threshold = threshold
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> str:
        """Current circuit breaker state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Whether the circuit breaker is in OPEN state."""
        return self._state == CircuitState.OPEN

    @property
    def consecutive_failures(self) -> int:
        """Number of consecutive failures recorded."""
        return self._consecutive_failures

    def record_success(self) -> None:
        """Reset consecutive failure counter on success.

        Note: Does NOT auto-recover from OPEN state.
        Use reset() for that.
        """
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Increment failure counter. Open circuit if threshold reached."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            self._state = CircuitState.OPEN
            logger.error(
                "llm_circuit_breaker_open",
                consecutive_failures=self._consecutive_failures,
                threshold=self._threshold,
            )

    def reset(self) -> None:
        """Manual reset — return to CLOSED state."""
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED
