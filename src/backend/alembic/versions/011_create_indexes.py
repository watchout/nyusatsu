"""Create performance indexes for all tables.

23 regular indexes per SSOT-4 §5.
Partial unique indexes (uq_*_current) were created with their tables.

Revision ID: 010
Revises: 009
Create Date: 2026-02-20
"""

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

# All index definitions from SSOT-4 §5
_INDEXES = [
    # --- cases (6) ---
    "CREATE INDEX idx_cases_status ON cases(status) WHERE status != 'archived'",
    "CREATE INDEX idx_cases_lifecycle ON cases(current_lifecycle_stage)",
    "CREATE INDEX idx_cases_deadline ON cases(submission_deadline) WHERE submission_deadline IS NOT NULL",
    "CREATE INDEX idx_cases_score ON cases(score DESC NULLS LAST) WHERE status != 'archived'",
    "CREATE INDEX idx_cases_source ON cases(source, source_id)",
    "CREATE INDEX idx_cases_first_seen ON cases(first_seen_at DESC)",
    # --- case_cards (4) ---
    "CREATE INDEX idx_case_cards_current ON case_cards(case_id) WHERE is_current = true",
    "CREATE INDEX idx_case_cards_status ON case_cards(status) WHERE is_current = true",
    "CREATE INDEX idx_case_cards_deadline ON case_cards(deadline_at) WHERE is_current = true",
    "CREATE INDEX idx_case_cards_file_hash ON case_cards(file_hash) WHERE file_hash IS NOT NULL",
    # --- eligibility_results (2) ---
    "CREATE INDEX idx_eligibility_current ON eligibility_results(case_id) WHERE is_current = true",
    "CREATE INDEX idx_eligibility_verdict ON eligibility_results(verdict) WHERE is_current = true",
    # --- checklists (2) ---
    "CREATE INDEX idx_checklists_current ON checklists(case_id) WHERE is_current = true",
    "CREATE INDEX idx_checklists_status ON checklists(status) WHERE is_current = true",
    # --- case_events (3) ---
    "CREATE INDEX idx_case_events_case_time ON case_events(case_id, created_at DESC)",
    "CREATE INDEX idx_case_events_type ON case_events(event_type, created_at DESC)",
    "CREATE INDEX idx_case_events_feature ON case_events(feature_origin, created_at DESC)",
    # --- base_bids (3) ---
    "CREATE INDEX idx_base_bids_opening ON base_bids(opening_date DESC)",
    "CREATE INDEX idx_base_bids_org ON base_bids(issuing_org)",
    "CREATE INDEX idx_base_bids_source_id ON base_bids(source_id)",
    # --- bid_details (1) ---
    "CREATE INDEX idx_bid_details_base ON bid_details(base_bid_id)",
    # --- batch_logs (2) ---
    "CREATE INDEX idx_batch_logs_source ON batch_logs(source, started_at DESC)",
    "CREATE INDEX idx_batch_logs_status ON batch_logs(status) WHERE status != 'success'",
]


def upgrade() -> None:
    for ddl in _INDEXES:
        op.execute(ddl)


def downgrade() -> None:
    for ddl in reversed(_INDEXES):
        index_name = ddl.split()[2]  # "CREATE INDEX idx_xxx ..."
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
