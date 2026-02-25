"""Tests for FileStore (F-002 Stage 1)."""

import pytest
from uuid import uuid4

from app.services.reading.file_store import FileStore


class TestFileStore:
    def test_compute_hash_deterministic(self) -> None:
        store = FileStore()
        content = b"test content for hashing"
        h1 = store.compute_hash(content)
        h2 = store.compute_hash(content)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_compute_hash_different_content(self) -> None:
        store = FileStore()
        h1 = store.compute_hash(b"content A")
        h2 = store.compute_hash(b"content B")
        assert h1 != h2

    @pytest.mark.anyio
    async def test_save_and_verify(self, tmp_path) -> None:
        store = FileStore(base_dir=tmp_path / "raw")
        case_id = uuid4()
        html = b"<html>test</html>"

        path = await store.save_notice(case_id, html)
        assert path.exists()
        assert path.read_bytes() == html
        assert str(case_id) in str(path)
