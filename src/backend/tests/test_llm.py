"""Tests for TASK-13: LLM abstraction layer.

Tests use MockProvider (no external API calls).
ClaudeProvider integration is skipped unless LLM_API_KEY is set.
"""

from __future__ import annotations

import pytest

from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse
from app.services.llm.mock import MockProvider


class TestLLMRequest:
    """LLMRequest dataclass validation."""

    def test_default_values(self):
        req = LLMRequest()
        assert req.system == ""
        assert req.messages == []
        assert req.max_tokens == 4096
        assert req.temperature == 0.0
        assert req.metadata == {}

    def test_custom_request(self):
        req = LLMRequest(
            system="You are an expert.",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1024,
            temperature=0.5,
            metadata={"case_id": "abc"},
        )
        assert req.system == "You are an expert."
        assert len(req.messages) == 1
        assert req.max_tokens == 1024
        assert req.temperature == 0.5
        assert req.metadata["case_id"] == "abc"


class TestLLMResponse:
    """LLMResponse dataclass validation."""

    def test_total_tokens(self):
        resp = LLMResponse(
            content="test",
            token_usage={"input": 200, "output": 100},
        )
        assert resp.total_tokens == 300

    def test_total_tokens_default(self):
        resp = LLMResponse(content="test")
        assert resp.total_tokens == 0

    def test_frozen_immutability(self):
        resp = LLMResponse(content="test")
        with pytest.raises(AttributeError):
            resp.content = "changed"  # type: ignore[misc]


class TestMockProvider:
    """MockProvider unit tests."""

    @pytest.mark.anyio
    async def test_implements_llm_provider(self):
        """MockProvider is a valid LLMProvider."""
        provider = MockProvider()
        assert isinstance(provider, LLMProvider)

    @pytest.mark.anyio
    async def test_default_response(self):
        """Returns default content when no custom responses queued."""
        provider = MockProvider(default_content="default reply")
        req = LLMRequest(messages=[{"role": "user", "content": "Hi"}])

        resp = await provider.complete(req)

        assert resp.content == "default reply"
        assert resp.model == "mock-model"
        assert resp.stop_reason == "end_turn"
        assert resp.token_usage == {"input": 100, "output": 50}

    @pytest.mark.anyio
    async def test_call_tracking(self):
        """Calls are recorded for assertion."""
        provider = MockProvider()
        req = LLMRequest(messages=[{"role": "user", "content": "Hi"}])

        await provider.complete(req)
        await provider.complete(req)

        assert provider.call_count == 2
        assert provider.calls[0][0] is req
        assert isinstance(provider.calls[0][1], LLMResponse)

    @pytest.mark.anyio
    async def test_queued_responses_fifo(self):
        """Custom responses are returned in FIFO order."""
        provider = MockProvider()
        provider.queue_response(content="first")
        provider.queue_response(content="second")

        req = LLMRequest(messages=[{"role": "user", "content": "Hi"}])

        resp1 = await provider.complete(req)
        resp2 = await provider.complete(req)
        resp3 = await provider.complete(req)  # Falls back to default

        assert resp1.content == "first"
        assert resp2.content == "second"
        assert resp3.content == "mock response"  # default

    @pytest.mark.anyio
    async def test_metadata_passthrough(self):
        """Request metadata is passed through to response."""
        provider = MockProvider()
        req = LLMRequest(
            messages=[{"role": "user", "content": "Hi"}],
            metadata={"case_id": "test-123"},
        )

        resp = await provider.complete(req)
        assert resp.metadata == {"case_id": "test-123"}

    @pytest.mark.anyio
    async def test_close(self):
        """close() marks provider as closed."""
        provider = MockProvider()
        assert provider.is_closed is False

        await provider.close()
        assert provider.is_closed is True

    @pytest.mark.anyio
    async def test_custom_token_usage(self):
        """Queued response with custom token usage."""
        provider = MockProvider()
        provider.queue_response(
            content="expensive",
            token_usage={"input": 5000, "output": 2000},
        )

        req = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        resp = await provider.complete(req)

        assert resp.token_usage["input"] == 5000
        assert resp.token_usage["output"] == 2000
        assert resp.total_tokens == 7000


class TestClaudeProviderImport:
    """Verify ClaudeProvider can be imported and instantiated."""

    def test_import_claude_provider(self):
        """ClaudeProvider class is importable."""
        from app.services.llm.claude import ClaudeProvider

        assert issubclass(ClaudeProvider, LLMProvider)

    def test_instantiation_with_dummy_key(self):
        """ClaudeProvider can be created with a dummy API key."""
        from app.services.llm.claude import ClaudeProvider

        provider = ClaudeProvider(api_key="sk-ant-test-dummy")
        assert provider._model == "claude-sonnet-4-20250514"
        assert provider._default_max_tokens == 4096


class TestGetLLMProviderFactory:
    """Test get_llm_provider() factory (Wave 0 Item 0-3)."""

    def test_factory_returns_mock_by_default(self, monkeypatch):
        """Default LLM_PROVIDER='mock' returns MockProvider."""
        monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "mock")
        from app.services.llm import get_llm_provider

        provider = get_llm_provider()
        assert isinstance(provider, MockProvider)

    def test_factory_returns_claude_when_configured(self, monkeypatch):
        """LLM_PROVIDER='claude' returns ClaudeProvider."""
        monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "claude")
        monkeypatch.setattr("app.core.config.settings.LLM_API_KEY", "sk-test")
        from app.services.llm import get_llm_provider
        from app.services.llm.claude import ClaudeProvider

        provider = get_llm_provider()
        assert isinstance(provider, ClaudeProvider)
