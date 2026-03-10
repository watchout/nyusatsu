"""Checklist builder for F-004.

Converts CaseCard submission_items into checklist items,
adds fixed items (envelope, delivery method), inserts uncertain
confirmation tasks, and generates warnings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()

# Fixed items always added to bid-time checklist
FIXED_BID_ITEMS = [
    {"name": "封筒（二重封筒）", "category": "bid_time", "source": "fixed", "is_checked": False},
    {"name": "配送方法の確認", "category": "bid_time", "source": "fixed", "is_checked": False},
]


@dataclass
class ChecklistBuildResult:
    """Result of checklist building."""

    checklist_items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ChecklistBuilder:
    """Build checklist items from CaseCard extraction and judgment result."""

    def build(
        self,
        extraction: dict[str, Any],
        eligibility_check_details: dict[str, Any] | None = None,
        risk_factors: list[dict[str, Any]] | None = None,
        soft_gaps: list[dict[str, Any]] | None = None,
        assertion_counts: dict[str, int] | None = None,
    ) -> ChecklistBuildResult:
        """Build the complete checklist.

        Args:
            extraction: CaseCard JSONB fields (submission_items, etc.)
            eligibility_check_details: From EligibilityResult.check_details
            risk_factors: From CaseCard.risk_factors
            soft_gaps: From EligibilityResult.soft_gaps
            assertion_counts: From CaseCard.assertion_counts
        """
        items: list[dict[str, Any]] = []
        warnings: list[str] = []

        # 1. Bid-time items from extraction
        submission_items = extraction.get("submission_items") or {}
        bid_items = submission_items.get("bid_time_items") or []
        for idx, item in enumerate(bid_items):
            checklist_item = {
                "name": item.get("name", f"提出物{idx+1}"),
                "category": "bid_time",
                "source": "extraction",
                "assertion_type": item.get("assertion_type", "inferred"),
                "template_source": item.get("template_source"),
                "deadline": item.get("deadline"),
                "is_checked": False,
            }
            # Prioritize quote-related items
            if self._is_quote_item(item):
                items.insert(0, checklist_item)
            else:
                items.append(checklist_item)

        # 2. Performance-time items
        perf_items = submission_items.get("performance_time_items") or []
        for idx, item in enumerate(perf_items):
            items.append({
                "name": item.get("name", f"履行時提出物{idx+1}"),
                "category": "performance_time",
                "source": "extraction",
                "assertion_type": item.get("assertion_type", "inferred"),
                "is_checked": False,
            })

        # 3. Fixed items
        for fixed in FIXED_BID_ITEMS:
            items.append(dict(fixed))

        # 4. Quote item if has_quote_requirement
        biz = extraction.get("business_content") or {}
        if biz.get("has_quote_requirement"):
            # Check if 見積書 already exists
            existing_names = {i["name"] for i in items}
            if "下見積もり書" not in existing_names and "見積書" not in existing_names:
                items.insert(0, {
                    "name": "下見積もり書",
                    "category": "bid_time",
                    "source": "extraction",
                    "assertion_type": "fact",
                    "is_checked": False,
                })

        # 5. Inferred items get label suffix
        for item in items:
            if item.get("assertion_type") == "inferred" and item.get("source") == "extraction":
                item["label_suffix"] = "（推定）"

        # 6. Uncertain confirmation tasks
        if eligibility_check_details:
            hard_checks = eligibility_check_details.get("hard_checks") or []
            soft_checks = eligibility_check_details.get("soft_checks") or []
            for check in hard_checks + soft_checks:
                if check.get("result") in ("uncertain", "gap"):
                    items.append({
                        "name": f"確認: {check.get('label', '不明')} — {check.get('required', '')}",
                        "category": "confirmation",
                        "source": "judgment",
                        "is_checked": False,
                    })

        # 7. Warnings
        if risk_factors:
            for rf in risk_factors:
                sev = rf.get("severity", "low")
                if sev in ("high", "medium"):
                    warnings.append(f"[{sev.upper()}] {rf.get('label', '')}: {rf.get('description', '')}")

        if soft_gaps:
            for gap in soft_gaps:
                warnings.append(f"ソフト条件ギャップ: {gap.get('label', '')} — {gap.get('required', '')}")

        if assertion_counts:
            inferred = assertion_counts.get("inferred", 0)
            caution = assertion_counts.get("caution", 0)
            if inferred + caution > 0:
                warnings.append(f"推定項目 {inferred}件, 要注意項目 {caution}件 — 原文確認推奨")

        return ChecklistBuildResult(checklist_items=items, warnings=warnings)

    @staticmethod
    def _is_quote_item(item: dict) -> bool:
        name = item.get("name", "")
        return "見積" in name or "quote" in name.lower()
