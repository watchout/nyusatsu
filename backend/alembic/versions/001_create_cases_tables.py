"""create cases and batch_logs tables

Revision ID: 001
Create Date: 2026-03-16

F-001: 案件自動収集＋AIフィルタリング
- cases: 案件データの統一スキーマ
- batch_logs: バッチ実行ログ
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # cases テーブル
    op.create_table(
        'cases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source', sa.String(50), nullable=False, comment='データソース識別子'),
        sa.Column('source_id', sa.String(255), nullable=False, comment='データソースでの案件ID'),
        sa.Column('case_name', sa.Text, nullable=False, comment='案件名'),
        sa.Column('issuing_org', sa.String(255), nullable=False, comment='発注機関名'),
        sa.Column('issuing_org_code', sa.String(50), nullable=True, comment='発注機関コード'),
        sa.Column('bid_type', sa.String(50), nullable=True, comment='入札方式'),
        sa.Column('category', sa.String(100), nullable=True, comment='品目分類'),
        sa.Column('region', sa.String(100), nullable=True, comment='地域'),
        sa.Column('grade', sa.String(10), nullable=True, comment='等級'),
        sa.Column('submission_deadline', TIMESTAMP(timezone=True), nullable=True, comment='提出期限'),
        sa.Column('opening_date', TIMESTAMP(timezone=True), nullable=True, comment='開札日'),
        sa.Column('spec_url', sa.Text, nullable=True, comment='仕様書URL'),
        sa.Column('notice_url', sa.Text, nullable=True, comment='公告URL'),
        sa.Column('detail_url', sa.Text, nullable=True, comment='詳細ページURL'),
        sa.Column('status', sa.String(20), nullable=False, server_default='new', comment='ステータス'),
        sa.Column('skip_reason', sa.Text, nullable=True, comment='見送り理由'),
        sa.Column('score', sa.Integer, nullable=True, comment='スコア(0-100)'),
        sa.Column('score_detail', JSONB, nullable=True, comment='スコア内訳'),
        sa.Column('raw_data', JSONB, nullable=True, comment='元データ全体'),
        sa.Column('first_seen_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='初回検出日時'),
        sa.Column('last_updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='最終更新日時'),
        sa.Column('archived_at', TIMESTAMP(timezone=True), nullable=True, comment='アーカイブ日時'),
        sa.UniqueConstraint('source', 'source_id', name='uq_cases_source_id'),
        sa.Index('idx_cases_status', 'status'),
        sa.Index('idx_cases_score', 'score'),
        sa.Index('idx_cases_submission_deadline', 'submission_deadline'),
    )

    # batch_logs テーブル
    op.create_table(
        'batch_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source', sa.String(50), nullable=False, comment='データソース識別子'),
        sa.Column('started_at', TIMESTAMP(timezone=True), nullable=False, comment='実行開始日時'),
        sa.Column('finished_at', TIMESTAMP(timezone=True), nullable=True, comment='実行終了日時'),
        sa.Column('status', sa.String(20), nullable=False, comment='success/failed/partial'),
        sa.Column('total_fetched', sa.Integer, nullable=True, comment='取得件数'),
        sa.Column('new_count', sa.Integer, nullable=True, comment='新規件数'),
        sa.Column('updated_count', sa.Integer, nullable=True, comment='更新件数'),
        sa.Column('unchanged_count', sa.Integer, nullable=True, comment='変更なし件数'),
        sa.Column('error_count', sa.Integer, nullable=True, comment='エラー件数'),
        sa.Column('error_details', JSONB, nullable=True, comment='エラー詳細'),
        sa.Index('idx_batch_logs_source', 'source'),
        sa.Index('idx_batch_logs_started_at', 'started_at'),
    )


def downgrade():
    op.drop_table('batch_logs')
    op.drop_table('cases')
