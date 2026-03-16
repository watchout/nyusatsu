"""Create cases table.

Revision ID: 004
Revises: 002
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # データソース識別
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(200), nullable=False),
        # 案件基本情報
        sa.Column("case_name", sa.Text(), nullable=False),
        sa.Column("issuing_org", sa.String(200), nullable=False),
        sa.Column("issuing_org_code", sa.String(50)),
        sa.Column("bid_type", sa.String(50)),
        sa.Column("category", sa.String(100)),
        sa.Column("region", sa.String(100)),
        sa.Column("grade", sa.String(10)),
        # 日程
        sa.Column("submission_deadline", sa.TIMESTAMP(timezone=True)),
        sa.Column("opening_date", sa.TIMESTAMP(timezone=True)),
        # URL
        sa.Column("spec_url", sa.Text()),
        sa.Column("notice_url", sa.Text()),
        sa.Column("detail_url", sa.Text()),
        # ステータス・スコア
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'new'")),
        sa.Column("skip_reason", sa.Text()),
        sa.Column("score", sa.Integer()),
        sa.Column("score_detail", JSONB()),
        # 統一ライフサイクル
        sa.Column("current_lifecycle_stage", sa.String(50), nullable=False, server_default=sa.text("'discovered'")),
        # 原本・メタ
        sa.Column("raw_data", JSONB()),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True)),
        # 制約
        sa.UniqueConstraint("source", "source_id", name="uq_cases_source"),
    )
    op.execute("COMMENT ON TABLE cases IS 'F-001: 案件マスタ。全データソースから収集した案件の統一スキーマ'")
    op.execute("COMMENT ON COLUMN cases.current_lifecycle_stage IS '非正規化キャッシュ。真実は case_events の最新行'")
    op.execute("COMMENT ON COLUMN cases.raw_data IS 'スキーマ変更への備え。取得した元データを丸ごと保存'")


def downgrade() -> None:
    op.drop_table("cases")
