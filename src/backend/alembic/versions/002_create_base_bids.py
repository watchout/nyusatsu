"""Create base_bids table.

Revision ID: 002
Revises: 001
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "base_bids",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.String(200), nullable=False, unique=True),
        sa.Column("case_name", sa.Text(), nullable=False),
        sa.Column("issuing_org", sa.String(200), nullable=False),
        sa.Column("issuing_org_code", sa.String(50)),
        sa.Column("bid_type", sa.String(50)),
        sa.Column("category", sa.String(100)),
        sa.Column("winning_amount", sa.BigInteger()),
        sa.Column("winning_bidder", sa.String(200)),
        sa.Column("opening_date", sa.Date()),
        sa.Column("contract_date", sa.Date()),
        sa.Column("detail_url", sa.Text()),
        sa.Column("raw_data", JSONB()),
        sa.Column("imported_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.execute("COMMENT ON TABLE base_bids IS 'F-005 Layer 1: 調達ポータル落札実績OD由来のベースデータ'")
    op.execute("COMMENT ON COLUMN base_bids.raw_data IS 'ODの元CSVを丸ごと保存。CSVスキーマ変更時はraw_dataから段階的にカラム昇格'")  # noqa: E501


def downgrade() -> None:
    op.drop_table("base_bids")
