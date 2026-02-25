"""Tests for TASK-16: OD file downloader."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.od_import.downloader import ODDownloader


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """Temporary directory for raw file storage."""
    d = tmp_path / "raw" / "od"
    d.mkdir(parents=True)
    return d


def _make_csv_bytes(text: str = "col1,col2\na,b\n") -> bytes:
    return text.encode("utf-8")


def _make_zip_bytes(csv_text: str = "col1,col2\na,b\n") -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.csv", csv_text)
    return buf.getvalue()


class TestODDownloader:
    """Test OD file download and storage."""

    @pytest.mark.anyio
    async def test_download_csv(self, raw_dir: Path):
        """Direct CSV download → stored and decoded."""
        csv_bytes = _make_csv_bytes("id,name\n1,テスト\n")

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.content = csv_bytes
        mock_response.raise_for_status = lambda: None

        with patch(
            "app.services.od_import.downloader.ODDownloader._fetch",
            return_value=csv_bytes,
        ):
            dl = ODDownloader(raw_dir)
            result = await dl.download("https://example.go.jp/od.csv")

        assert "id,name" in result.csv_text
        assert "テスト" in result.csv_text
        assert len(result.sha256) == 64
        assert result.file_path.exists()
        assert result.size_bytes == len(csv_bytes)

    @pytest.mark.anyio
    async def test_download_zip(self, raw_dir: Path):
        """ZIP containing CSV → extracted and decoded."""
        csv_content = "id,name\n1,ZIPテスト\n"
        zip_bytes = _make_zip_bytes(csv_content)

        with patch(
            "app.services.od_import.downloader.ODDownloader._fetch",
            return_value=zip_bytes,
        ):
            dl = ODDownloader(raw_dir)
            result = await dl.download("https://example.go.jp/od.zip")

        assert "ZIPテスト" in result.csv_text
        assert result.file_path.suffix == ".zip"

    @pytest.mark.anyio
    async def test_download_stores_raw_file(self, raw_dir: Path):
        """Raw file is saved to the configured directory."""
        csv_bytes = _make_csv_bytes()

        with patch(
            "app.services.od_import.downloader.ODDownloader._fetch",
            return_value=csv_bytes,
        ):
            dl = ODDownloader(raw_dir)
            result = await dl.download("https://example.go.jp/od.csv")

        assert result.file_path.parent == raw_dir
        assert result.file_path.read_bytes() == csv_bytes

    @pytest.mark.anyio
    async def test_download_sha256_consistency(self, raw_dir: Path):
        """Same content → same SHA-256."""
        csv_bytes = _make_csv_bytes("consistent\n")

        with patch(
            "app.services.od_import.downloader.ODDownloader._fetch",
            return_value=csv_bytes,
        ):
            dl = ODDownloader(raw_dir)
            r1 = await dl.download("https://example.go.jp/od.csv")
            r2 = await dl.download("https://example.go.jp/od.csv")

        assert r1.sha256 == r2.sha256
