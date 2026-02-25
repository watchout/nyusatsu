"""F-002 evaluation metrics logging per SSOT-5 §8.

Logs extraction quality metrics via structlog for monitoring and evaluation.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class ReadingMetrics:
    """Collect and log F-002 reading pipeline evaluation metrics."""

    @staticmethod
    def log_extraction(
        *,
        case_id: str,
        recall_fields: int,
        evidence_rate: float,
        uncertain_rate: float,
        processing_time_ms: int,
        token_usage: dict[str, int],
    ) -> None:
        """Log extraction quality metrics.

        Args:
            case_id: Target case UUID as string.
            recall_fields: Number of fields that had evidence matches.
            evidence_rate: Fraction of fields with evidence attached (0.0-1.0).
            uncertain_rate: Fraction of assertions that are caution (0.0-1.0).
            processing_time_ms: Total pipeline processing time in milliseconds.
            token_usage: LLM token usage dict {"input": N, "output": N}.
        """
        logger.info(
            "f002_extraction_metrics",
            case_id=case_id,
            recall_fields=recall_fields,
            evidence_rate=round(evidence_rate, 3),
            uncertain_rate=round(uncertain_rate, 3),
            processing_time_ms=processing_time_ms,
            token_input=token_usage.get("input", 0),
            token_output=token_usage.get("output", 0),
        )
