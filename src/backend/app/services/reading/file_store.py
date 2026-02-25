"""Raw file storage for F-002 Stage 1.

Saves raw notice HTML and spec PDF to local storage for audit trail.
Computes SHA-256 hashes for cache deduplication.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID


class FileStore:
    """Save and retrieve raw documents."""

    def __init__(self, base_dir: str | Path = "data/raw/reading") -> None:
        self._base_dir = Path(base_dir)

    async def save_notice(self, case_id: UUID, html: bytes) -> Path:
        """Save raw notice HTML."""
        return self._write(case_id, "notice.html", html)

    async def save_spec(self, case_id: UUID, pdf: bytes) -> Path:
        """Save raw spec PDF."""
        return self._write(case_id, "spec.pdf", pdf)

    async def save_text(self, case_id: UUID, text: str) -> Path:
        """Save extracted text."""
        return self._write(case_id, "extracted.txt", text.encode("utf-8"))

    def compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hex digest of content."""
        return hashlib.sha256(content).hexdigest()

    def _write(self, case_id: UUID, filename: str, data: bytes) -> Path:
        """Write data to case-specific directory."""
        case_dir = self._base_dir / str(case_id)
        case_dir.mkdir(parents=True, exist_ok=True)
        path = case_dir / filename
        path.write_bytes(data)
        return path
