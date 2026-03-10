"""Create case_cards table.

Revision ID: 006
Revises: 003
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "006"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_cards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        # バージョン管理
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # JSONB 5カテゴリ
        sa.Column("eligibility", JSONB()),
        sa.Column("schedule", JSONB()),
        sa.Column("business_content", JSONB()),
        sa.Column("submission_items", JSONB()),
        sa.Column("risk_factors", JSONB()),
        # 正規化キーカラム
        sa.Column("deadline_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("business_type", sa.String(50)),
        sa.Column("risk_level", sa.String(10)),
        sa.Column("extraction_method", sa.String(20), nullable=False, server_default=sa.text("'text'")),
        sa.Column("is_scanned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("assertion_counts", JSONB()),
        # 根拠・品質
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Numeric(3, 2)),
        sa.Column("file_hash", sa.String(64)),
        # ステータス・メタデータ
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("raw_notice_text", sa.Text()),
        sa.Column("raw_spec_text", sa.Text()),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("llm_request_id", sa.String(200)),
        sa.Column("token_usage", JSONB()),
        sa.Column("extracted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("reviewed_by", sa.String(100)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        # 制約
        sa.UniqueConstraint("case_id", "version", name="uq_case_cards_version"),
    )
    # 部分ユニーク: 1 case_id につき is_current=true は 1 件のみ
    op.execute("""
        CREATE UNIQUE INDEX uq_case_cards_current
        ON case_cards(case_id) WHERE is_current = true
    """)
    op.execute("COMMENT ON TABLE case_cards IS 'F-002: AI読解結果。version + is_current で再読解履歴を管理'")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_case_cards_current")
    op.drop_table("case_cards")
