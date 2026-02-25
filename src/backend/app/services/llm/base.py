"""LLM Provider abstract base — SSOT-5 §1 Principle 11.

Defines:
- LLMRequest: structured request to any LLM provider
- LLMResponse: structured response with token usage tracking (§8-3a)
- LLMProvider: ABC that all providers must implement
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    """Structured request to an LLM provider.

    Attributes:
        system: System prompt (role instructions).
        messages: List of message dicts [{"role": "user", "content": "..."}].
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (0.0–1.0).
        metadata: Arbitrary metadata passed through to response.
    """

    system: str = ""
    messages: list[dict[str, str]] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    """Structured response from an LLM provider.

    Attributes:
        content: The text content of the LLM response.
        token_usage: Token counts {"input": N, "output": N} per §8-3a.
        model: Model identifier that actually served the request.
        stop_reason: Reason the model stopped generating.
        metadata: Pass-through from request + provider-specific extras.
    """

    content: str
    token_usage: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    model: str = ""
    stop_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed (input + output)."""
        return self.token_usage.get("input", 0) + self.token_usage.get("output", 0)


class LLMProvider(ABC):
    """Abstract base for LLM providers — SSOT-5 §1 Principle 11.

    Phase1 uses ClaudeProvider; can swap to other providers
    (OpenAI, local models) without changing callers.
    """

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request and return the response.

        Args:
            request: Structured LLM request.

        Returns:
            LLMResponse with content and token usage.

        Raises:
            httpx.TimeoutException: On timeout (will be retried by @llm_retry).
            httpx.ConnectError: On connection failure.
        """

    async def close(self) -> None:
        """Release provider resources (HTTP connections, etc.).

        Override if the provider holds stateful resources.
        Default is a no-op.
        """
