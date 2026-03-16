"""Create bid_details table.

Revision ID: 003
Revises: 005
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bid_details",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("base_bid_id", UUID(as_uuid=True), sa.ForeignKey("base_bids.id"), nullable=False, unique=True),
        sa.Column("num_participants", sa.Integer()),
        sa.Column("budget_amount", sa.BigInteger()),
        sa.Column("winning_rate", sa.Numeric(5, 4)),
        sa.Column("bidder_details", JSONB()),
        sa.Column("raw_html", sa.Text()),
        sa.Column("scraped_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.execute("COMMENT ON TABLE bid_details IS 'F-005 Layer 2: 公告詳細補完データ。base_bids と 1:1'")


def downgrade() -> None:
    op.drop_table("bid_details")
