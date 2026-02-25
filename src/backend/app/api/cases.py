"""Cases API endpoints — TASK-33 / SSOT-3 §4-1.

GET /api/v1/cases      — List with 8 filters + sort + pagination
GET /api/v1/cases/:id  — Detail with optional include parameter
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationError
from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.case_event import CaseEvent
from app.models.checklist import Checklist
from app.models.eligibility_result import EligibilityResult
from app.schemas.case import CaseDetailResponse, CaseResponse
from app.schemas.case_card import CaseCardResponse
from app.schemas.checklist import ChecklistResponse
from app.schemas.eligibility import EligibilityResponse
from app.schemas.envelope import PaginatedMeta, PaginatedResponse, SuccessResponse
from app.schemas.event import EventResponse

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

# Allowed sort fields → column mapping
_SORT_FIELDS = {
    "deadline_at": "submission_deadline",
    "score": "score",
    "first_seen_at": "first_seen_at",
    "case_name": "case_name",
}

# lifecycle_stage values considered "failed"
_FAILED_STAGES = frozenset({
    "reading_failed", "judging_failed",
})


# ---------------------------------------------------------------------------
# GET /api/v1/cases — list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse)
async def list_cases(
    db: AsyncSession = Depends(get_db),
    lifecycle_stage: str | None = Query(None, description="Comma-sep stages"),
    status: str | None = Query(None, description="Case status filter"),
    score_min: int | None = Query(None, ge=0, le=100),
    score_max: int | None = Query(None, ge=0, le=100),
    deadline_before: str | None = Query(None, description="ISO8601"),
    deadline_after: str | None = Query(None, description="ISO8601"),
    needs_review: bool | None = Query(None),
    has_failed: bool | None = Query(None),
    search: str | None = Query(None, description="Partial match"),
    sort: str = Query("deadline_at:asc", description="field:dir[,field:dir]"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    exclude_archived: bool = Query(True),
) -> PaginatedResponse:
    """案件一覧 (§4-1)."""
    stmt = select(Case)
    count_stmt = select(func.count()).select_from(Case)

    conditions = []

    # --- Filters ---
    if exclude_archived:
        conditions.append(Case.current_lifecycle_stage != "archived")

    if lifecycle_stage:
        stages = [s.strip() for s in lifecycle_stage.split(",") if s.strip()]
        if stages:
            conditions.append(Case.current_lifecycle_stage.in_(stages))

    if status:
        conditions.append(Case.status == status)

    if score_min is not None:
        conditions.append(Case.score >= score_min)

    if score_max is not None:
        conditions.append(Case.score <= score_max)

    if deadline_before:
        conditions.append(Case.submission_deadline <= deadline_before)

    if deadline_after:
        conditions.append(Case.submission_deadline >= deadline_after)

    if has_failed is True:
        conditions.append(Case.current_lifecycle_stage.in_(_FAILED_STAGES))

    if search:
        pattern = f"%{search}%"
        conditions.append(
            or_(
                Case.case_name.ilike(pattern),
                Case.issuing_org.ilike(pattern),
            ),
        )

    # needs_review → subquery on case_cards
    if needs_review is True:
        needs_review_subq = (
            select(CaseCard.case_id)
            .where(CaseCard.is_current.is_(True), CaseCard.status == "needs_review")
            .correlate(Case)
        )
        conditions.append(Case.id.in_(needs_review_subq))

    for cond in conditions:
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    # --- Sort ---
    order_clauses = _parse_sort(sort)
    for clause in order_clauses:
        stmt = stmt.order_by(clause)

    # --- Pagination ---
    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / limit))

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    rows = (await db.execute(stmt)).scalars().all()

    data = [
        CaseResponse.model_validate(row).model_dump(mode="json")
        for row in rows
    ]

    return PaginatedResponse(
        data=data,
        meta=PaginatedMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/cases/:id — detail
# ---------------------------------------------------------------------------


@router.get("/{case_id}", response_model=SuccessResponse)
async def get_case_detail(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    include: str | None = Query(None, description="Comma-sep: card_current,..."),
) -> SuccessResponse:
    """案件詳細 (§4-1)."""
    case = (
        await db.execute(select(Case).where(Case.id == case_id))
    ).scalar_one_or_none()

    if case is None:
        raise NotFoundError(
            message=f"Case not found: {case_id}",
            details={"case_id": str(case_id)},
        )

    data = CaseDetailResponse.model_validate(case).model_dump(mode="json")

    # --- Embed optional includes ---
    if include:
        includes = {s.strip() for s in include.split(",") if s.strip()}
        _ALLOWED = {"card_current", "eligibility_current", "checklist_current", "latest_events"}
        invalid = includes - _ALLOWED
        if invalid:
            raise ValidationError(
                message=f"Invalid include value(s): {', '.join(sorted(invalid))}",
                details={"allowed": sorted(_ALLOWED), "invalid": sorted(invalid)},
            )

        if "card_current" in includes:
            card = (
                await db.execute(
                    select(CaseCard)
                    .where(CaseCard.case_id == case_id, CaseCard.is_current.is_(True)),
                )
            ).scalar_one_or_none()
            data["card"] = (
                CaseCardResponse.model_validate(card).model_dump(mode="json")
                if card else None
            )

        if "eligibility_current" in includes:
            elig = (
                await db.execute(
                    select(EligibilityResult)
                    .where(
                        EligibilityResult.case_id == case_id,
                        EligibilityResult.is_current.is_(True),
                    ),
                )
            ).scalar_one_or_none()
            data["eligibility"] = (
                EligibilityResponse.model_validate(elig).model_dump(mode="json")
                if elig else None
            )

        if "checklist_current" in includes:
            cl = (
                await db.execute(
                    select(Checklist)
                    .where(
                        Checklist.case_id == case_id,
                        Checklist.is_current.is_(True),
                    ),
                )
            ).scalar_one_or_none()
            data["checklist"] = (
                ChecklistResponse.model_validate(cl).model_dump(mode="json")
                if cl else None
            )

        if "latest_events" in includes:
            events = (
                await db.execute(
                    select(CaseEvent)
                    .where(CaseEvent.case_id == case_id)
                    .order_by(CaseEvent.created_at.desc())
                    .limit(10),
                )
            ).scalars().all()
            data["latest_events"] = [
                EventResponse.model_validate(e).model_dump(mode="json")
                for e in events
            ]

    return SuccessResponse(data=data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sort(sort_str: str) -> list:
    """Parse 'field:dir,field:dir' into SQLAlchemy order_by clauses.

    Raises ValidationError on invalid field/direction.
    """
    clauses = []
    parts = [p.strip() for p in sort_str.split(",") if p.strip()]

    for part in parts:
        tokens = part.split(":")
        if len(tokens) != 2:
            raise ValidationError(
                message=f"Invalid sort format: '{part}'. Expected 'field:asc' or 'field:desc'.",
                details={"sort": sort_str},
            )
        field_name, direction = tokens[0], tokens[1]

        # Special handling for needs_review (virtual sort)
        if field_name == "needs_review":
            if direction == "desc":
                # needs_review cases first
                clauses.append(
                    case(
                        (Case.current_lifecycle_stage == "reading_completed", 0),
                        else_=1,
                    ).asc(),
                )
            else:
                clauses.append(
                    case(
                        (Case.current_lifecycle_stage == "reading_completed", 0),
                        else_=1,
                    ).desc(),
                )
            continue

        col_name = _SORT_FIELDS.get(field_name)
        if col_name is None:
            raise ValidationError(
                message=f"Invalid sort field: '{field_name}'.",
                details={
                    "allowed_fields": sorted(list(_SORT_FIELDS.keys()) + ["needs_review"]),
                    "given": field_name,
                },
            )

        if direction not in ("asc", "desc"):
            raise ValidationError(
                message=f"Invalid sort direction: '{direction}'. Must be 'asc' or 'desc'.",
                details={"allowed": ["asc", "desc"], "given": direction},
            )

        col = getattr(Case, col_name)
        if direction == "asc":
            clauses.append(col.asc().nulls_last())
        else:
            clauses.append(col.desc().nulls_last())

    return clauses
