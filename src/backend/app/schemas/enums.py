"""SSOT-3 §5-3: Enum types for API request/response schemas.

Nine enum types used across all API endpoints.
These are *schema-layer* enums (str, Enum) — separate from SQLAlchemy model enums.
"""

from enum import Enum


class LifecycleStage(str, Enum):
    """17-value lifecycle stage (SSOT-2 §2-1 / SSOT-4 §3-9)."""

    DISCOVERED = "discovered"
    SCORED = "scored"
    UNDER_REVIEW = "under_review"
    PLANNED = "planned"
    SKIPPED = "skipped"
    READING_QUEUED = "reading_queued"
    READING_IN_PROGRESS = "reading_in_progress"
    READING_COMPLETED = "reading_completed"
    READING_FAILED = "reading_failed"
    JUDGING_QUEUED = "judging_queued"
    JUDGING_IN_PROGRESS = "judging_in_progress"
    JUDGING_COMPLETED = "judging_completed"
    JUDGING_FAILED = "judging_failed"
    CHECKLIST_GENERATING = "checklist_generating"
    CHECKLIST_ACTIVE = "checklist_active"
    CHECKLIST_COMPLETED = "checklist_completed"
    ARCHIVED = "archived"


class CaseStatus(str, Enum):
    """Case status (human-driven)."""

    NEW = "new"
    REVIEWED = "reviewed"
    PLANNED = "planned"
    SKIPPED = "skipped"
    ARCHIVED = "archived"


class Verdict(str, Enum):
    """Eligibility verdict."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCERTAIN = "uncertain"


class ChecklistItemStatus(str, Enum):
    """Checklist item check status."""

    PENDING = "pending"
    DONE = "done"


class TriggeredBy(str, Enum):
    """Event trigger source."""

    SYSTEM = "system"
    USER = "user"
    BATCH = "batch"
    CASCADE = "cascade"


class IncludeParam(str, Enum):
    """GET /cases/:id include parameter values (§4-1)."""

    CARD_CURRENT = "card_current"
    ELIGIBILITY_CURRENT = "eligibility_current"
    CHECKLIST_CURRENT = "checklist_current"
    LATEST_EVENTS = "latest_events"


class SortField(str, Enum):
    """Allowed sort fields for GET /cases (§4-1)."""

    DEADLINE_AT = "deadline_at"
    SCORE = "score"
    FIRST_SEEN_AT = "first_seen_at"
    CASE_NAME = "case_name"
    NEEDS_REVIEW = "needs_review"


class SortDirection(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class RetryScope(str, Enum):
    """Retry scope for retry-* endpoints (§4-2)."""

    SOFT = "soft"
    FORCE = "force"
