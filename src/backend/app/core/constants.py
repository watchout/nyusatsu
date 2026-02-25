"""Application constants — SSOT-5 §12-2.

All 31 constants from the SSOT-5 §12-2 constant table.
Constants that need environment override read from config.settings.
All others are compile-time constants.

**ルール**: 新規モジュールは全て ``from app.core.constants import XXX`` で定数を
参照すること。マジックナンバーの直書き禁止。各セクションに参照元タスクを明記。
"""

from __future__ import annotations

from app.core.config import settings

# ---------------------------------------------------------------------------
# HTTP / Scraping
# ---------------------------------------------------------------------------
HTTP_TIMEOUT_SEC: int = 30
"""HTTP request timeout per attempt (F-001, F-005)."""

PDF_DOWNLOAD_TIMEOUT_SEC: int = 60
"""PDF file download timeout (F-002)."""

SCRAPE_RATE_LIMIT_SEC: float = 1.0
"""Minimum interval between scraping requests (sec/request)."""

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
LLM_API_TIMEOUT_SEC: int = 60
"""LLM API call timeout (F-002)."""

LLM_RETRY_MAX: int = 2
"""LLM API retry limit."""

LLM_RETRY_BACKOFF_SEC: list[int] = [10, 30]
"""LLM API retry backoff intervals (seconds)."""

LLM_PARSE_RETRY_MAX: int = 1
"""LLM response parse retry limit."""

LLM_CIRCUIT_BREAKER_THRESHOLD: int = 3
"""Consecutive LLM failures to trigger circuit breaker (§3-4a)."""

LLM_DAILY_TOKEN_LIMIT: int = settings.LLM_DAILY_TOKEN_LIMIT
"""Daily LLM token cap (0=unlimited). Overridable via env var."""

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------
DB_CONNECT_TIMEOUT_SEC: int = 10
"""DB connection timeout."""

DB_RETRY_MAX: int = 3
"""DB connection retry limit."""

DB_RETRY_BACKOFF_SEC: list[int] = [1, 2, 4]
"""DB retry backoff intervals (seconds)."""

# ---------------------------------------------------------------------------
# HTTP Retry
# ---------------------------------------------------------------------------
HTTP_RETRY_MAX: int = 3
"""HTTP request retry limit (F-001, F-005)."""

HTTP_RETRY_BACKOFF_SEC: list[int] = [30, 60, 120]
"""HTTP retry backoff intervals (seconds)."""

# ---------------------------------------------------------------------------
# Stuck Detection (§3-5)
# ---------------------------------------------------------------------------
READING_STUCK_TIMEOUT_MIN: int = 5
"""reading_in_progress stuck timeout (minutes)."""

READING_STUCK_TIMEOUT_SCANNED_MIN: int = 10
"""reading_in_progress stuck timeout for scanned PDFs (minutes)."""

JUDGING_STUCK_TIMEOUT_MIN: int = 2
"""judging_in_progress stuck timeout (minutes)."""

CHECKLIST_STUCK_TIMEOUT_MIN: int = 1
"""checklist_generating stuck timeout (minutes)."""

# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------
BATCH_CASE_FETCH_TIMEOUT_MIN: int = 30
"""case_fetch batch overall timeout (minutes)."""

BATCH_OD_IMPORT_TIMEOUT_MIN: int = 30
"""od_import batch overall timeout (minutes)."""

BATCH_DETAIL_SCRAPE_TIMEOUT_MIN: int = 30
"""detail_scrape batch overall timeout (minutes)."""

CASCADE_FAILURE_THRESHOLD: int = 3
"""Consecutive cascade failures to abort F-002 within batch (§7-3)."""

# ---------------------------------------------------------------------------
# AI Quality
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD: float = 0.6
"""needs_review confidence threshold (F-002 §3-D)."""

SCANNED_PDF_CHAR_THRESHOLD: int = 50
"""Scanned PDF detection: chars/page below this = scanned (F-002 §3-B)."""

CHUNK_SPLIT_TOKEN_THRESHOLD: int = 5000
"""Section split threshold in tokens (F-002 §4)."""

EVIDENCE_MATCH_STRONG: float = 0.8
"""Strong evidence match Jaccard threshold (F-002 §6)."""

EVIDENCE_MATCH_CANDIDATE: float = 0.65
"""Candidate evidence match Jaccard threshold (F-002 §6)."""

# ---------------------------------------------------------------------------
# Schedule Calculation (F-004 §3-B)
# ---------------------------------------------------------------------------
SCHEDULE_REVERSE_START_BD: int = -5
"""Reverse schedule: prep start (business days before deadline)."""

SCHEDULE_REVERSE_REVIEW_BD: int = -2
"""Reverse schedule: internal review (business days before deadline)."""

SCHEDULE_REVERSE_FINALIZE_BD: int = -1
"""Reverse schedule: finalization (business days before deadline)."""

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
POLLING_INTERVAL_SEC: int = 5
"""Frontend polling interval for status updates (SSOT-2 §6-6)."""
