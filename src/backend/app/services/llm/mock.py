"""Mock LLM provider for testing — no external API calls.

Records all calls for assertion and returns configurable responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse


@dataclass
class MockProvider(LLMProvider):
    """Mock provider that returns canned responses.

    Attributes:
        default_content: Content to return when no custom responses queued.
        default_token_usage: Token usage to return by default.
        calls: List of (request, response) tuples for assertions.
        responses: Queue of custom LLMResponse objects. FIFO — pops from front.
    """

    default_content: str = "mock response"
    default_token_usage: dict[str, int] = field(
        default_factory=lambda: {"input": 100, "output": 50},
    )
    calls: list[tuple[LLMRequest, LLMResponse]] = field(default_factory=list)
    responses: list[LLMResponse] = field(default_factory=list)
    _closed: bool = field(default=False, repr=False)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Return queued response or default mock response."""
        if self.responses:
            response = self.responses.pop(0)
        else:
            response = LLMResponse(
                content=self.default_content,
                token_usage=dict(self.default_token_usage),
                model="mock-model",
                stop_reason="end_turn",
                metadata=request.metadata,
            )

        self.calls.append((request, response))
        return response

    async def close(self) -> None:
        """Mark provider as closed."""
        self._closed = True

    @property
    def is_closed(self) -> bool:
        """Whether close() has been called."""
        return self._closed

    @property
    def call_count(self) -> int:
        """Number of complete() calls made."""
        return len(self.calls)

    def queue_response(
        self,
        content: str = "queued response",
        *,
        token_usage: dict[str, int] | None = None,
        model: str = "mock-model",
        stop_reason: str = "end_turn",
    ) -> None:
        """Add a custom response to the FIFO queue."""
        self.responses.append(
            LLMResponse(
                content=content,
                token_usage=token_usage or {"input": 100, "output": 50},
                model=model,
                stop_reason=stop_reason,
            ),
        )

    def queue_error(self, exc: Exception) -> None:
        """Queue an exception to be raised on next complete() call.

        This replaces the response queue with a sentinel that raises.
        Use for testing error paths.
        """
        self._pending_error = exc

    async def complete_or_raise(self, request: LLMRequest) -> LLMResponse:
        """Like complete(), but raises queued errors."""
        if hasattr(self, "_pending_error") and self._pending_error is not None:
            err = self._pending_error
            self._pending_error = None
            raise err
        return await self.complete(request)
