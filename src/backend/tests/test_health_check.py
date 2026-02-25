"""Tests for health_check script — TASK-47.

Tests all 5 critical alert conditions defined in SSOT-5 §4-4a.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_log import BatchLog
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.scripts.health_check import (
    CheckResult,
    check_batch_freshness,
    check_cascade_failure,
    check_circuit_breaker,
    check_raw_document_storage,
    check_stuck_cases,
    format_results,
)

pytestmark = pytest.mark.anyio


# ---- Helper factories ----


def _make_batch_log(
    *,
    feature_origin: str = "F-002",
    batch_type: str = "cascade",
    status: str = "success",
    started_at: datetime | None = None,
    source: str = "test",
) -> BatchLog:
    return BatchLog(
        id=uuid.uuid4(),
        source=source,
        feature_origin=feature_origin,
        batch_type=batch_type,
        status=status,
        started_at=started_at or datetime.now(timezone.utc),
        total_fetched=10,
        new_count=5,
        updated_count=2,
        unchanged_count=3,
        error_count=0,
    )


def _make_case(
    *,
    stage: str = "scored",
    source: str = "test",
    source_id: str | None = None,
) -> Case:
    return Case(
        id=uuid.uuid4(),
        source=source,
        source_id=source_id or f"TEST-{uuid.uuid4().hex[:8]}",
        case_name="テスト案件",
        issuing_org="テスト機関",
        current_lifecycle_stage=stage,
    )


def _make_event(
    *,
    case_id: uuid.UUID,
    event_type: str = "stage_transition",
    to_status: str = "scored",
    created_at: datetime | None = None,
) -> CaseEvent:
    return CaseEvent(
        id=uuid.uuid4(),
        case_id=case_id,
        event_type=event_type,
        to_status=to_status,
        triggered_by="system",
        actor_id="system",
        feature_origin="F-002",
        created_at=created_at or datetime.now(timezone.utc),
    )


# ---- HIGH-1: Cascade pipeline failure ----


class TestCascadeFailure:
    async def test_passes_when_no_batch_logs(self, db: AsyncSession) -> None:
        """No cascade batch logs → passes (no data yet)."""
        result = await check_cascade_failure(db)
        assert result.passed is True
        assert result.severity == "HIGH"

    async def test_passes_when_cascade_succeeds(self, db: AsyncSession) -> None:
        """Cascade batch logs with status=success → passes."""
        db.add(_make_batch_log(feature_origin="F-002", status="success"))
        db.add(_make_batch_log(feature_origin="F-003", status="success"))
        await db.flush()

        result = await check_cascade_failure(db)
        assert result.passed is True

    async def test_fails_when_cascade_failed(self, db: AsyncSession) -> None:
        """Cascade batch log with status=failed → fails with HIGH severity."""
        db.add(_make_batch_log(feature_origin="F-002", status="failed"))
        await db.flush()

        result = await check_cascade_failure(db)
        assert result.passed is False
        assert result.severity == "HIGH"
        assert "F-002" in str(result.details.get("failed_features"))


# ---- HIGH-2: Raw document storage ----


class TestRawDocumentStorage:
    async def test_passes_when_dir_exists_and_writable(self, tmp_path: Path) -> None:
        """Writable directory → passes."""
        result = await check_raw_document_storage(raw_dir_override=tmp_path)
        assert result.passed is True
        assert result.severity == "HIGH"

    async def test_fails_when_dir_missing(self) -> None:
        """Missing directory → fails."""
        missing = Path("/nonexistent/path/that/does/not/exist")
        result = await check_raw_document_storage(raw_dir_override=missing)
        assert result.passed is False
        assert result.severity == "HIGH"
        assert "does not exist" in result.message


# ---- HIGH-3: Circuit breaker ----


class TestCircuitBreaker:
    async def test_passes_when_no_circuit_events(self, db: AsyncSession) -> None:
        """No llm_circuit_open events → passes."""
        result = await check_circuit_breaker(db)
        assert result.passed is True
        assert result.severity == "HIGH"

    async def test_fails_when_circuit_open(self, db: AsyncSession) -> None:
        """Recent llm_circuit_open event → fails."""
        case = _make_case()
        db.add(case)
        await db.flush()

        event = _make_event(
            case_id=case.id,
            event_type="llm_circuit_open",
            to_status="reading_failed",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(event)
        await db.flush()

        result = await check_circuit_breaker(db)
        assert result.passed is False
        assert result.severity == "HIGH"
        assert result.details["count"] == 1

    async def test_passes_when_circuit_event_is_old(self, db: AsyncSession) -> None:
        """Old (>24h) llm_circuit_open event → passes."""
        case = _make_case()
        db.add(case)
        await db.flush()

        event = _make_event(
            case_id=case.id,
            event_type="llm_circuit_open",
            to_status="reading_failed",
            created_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        db.add(event)
        await db.flush()

        result = await check_circuit_breaker(db)
        assert result.passed is True


# ---- MEDIUM-4: Batch freshness ----


class TestBatchFreshness:
    async def test_fails_when_no_batches(self, db: AsyncSession) -> None:
        """No batch logs → fails (never run)."""
        result = await check_batch_freshness(db)
        assert result.passed is False
        assert result.severity == "MEDIUM"
        assert "never run" in result.message

    async def test_passes_when_recent_batch(self, db: AsyncSession) -> None:
        """Recent batch log → passes."""
        db.add(_make_batch_log(
            feature_origin="F-001",
            batch_type="case_fetch",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        ))
        await db.flush()

        result = await check_batch_freshness(db)
        assert result.passed is True
        assert result.severity == "MEDIUM"

    async def test_fails_when_stale_batch(self, db: AsyncSession) -> None:
        """Batch ran 30h ago → fails."""
        db.add(_make_batch_log(
            feature_origin="F-001",
            batch_type="case_fetch",
            started_at=datetime.now(timezone.utc) - timedelta(hours=30),
        ))
        await db.flush()

        result = await check_batch_freshness(db)
        assert result.passed is False
        assert "h ago" in result.message


# ---- MEDIUM-5: Stuck cases ----


class TestStuckCases:
    async def test_passes_when_no_stuck_cases(self, db: AsyncSession) -> None:
        """No processing cases → passes."""
        db.add(_make_case(stage="scored"))
        await db.flush()

        result = await check_stuck_cases(db)
        assert result.passed is True
        assert result.severity == "MEDIUM"

    async def test_passes_when_few_stuck(self, db: AsyncSession) -> None:
        """2 stuck cases (< threshold 3) → passes."""
        db.add(_make_case(stage="reading_in_progress"))
        db.add(_make_case(stage="judging_in_progress"))
        await db.flush()

        result = await check_stuck_cases(db)
        assert result.passed is True

    async def test_fails_when_3_or_more_stuck(self, db: AsyncSession) -> None:
        """3 stuck cases → fails."""
        db.add(_make_case(stage="reading_in_progress"))
        db.add(_make_case(stage="judging_in_progress"))
        db.add(_make_case(stage="checklist_generating"))
        await db.flush()

        result = await check_stuck_cases(db)
        assert result.passed is False
        assert result.severity == "MEDIUM"
        assert result.details["count"] == 3


# ---- Integration: format_results ----


class TestFormatResults:
    def test_all_pass(self) -> None:
        """When all pass, overall_status is PASS."""
        results = [
            CheckResult(name="a", severity="HIGH", passed=True, message="ok"),
            CheckResult(name="b", severity="MEDIUM", passed=True, message="ok"),
        ]
        output = json.loads(format_results(results))
        assert output["overall_status"] == "PASS"
        assert output["high_failures"] == 0
        assert output["medium_failures"] == 0

    def test_high_failure_counted(self) -> None:
        """HIGH failure is counted."""
        results = [
            CheckResult(name="a", severity="HIGH", passed=False, message="fail"),
            CheckResult(name="b", severity="MEDIUM", passed=True, message="ok"),
        ]
        output = json.loads(format_results(results))
        assert output["overall_status"] == "FAIL"
        assert output["high_failures"] == 1
        assert output["medium_failures"] == 0
