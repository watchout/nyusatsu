"""Tests for DocumentFetcher (F-002 Stage 1).

We patch httpx.AsyncClient to avoid real network calls.
The @http_retry decorator is tested separately in test_retry.py;
here we test the fetcher logic by patching tenacity to skip retries.
"""

from unittest.mock import AsyncMock, patch

import pytest
import httpx

from app.services.reading.document_fetcher import DocumentFetcher, FetchResult


def _mock_client(mock_resp=None, side_effect=None):
    """Create a mock AsyncClient context manager."""
    mock_client = AsyncMock()
    if side_effect:
        mock_client.get.side_effect = side_effect
    else:
        mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.anyio
class TestDocumentFetcher:
    async def test_fetch_html_success(self) -> None:
        url = "https://example.com/notice.html"
        resp = httpx.Response(
            200,
            content=b"<html><body>OK</body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )
        with patch("app.services.reading.document_fetcher.httpx.AsyncClient") as cls:
            cls.return_value = _mock_client(mock_resp=resp)
            fetcher = DocumentFetcher()
            result = await fetcher.fetch_notice_html(url)

        assert isinstance(result, FetchResult)
        assert result.status_code == 200
        assert b"OK" in result.content

    async def test_fetch_html_404(self) -> None:
        url = "https://example.com/missing.html"
        resp = httpx.Response(404, request=httpx.Request("GET", url))
        with patch("app.services.reading.document_fetcher.httpx.AsyncClient") as cls:
            cls.return_value = _mock_client(mock_resp=resp)
            fetcher = DocumentFetcher()
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch_notice_html(url)

    async def test_fetch_pdf_success(self) -> None:
        url = "https://example.com/spec.pdf"
        pdf_content = b"%PDF-1.4 fake content"
        resp = httpx.Response(
            200,
            content=pdf_content,
            headers={"content-type": "application/pdf"},
            request=httpx.Request("GET", url),
        )
        with patch("app.services.reading.document_fetcher.httpx.AsyncClient") as cls:
            cls.return_value = _mock_client(mock_resp=resp)
            fetcher = DocumentFetcher()
            result = await fetcher.fetch_spec_pdf(url)

        assert result is not None
        assert result.content == pdf_content

    async def test_fetch_pdf_spec_url_none(self) -> None:
        fetcher = DocumentFetcher()
        result = await fetcher.fetch_spec_pdf(None)
        assert result is None

    async def test_fetch_pdf_timeout(self) -> None:
        """Timeout propagates (tenacity retries, then re-raises).

        We patch asyncio.sleep to zero so the test completes fast.
        Async tenacity uses asyncio.sleep, not tenacity.nap.time.
        """
        url = "https://example.com/slow.pdf"

        async def _instant_sleep(_: float) -> None:
            pass

        with (
            patch("app.services.reading.document_fetcher.httpx.AsyncClient") as cls,
            patch("asyncio.sleep", new=_instant_sleep),
        ):
            cls.return_value = _mock_client(
                side_effect=httpx.ReadTimeout("timeout"),
            )
            fetcher = DocumentFetcher()
            with pytest.raises(httpx.ReadTimeout):
                await fetcher.fetch_spec_pdf(url)
