"""Create price_history and successful_bids tables for F-005.

Revision ID: 012_create_price_history_and_successful_bids
Revises: 011_seed_company_profile
Create Date: 2026-03-16 18:06:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "012_create_price_history_and_successful_bids"
down_revision = "011_seed_company_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create price_history and successful_bids tables."""
    # Create price_history table
    op.create_table(
        "price_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("asking_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("estimated_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("lowest_bid", sa.Numeric(15, 2), nullable=True),
        sa.Column("highest_bid", sa.Numeric(15, 2), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("data_source", sa.String(255), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="JPY"),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "source", "recorded_at", name="uq_price_history_unique_entry"),
    )
    op.create_index("idx_price_history_case_id", "price_history", ["case_id"], unique=False)
    op.create_index("idx_price_history_recorded_at", "price_history", ["recorded_at"], unique=False)
    op.create_index("idx_price_history_case_recorded", "price_history", ["case_id", "recorded_at"], unique=False)

    # Create successful_bids table
    op.create_table(
        "successful_bids",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("final_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("number_of_bidders", sa.Integer(), nullable=True),
        sa.Column("winning_company", sa.String(255), nullable=True),
        sa.Column("bid_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("contract_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="JPY"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_successful_bids_case_id", "successful_bids", ["case_id"], unique=False)
    op.create_index("idx_successful_bids_bid_date", "successful_bids", ["bid_date"], unique=False)
    op.create_index("idx_successful_bids_case_date", "successful_bids", ["case_id", "bid_date"], unique=False)


def downgrade() -> None:
    """Drop price_history and successful_bids tables."""
    op.drop_index("idx_successful_bids_case_date", table_name="successful_bids")
    op.drop_index("idx_successful_bids_bid_date", table_name="successful_bids")
    op.drop_index("idx_successful_bids_case_id", table_name="successful_bids")
    op.drop_table("successful_bids")

    op.drop_index("idx_price_history_case_recorded", table_name="price_history")
    op.drop_index("idx_price_history_recorded_at", table_name="price_history")
    op.drop_index("idx_price_history_case_id", table_name="price_history")
    op.drop_constraint("uq_price_history_unique_entry", "price_history", type_="unique")
    op.drop_table("price_history")
