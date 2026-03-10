"""Create case_events table.

Revision ID: 009
Revises: 008
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        # イベント情報
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("from_status", sa.String(50)),
        sa.Column("to_status", sa.String(50), nullable=False),
        # 発火元
        sa.Column("triggered_by", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False, server_default=sa.text("'system'")),
        sa.Column("feature_origin", sa.String(10), nullable=False),
        # ペイロード
        sa.Column("payload", JSONB()),
        # タイムスタンプ
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.execute("COMMENT ON TABLE case_events IS 'イベントスパイン（監査ログ）。INSERT-ONLY: UPDATE/DELETE禁止（アプリケーション層で強制）'")  # noqa: E501
    op.execute("COMMENT ON COLUMN case_events.event_type IS '27種のイベント型。case_discovered, reading_started, judging_completed 等'")  # noqa: E501


def downgrade() -> None:
    op.drop_table("case_events")
