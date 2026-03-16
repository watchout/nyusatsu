"""Create checklists table.

Revision ID: 008
Revises: 007
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
        "checklists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("case_card_id", UUID(as_uuid=True), sa.ForeignKey("case_cards.id"), nullable=False),
        sa.Column(
            "eligibility_result_id", UUID(as_uuid=True),
            sa.ForeignKey("eligibility_results.id"), nullable=False,
        ),
        # バージョン管理
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # チェックリスト内容
        sa.Column("checklist_items", JSONB(), nullable=False),
        sa.Column("schedule_items", JSONB(), nullable=False),
        sa.Column("warnings", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "progress", JSONB(), nullable=False,
            server_default=sa.text("'{\"total\": 0, \"done\": 0, \"rate\": 0.0}'::jsonb"),
        ),
        # ステータス
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        # 制約
        sa.UniqueConstraint("case_id", "version", name="uq_checklists_version"),
    )
    # 部分ユニーク
    op.execute("""
        CREATE UNIQUE INDEX uq_checklists_current
        ON checklists(case_id) WHERE is_current = true
    """)
    op.execute("COMMENT ON TABLE checklists IS 'F-004: チェックリスト。version + is_current で再生成履歴を管理'")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_checklists_current")
    op.drop_table("checklists")
