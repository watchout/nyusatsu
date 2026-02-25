"""LLM abstraction layer — SSOT-5 §1 Principle 11.

Phase1: Claude API via anthropic SDK.
Provider is swappable without changing caller code.

Switch via environment variable:
    LLM_PROVIDER=claude  → ClaudeProvider (requires LLM_API_KEY)
    LLM_PROVIDER=mock    → MockProvider (default, no API calls)
"""

from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse


def get_llm_provider() -> LLMProvider:
    """Factory: return the configured LLM provider.

    Reads ``settings.LLM_PROVIDER`` (env ``LLM_PROVIDER``).
    Default is ``"mock"`` so tests/dev never hit real API.
    """
    from app.core.config import settings

    if settings.LLM_PROVIDER == "claude":
        from app.services.llm.claude import ClaudeProvider

        return ClaudeProvider()

    from app.services.llm.mock import MockProvider

    return MockProvider()


__all__ = ["LLMProvider", "LLMRequest", "LLMResponse", "get_llm_provider"]
