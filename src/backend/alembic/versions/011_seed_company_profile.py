"""Seed company_profiles with initial data.

Phase1 initial data per SSOT-4 §7-3.

Revision ID: 011
Revises: 010
Create Date: 2026-02-20
"""

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO company_profiles (
            unified_qualification, grade, business_categories, regions,
            licenses, certifications, experience, subcontractors
        ) VALUES (
            true,
            'D',
            '["物品の販売", "役務の提供その他"]'::JSONB,
            '["関東・甲信越"]'::JSONB,
            '[]'::JSONB,
            '[]'::JSONB,
            '[]'::JSONB,
            '[
                {"name": "クローバー運輸", "license": "運送業", "capabilities": ["軽運送", "配送"]},
                {"name": "電気工事会社", "license": "電気工事業", "capabilities": ["電気工事"]},
                {"name": "内装関係", "license": "内装業", "capabilities": ["内装工事"]}
            ]'::JSONB
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM company_profiles")
