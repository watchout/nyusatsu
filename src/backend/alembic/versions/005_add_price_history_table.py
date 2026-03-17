"""Add price_history table for F-005.

Revision ID: 005_add_price_history
Revises: 
Create Date: 2026-03-16 17:45:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_price_history"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create price_histories table."""
    op.create_table(
        "price_histories",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("budgeted_price", sa.Numeric(15, 0), nullable=True),
        sa.Column("winning_bid", sa.Numeric(15, 0), nullable=True),
        sa.Column("lowest_bid", sa.Numeric(15, 0), nullable=True),
        sa.Column("estimated_price", sa.Numeric(15, 0), nullable=True),
        sa.Column("total_bids", sa.Integer(), nullable=True),
        sa.Column("unique_bidders", sa.Integer(), nullable=True),
        sa.Column("bid_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("price_difference_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("data_source", sa.String(50), nullable=True),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "analysis_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_histories_case_id",
        "price_histories",
        ["case_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_price_history_case_recorded",
        "price_histories",
        ["case_id", "recorded_at"],
    )


def downgrade() -> None:
    """Drop price_histories table."""
    op.drop_constraint("uq_price_history_case_recorded", "price_histories")
    op.drop_index("ix_price_histories_case_id", "price_histories")
    op.drop_table("price_histories")
