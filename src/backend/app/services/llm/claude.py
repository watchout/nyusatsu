"""Claude API provider — SSOT-5 §12-1.

Uses the official anthropic SDK (AsyncAnthropic) with @llm_retry.
Reads configuration from core/config.py:
  - LLM_API_KEY
  - LLM_MODEL
  - LLM_MAX_TOKENS
"""

from __future__ import annotations

import structlog
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.core.constants import LLM_API_TIMEOUT_SEC
from app.core.retry import llm_retry
from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse

logger = structlog.get_logger()


class ClaudeProvider(LLMProvider):
    """Claude API provider via anthropic SDK.

    Instantiate once and reuse; call close() when done.

    Example::

        provider = ClaudeProvider()
        try:
            resp = await provider.complete(LLMRequest(
                system="You are an expert on government bids.",
                messages=[{"role": "user", "content": "Summarize this document."}],
            ))
            print(resp.content)
        finally:
            await provider.close()
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._api_key = api_key or settings.LLM_API_KEY
        self._model = model or settings.LLM_MODEL
        self._default_max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self._timeout = timeout or float(LLM_API_TIMEOUT_SEC)

        self._client = AsyncAnthropic(
            api_key=self._api_key,
            timeout=self._timeout,
        )

    @llm_retry
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send completion request to Claude API.

        Decorated with @llm_retry (max 2 retries, backoff [10s, 30s]).
        """
        max_tokens = request.max_tokens or self._default_max_tokens

        logger.debug(
            "llm_request",
            model=self._model,
            max_tokens=max_tokens,
            message_count=len(request.messages),
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=request.system or "",
            messages=request.messages,
            temperature=request.temperature,
        )

        # Extract content text (Claude returns list of content blocks)
        content_text = ""
        for block in response.content:
            if block.type == "text":
                content_text += block.text

        # Token usage per §8-3a
        token_usage = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }

        logger.info(
            "llm_response",
            model=response.model,
            input_tokens=token_usage["input"],
            output_tokens=token_usage["output"],
            stop_reason=response.stop_reason,
        )

        return LLMResponse(
            content=content_text,
            token_usage=token_usage,
            model=response.model,
            stop_reason=response.stop_reason or "",
            metadata=request.metadata,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()
