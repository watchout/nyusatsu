"""Tests for LLM mock/real provider switching (pre-check #3).

Verifies that the provider factory correctly switches based on
the LLM_PROVIDER environment variable.
"""

from unittest.mock import patch

import pytest

from app.services.llm import get_llm_provider
from app.services.llm.base import LLMRequest
from app.services.llm.mock import MockProvider


class TestLLMMockRealSwitch:
    def test_default_is_mock(self) -> None:
        """Default LLM_PROVIDER=mock returns MockProvider."""
        provider = get_llm_provider()
        assert isinstance(provider, MockProvider)

    def test_env_switch_to_claude(self) -> None:
        """LLM_PROVIDER=claude returns ClaudeProvider."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "claude"
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_MODEL = "claude-sonnet-4-20250514"
            mock_settings.LLM_API_TIMEOUT_SEC = 60
            provider = get_llm_provider()
            # Import here to avoid top-level import issues
            from app.services.llm.claude import ClaudeProvider

            assert isinstance(provider, ClaudeProvider)

    @pytest.mark.anyio
    async def test_mock_queue_response(self) -> None:
        """MockProvider.queue_response returns queued content."""
        provider = MockProvider()
        provider.queue_response(content="custom response")

        request = LLMRequest(
            system="test",
            messages=[{"role": "user", "content": "hello"}],
        )
        response = await provider.complete(request)
        assert response.content == "custom response"

    @pytest.mark.anyio
    async def test_mock_call_tracking(self) -> None:
        """MockProvider tracks all calls."""
        provider = MockProvider()
        request = LLMRequest(
            system="test",
            messages=[{"role": "user", "content": "hello"}],
        )
        await provider.complete(request)
        await provider.complete(request)

        assert provider.call_count == 2
        assert len(provider.calls) == 2
        assert provider.calls[0][0] is request
