"""Create price_analysis view for F-005 analytics.

Revision ID: 014
Revises: 013
Create Date: 2026-03-16 18:07:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create price_analysis view."""
    view_sql = """
    CREATE OR REPLACE VIEW price_analysis AS
    SELECT
        COALESCE(ph.case_id, sb.case_id) AS case_id,
        COUNT(*) FILTER (WHERE ph.id IS NOT NULL OR sb.id IS NOT NULL) AS total_records,
        AVG(ph.asking_price) AS avg_asking_price,
        MIN(ph.asking_price) AS min_asking_price,
        MAX(ph.asking_price) AS max_asking_price,
        AVG(sb.final_price) AS avg_bid_price,
        MIN(sb.final_price) AS min_bid_price,
        MAX(sb.final_price) AS max_bid_price,
        CASE 
            WHEN AVG(ph.asking_price) > 0 
            THEN ROUND(((AVG(sb.final_price) - AVG(ph.asking_price)) / AVG(ph.asking_price) * 100)::numeric, 2)
            ELSE NULL 
        END AS price_variance_rate,
        AVG(sb.number_of_bidders)::numeric(8, 2) AS avg_bidders,
        GREATEST(MAX(ph.recorded_at), MAX(sb.bid_date)) AS latest_updated
    FROM price_history ph
    FULL OUTER JOIN successful_bids sb ON ph.case_id = sb.case_id
    GROUP BY COALESCE(ph.case_id, sb.case_id);
    """
    op.execute(view_sql)


def downgrade() -> None:
    """Drop price_analysis view."""
    op.execute("DROP VIEW IF EXISTS price_analysis;")
