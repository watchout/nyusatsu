"""CaseEvent model — イベントスパイン / 監査ログ (All features)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, ForeignKey, String, event, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class CaseEvent(UUIDPrimaryKeyMixin, Base):
    """イベントスパイン。INSERT-ONLY: UPDATE/DELETE はアプリ層で禁止。"""

    __tablename__ = "case_events"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False,
    )

    # Event info
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Trigger source
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default=text("'system'"),
    )
    feature_origin: Mapped[str] = mapped_column(String(10), nullable=False)

    # Payload
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"),
    )

    # Relationships
    case: Mapped[Case] = relationship(back_populates="events", lazy="raise")


from app.models.case import Case  # noqa: E402


# --- INSERT-ONLY enforcement at ORM level ---

@event.listens_for(CaseEvent, "before_update")
def _prevent_case_event_update(mapper: Any, connection: Any, target: CaseEvent) -> None:
    raise RuntimeError(
        "CaseEvent is INSERT-ONLY. UPDATE is prohibited. "
        f"Attempted to update event id={target.id}"
    )


@event.listens_for(CaseEvent, "before_delete")
def _prevent_case_event_delete(mapper: Any, connection: Any, target: CaseEvent) -> None:
    raise RuntimeError(
        "CaseEvent is INSERT-ONLY. DELETE is prohibited. "
        f"Attempted to delete event id={target.id}"
    )
