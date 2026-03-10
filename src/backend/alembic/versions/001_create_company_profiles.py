"""Create company_profiles table.

Revision ID: 001
Revises:
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("unified_qualification", sa.Boolean(), nullable=False),
        sa.Column("grade", sa.String(10), nullable=False),
        sa.Column("business_categories", JSONB(), nullable=False),
        sa.Column("regions", JSONB(), nullable=False),
        sa.Column("licenses", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("certifications", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("experience", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("subcontractors", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.execute("COMMENT ON TABLE company_profiles IS 'F-003: 会社プロフィール。Phase1は1レコード固定'")


def downgrade() -> None:
    op.drop_table("company_profiles")
