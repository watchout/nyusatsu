"""Create eligibility_results table.

Revision ID: 007
Revises: 006
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eligibility_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("case_card_id", UUID(as_uuid=True), sa.ForeignKey("case_cards.id"), nullable=False),
        # バージョン管理
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # 判定結果
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("hard_fail_reasons", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("soft_gaps", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_refs", JSONB()),
        sa.Column("check_details", JSONB(), nullable=False),
        sa.Column("company_profile_snapshot", JSONB(), nullable=False),
        # 人間オーバーライド
        sa.Column("human_override", sa.String(20)),
        sa.Column("override_reason", sa.Text()),
        sa.Column("overridden_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("overridden_by", sa.String(100)),
        # タイムスタンプ
        sa.Column("judged_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        # 制約
        sa.UniqueConstraint("case_id", "version", name="uq_eligibility_version"),
    )
    # 部分ユニーク
    op.execute("""
        CREATE UNIQUE INDEX uq_eligibility_current
        ON eligibility_results(case_id) WHERE is_current = true
    """)
    op.execute("COMMENT ON TABLE eligibility_results IS 'F-003: 参加可否判定結果。version + is_current で再判定履歴を管理'")  # noqa: E501


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_eligibility_current")
    op.drop_table("eligibility_results")
