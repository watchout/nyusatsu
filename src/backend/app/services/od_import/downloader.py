"""OD file downloader — F-005 Layer 1.

Downloads CSV (optionally ZIP-compressed) from the procurement portal,
verifies content via SHA-256 hash, and stores the raw file for audit.

Uses @http_retry for resilient downloads.
"""

from __future__ import annotations

import hashlib
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

import httpx
import structlog

from app.core.constants import HTTP_TIMEOUT_SEC
from app.core.retry import http_retry

logger = structlog.get_logger()


class DownloadResult(NamedTuple):
    """Result of downloading a file."""

    csv_text: str
    """Decoded CSV content (UTF-8)."""

    sha256: str
    """SHA-256 hex digest of the raw download bytes."""

    file_path: Path
    """Path where the raw file was saved."""

    size_bytes: int
    """Size of the downloaded content."""


class ODDownloader:
    """Download OD CSV files from the procurement portal.

    Supports:
    - Direct CSV download
    - ZIP containing a single CSV file
    - Raw file storage for audit trail

    Args:
        raw_dir: Directory for storing raw downloads.
    """

    def __init__(self, raw_dir: Path) -> None:
        self._raw_dir = raw_dir
        self._raw_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, url: str) -> DownloadResult:
        """Download and extract CSV from the given URL.

        Args:
            url: URL to the CSV or ZIP file.

        Returns:
            DownloadResult with CSV text, hash, and storage path.
        """
        raw_bytes = await self._fetch(url)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # Save raw file
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        suffix = ".zip" if self._is_zip(raw_bytes) else ".csv"
        filename = f"od_{ts}_{sha256[:8]}{suffix}"
        file_path = self._raw_dir / filename
        file_path.write_bytes(raw_bytes)

        # Extract CSV text
        csv_text = self._extract_csv_from_zip(raw_bytes) if self._is_zip(raw_bytes) else self._decode_csv(raw_bytes)

        logger.info(
            "od_download_complete",
            url=url,
            sha256=sha256,
            size_bytes=len(raw_bytes),
            file_path=str(file_path),
        )

        return DownloadResult(
            csv_text=csv_text,
            sha256=sha256,
            file_path=file_path,
            size_bytes=len(raw_bytes),
        )

    @http_retry
    async def _fetch(self, url: str) -> bytes:
        """HTTP GET with retry and timeout."""
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    @staticmethod
    def _is_zip(data: bytes) -> bool:
        """Check ZIP magic bytes."""
        return data[:4] == b"PK\x03\x04"

    @staticmethod
    def _extract_csv_from_zip(data: bytes) -> str:
        """Extract the first CSV file from a ZIP archive."""
        with zipfile.ZipFile(BytesIO(data)) as zf:
            csv_files = [
                n for n in zf.namelist()
                if n.lower().endswith(".csv") and not n.startswith("__MACOSX")
            ]
            if not csv_files:
                raise ValueError("No CSV file found in ZIP archive")

            raw_csv = zf.read(csv_files[0])
            # Try UTF-8 BOM first, then UTF-8, then Shift-JIS
            for encoding in ("utf-8-sig", "utf-8", "shift_jis"):
                try:
                    return raw_csv.decode(encoding)
                except (UnicodeDecodeError, ValueError):
                    continue
            raise ValueError("Could not decode CSV from ZIP")

    @staticmethod
    def _decode_csv(data: bytes) -> str:
        """Decode raw bytes to CSV text."""
        for encoding in ("utf-8-sig", "utf-8", "shift_jis"):
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, ValueError):
                continue
        raise ValueError("Could not decode CSV file")
