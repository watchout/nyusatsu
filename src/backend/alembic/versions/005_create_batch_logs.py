"""Create batch_logs table.

Revision ID: 005
Revises: 004
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "batch_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("feature_origin", sa.String(10), nullable=False),
        sa.Column("batch_type", sa.String(30), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'running'")),
        sa.Column("total_fetched", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("new_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_details", JSONB()),
        sa.Column("metadata", JSONB()),
    )
    op.execute("COMMENT ON TABLE batch_logs IS 'F-001/F-005: バッチ実行ログ'")


def downgrade() -> None:
    op.drop_table("batch_logs")
