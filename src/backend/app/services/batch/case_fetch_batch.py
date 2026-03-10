"""Case fetch batch runner — F-001 TASK-20.

Orchestrates the full case fetch pipeline:
1. Adapter.fetch() — get raw cases
2. Normalise → store (UPSERT)
3. Filter — apply criteria
4. Score — 4-factor model
5. EventService — discovered → scored transition

Implements BaseBatchRunner for use with BatchRunner.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.services.batch.base import BaseBatchRunner
from app.services.batch.types import (
    BatchConfig,
    BatchItemResult,
    ItemStatus,
)
from app.services.case_fetch.base_adapter import BaseSourceAdapter, RawCase, StoreAction
from app.services.case_fetch.filter import CaseFilter, CaseFilterCriteria
from app.services.case_fetch.normalizer import CaseNormalizer
from app.services.case_fetch.scorer import CaseScorer
from app.services.event_service import EventService

logger = structlog.get_logger()


class CaseFetchBatch(BaseBatchRunner):
    """Batch runner for case fetching pipeline.

    Args:
        adapter: Source adapter to fetch from.
        filter_criteria: Optional filter criteria.
        scorer: Optional scorer (uses defaults if None).
    """

    def __init__(
        self,
        adapter: BaseSourceAdapter,
        filter_criteria: CaseFilterCriteria | None = None,
        scorer: CaseScorer | None = None,
    ) -> None:
        self._adapter = adapter
        self._filter_criteria = filter_criteria or CaseFilterCriteria()
        self._scorer = scorer or CaseScorer()
        self._normalizer = CaseNormalizer()
        self._filter = CaseFilter()
        self._event_service = EventService()
        self._raw_cases: list[RawCase] = []

    @property
    def config(self) -> BatchConfig:
        return BatchConfig(
            source=self._adapter.source_name,
            batch_type="case_fetch",
            feature_origin="F-001",
        )

    async def on_batch_start(self) -> None:
        """Fetch raw cases from adapter."""
        self._raw_cases = await self._adapter.fetch()
        logger.info(
            "case_fetch_fetched",
            source=self._adapter.source_name,
            raw_count=len(self._raw_cases),
        )

    async def fetch_items(
        self, db: AsyncSession,
    ) -> AsyncIterator[RawCase]:
        """Yield fetched raw cases."""
        for raw_case in self._raw_cases:
            yield raw_case

    async def process_item(
        self, db: AsyncSession, item: Any,
    ) -> BatchItemResult:
        """Process a single raw case through the full pipeline.

        Steps:
        1. Normalise
        2. Store (UPSERT)
        3. Filter check
        4. Score
        5. Record lifecycle transition (discovered → scored)
        """
        raw_case: RawCase = item

        # 1. Normalise
        try:
            norm_result = self._normalizer.normalise(raw_case)
        except ValueError as exc:
            return BatchItemResult(
                item_id=raw_case.source_id,
                status=ItemStatus.FAILED,
                error_message=f"Normalisation error: {exc}",
            )

        # 2. Store
        store_result = await self._adapter.store(db, norm_result.data)

        if store_result.action == StoreAction.SKIPPED:
            return BatchItemResult(
                item_id=raw_case.source_id,
                status=ItemStatus.SKIPPED,
            )

        # 3. Load the case for filtering and scoring
        from sqlalchemy import select
        case = (
            await db.execute(
                select(Case).where(
                    Case.source == raw_case.source,
                    Case.source_id == raw_case.source_id,
                ),
            )
        ).scalar_one()

        # 4. Score
        breakdown = await self._scorer.score(db, case)
        case.score = breakdown.total
        case.score_detail = {
            "competition": breakdown.competition,
            "scale": breakdown.scale,
            "deadline": breakdown.deadline,
            "domain_fit": breakdown.domain_fit,
        }
        await db.flush()

        # 5. Record lifecycle transition: discovered → scored
        try:
            await self._event_service.record_transition(
                db,
                case=case,
                to_stage="scored",
                triggered_by="batch",
                feature_origin="F-001",
            )
        except Exception as exc:
            # Log but don't fail — event recording is best-effort
            logger.warning(
                "lifecycle_transition_failed",
                case_id=str(case.id),
                error=str(exc),
            )

        if store_result.action == StoreAction.INSERTED:
            return BatchItemResult(
                item_id=raw_case.source_id,
                status=ItemStatus.SUCCESS,
            )
        else:  # UPDATED
            return BatchItemResult(
                item_id=raw_case.source_id,
                status=ItemStatus.SUCCESS,
            )
