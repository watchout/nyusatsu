"""Document fetching for F-002 Stage 1.

Fetches notice HTML and spec PDF from URLs with retry logic.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.constants import HTTP_TIMEOUT_SEC
from app.core.retry import http_retry


@dataclass
class FetchResult:
    """Result of fetching a document."""

    content: bytes
    content_type: str
    url: str
    status_code: int


class DocumentFetcher:
    """Fetch notice HTML and spec PDF documents from URLs."""

    def __init__(self, *, timeout: float = HTTP_TIMEOUT_SEC) -> None:
        self._timeout = timeout

    @http_retry
    async def fetch_notice_html(self, notice_url: str) -> FetchResult:
        """Fetch notice HTML page.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses.
            httpx.TimeoutException: On timeout.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(notice_url)
            resp.raise_for_status()
            return FetchResult(
                content=resp.content,
                content_type=resp.headers.get("content-type", "text/html"),
                url=str(resp.url),
                status_code=resp.status_code,
            )

    @http_retry
    async def fetch_spec_pdf(self, spec_url: str | None) -> FetchResult | None:
        """Fetch spec PDF document.

        Returns None if spec_url is None.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses.
            httpx.TimeoutException: On timeout.
        """
        if spec_url is None:
            return None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(spec_url)
            resp.raise_for_status()
            return FetchResult(
                content=resp.content,
                content_type=resp.headers.get("content-type", "application/pdf"),
                url=str(resp.url),
                status_code=resp.status_code,
            )
