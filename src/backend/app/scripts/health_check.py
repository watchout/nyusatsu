"""health_check — 致命アラート 5 条件チェック (SSOT-5 §4-4a, TASK-47).

Usage:
    python -m app.scripts.health_check

Exit code:
    0 — all checks passed (or only MEDIUM severity detected)
    1 — HIGH severity condition detected

Checks:
    HIGH-1: cascade_pipeline 全件失敗
    HIGH-2: raw ドキュメント保存失敗（ファイル存在チェック）
    HIGH-3: LLM サーキットブレーカ発動
    MEDIUM-4: 24h 以上バッチ未実行
    MEDIUM-5: スタック案件 3+ 件同時存在
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.models.batch_log import BatchLog
from app.models.case import Case
from app.models.case_event import CaseEvent

# Processing stages that indicate a stuck case
STUCK_STAGES = (
    "reading_in_progress",
    "judging_in_progress",
    "checklist_generating",
)

# Feature origins for cascade pipeline
CASCADE_FEATURES = ("F-002", "F-003", "F-004")


@dataclass
class CheckResult:
    """Single health check result."""

    name: str
    severity: str  # "HIGH" | "MEDIUM"
    passed: bool
    message: str
    details: dict[str, object] = field(default_factory=dict)


async def check_cascade_failure(session: AsyncSession) -> CheckResult:
    """HIGH-1: cascade_pipeline 全件失敗。

    最新のカスケード系バッチ (F-002/F-003/F-004) のうち、
    status='failed' のものがあるか確認。
    """
    subq = (
        select(
            BatchLog.feature_origin,
            func.max(BatchLog.started_at).label("latest"),
        )
        .where(BatchLog.feature_origin.in_(CASCADE_FEATURES))
        .group_by(BatchLog.feature_origin)
        .subquery()
    )

    stmt = (
        select(BatchLog)
        .join(
            subq,
            (BatchLog.feature_origin == subq.c.feature_origin)
            & (BatchLog.started_at == subq.c.latest),
        )
    )
    result = await session.execute(stmt)
    latest_batches = result.scalars().all()

    if not latest_batches:
        return CheckResult(
            name="cascade_failure",
            severity="HIGH",
            passed=True,
            message="No cascade batch logs found (no data yet).",
        )

    failed = [b for b in latest_batches if b.status == "failed"]
    if failed:
        return CheckResult(
            name="cascade_failure",
            severity="HIGH",
            passed=False,
            message=f"Cascade pipeline failure: {len(failed)} feature(s) failed.",
            details={
                "failed_features": [b.feature_origin for b in failed],
            },
        )

    return CheckResult(
        name="cascade_failure",
        severity="HIGH",
        passed=True,
        message="Cascade pipeline OK.",
    )


async def check_raw_document_storage(
    raw_dir_override: Path | None = None,
) -> CheckResult:
    """HIGH-2: raw ドキュメント保存失敗（ファイルシステムエラー）。

    DATA_RAW_DIR が存在し、書き込み可能かチェック。
    """
    raw_dir = raw_dir_override or Path(settings.DATA_RAW_DIR)

    if not raw_dir.exists():
        return CheckResult(
            name="raw_document_storage",
            severity="HIGH",
            passed=False,
            message=f"Raw data directory does not exist: {raw_dir}",
            details={"path": str(raw_dir)},
        )

    # Check write permission by attempting to create a temp file
    test_file = raw_dir / ".health_check_test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
    except OSError as exc:
        return CheckResult(
            name="raw_document_storage",
            severity="HIGH",
            passed=False,
            message=f"Raw data directory is not writable: {exc}",
            details={"path": str(raw_dir), "error": str(exc)},
        )

    return CheckResult(
        name="raw_document_storage",
        severity="HIGH",
        passed=True,
        message="Raw document storage OK.",
    )


async def check_circuit_breaker(session: AsyncSession) -> CheckResult:
    """HIGH-3: LLM サーキットブレーカ発動。

    case_events に event_type='llm_circuit_open' が直近24h以内に存在するか。
    """
    threshold = datetime.now(UTC) - timedelta(hours=24)

    stmt = (
        select(func.count())
        .select_from(CaseEvent)
        .where(
            CaseEvent.event_type == "llm_circuit_open",
            CaseEvent.created_at >= threshold,
        )
    )
    result = await session.execute(stmt)
    count = result.scalar_one()

    if count > 0:
        return CheckResult(
            name="circuit_breaker",
            severity="HIGH",
            passed=False,
            message=f"LLM circuit breaker triggered {count} time(s) in last 24h.",
            details={"count": count},
        )

    return CheckResult(
        name="circuit_breaker",
        severity="HIGH",
        passed=True,
        message="LLM circuit breaker OK (no triggers in 24h).",
    )


async def check_batch_freshness(session: AsyncSession) -> CheckResult:
    """MEDIUM-4: 24h 以上バッチ未実行。

    batch_logs の最新 started_at が 24h 以上前かチェック。
    """
    threshold = datetime.now(UTC) - timedelta(hours=24)

    stmt = select(func.max(BatchLog.started_at))
    result = await session.execute(stmt)
    latest = result.scalar_one()

    if latest is None:
        return CheckResult(
            name="batch_freshness",
            severity="MEDIUM",
            passed=False,
            message="No batch logs found — batches have never run.",
        )

    if latest < threshold:
        hours_ago = (datetime.now(UTC) - latest).total_seconds() / 3600
        return CheckResult(
            name="batch_freshness",
            severity="MEDIUM",
            passed=False,
            message=f"Last batch ran {hours_ago:.1f}h ago (threshold: 24h).",
            details={
                "last_batch_at": latest.isoformat(),
                "hours_ago": round(hours_ago, 1),
            },
        )

    return CheckResult(
        name="batch_freshness",
        severity="MEDIUM",
        passed=True,
        message="Batch freshness OK.",
    )


async def check_stuck_cases(session: AsyncSession) -> CheckResult:
    """MEDIUM-5: スタック案件 3+ 件同時存在。

    *_in_progress / *_generating ステージの案件数をカウント。
    """
    stmt = (
        select(func.count())
        .select_from(Case)
        .where(Case.current_lifecycle_stage.in_(STUCK_STAGES))
    )
    result = await session.execute(stmt)
    count = result.scalar_one()

    if count >= 3:
        detail_stmt = (
            select(Case.id, Case.current_lifecycle_stage, Case.last_updated_at)
            .where(Case.current_lifecycle_stage.in_(STUCK_STAGES))
            .limit(10)
        )
        detail_result = await session.execute(detail_stmt)
        stuck = [
            {
                "case_id": str(row.id),
                "stage": row.current_lifecycle_stage,
                "last_updated": row.last_updated_at.isoformat(),
            }
            for row in detail_result
        ]

        return CheckResult(
            name="stuck_cases",
            severity="MEDIUM",
            passed=False,
            message=f"{count} case(s) in processing stage (threshold: 3).",
            details={"count": count, "cases": stuck},
        )

    return CheckResult(
        name="stuck_cases",
        severity="MEDIUM",
        passed=True,
        message=f"Stuck cases OK ({count} in processing).",
    )


async def run_all_checks() -> list[CheckResult]:
    """Run all 5 health checks and return results."""
    results: list[CheckResult] = []

    # Filesystem check (no DB needed)
    results.append(await check_raw_document_storage())

    # DB-dependent checks share a session
    async with async_session() as session:
        results.append(await check_cascade_failure(session))
        results.append(await check_circuit_breaker(session))
        results.append(await check_batch_freshness(session))
        results.append(await check_stuck_cases(session))

    return results


def format_results(results: list[CheckResult]) -> str:
    """Format results as structured JSON."""
    output = {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_status": "PASS" if all(r.passed for r in results) else "FAIL",
        "high_failures": sum(1 for r in results if not r.passed and r.severity == "HIGH"),
        "medium_failures": sum(1 for r in results if not r.passed and r.severity == "MEDIUM"),
        "checks": [asdict(r) for r in results],
    }
    return json.dumps(output, indent=2, ensure_ascii=False, default=str)


async def main() -> int:
    """Run health checks and return exit code."""
    results = await run_all_checks()
    output = format_results(results)

    # Print structured JSON to stdout
    print(output)

    # Print failures to stderr with color
    for r in results:
        if not r.passed:
            severity_color = "\033[91m" if r.severity == "HIGH" else "\033[93m"
            reset = "\033[0m"
            print(
                f"{severity_color}[{r.severity}] {r.name}: {r.message}{reset}",
                file=sys.stderr,
            )

    # Exit 1 if any HIGH severity failed
    has_high_failure = any(not r.passed and r.severity == "HIGH" for r in results)
    return 1 if has_high_failure else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
