/**
 * CaseList — case table/card list for the dashboard (SSOT-2 §6-4).
 */

import { Link } from 'react-router-dom';
import { useCaseActions, useCases } from '../contexts/AppContext';
import type { Case } from '../types/case';
import ScoreBadge from './ScoreBadge';
import StageBadge from './StageBadge';

function formatDeadline(deadline: string | null): string {
  if (!deadline) return '—';
  const d = new Date(deadline);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function CaseRow({ caseItem }: { caseItem: Case }) {
  return (
    <Link
      to={`/cases/${caseItem.id}`}
      style={cardStyle}
      data-testid="case-row"
    >
      <div style={cardHeaderStyle}>
        <span style={{ fontWeight: 600, flex: 1 }}>{caseItem.case_name}</span>
        <ScoreBadge score={caseItem.score} />
      </div>
      <div style={cardBodyStyle}>
        <span style={{ color: '#6b7280', fontSize: '0.8rem' }}>
          {caseItem.issuing_org}
        </span>
        <span style={{ fontSize: '0.8rem' }}>
          期限: {formatDeadline(caseItem.submission_deadline)}
        </span>
        <StageBadge stage={caseItem.current_lifecycle_stage} />
      </div>
    </Link>
  );
}

export default function CaseList() {
  const { items, loading, error, total, page, totalPages } = useCases();
  const { setPage } = useCaseActions();

  if (loading && items.length === 0) {
    return <div data-testid="case-list-loading" style={emptyStyle}>読み込み中…</div>;
  }

  if (error) {
    return (
      <div data-testid="case-list-error" style={emptyStyle}>
        エラーが発生しました: {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div data-testid="case-list-empty" style={emptyStyle}>
        まだ案件がありません。バッチを実行して案件を収集しましょう。
      </div>
    );
  }

  return (
    <div data-testid="case-list">
      <div style={listStyle}>
        {items.map((c) => (
          <CaseRow key={c.id} caseItem={c} />
        ))}
      </div>

      {/* Pagination */}
      <div data-testid="pagination" style={paginationStyle}>
        <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>
          全 {total} 件
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            style={pageBtnStyle}
          >
            前へ
          </button>
          <span style={{ fontSize: '0.85rem', lineHeight: '32px' }}>
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
            style={pageBtnStyle}
          >
            次へ
          </button>
        </div>
      </div>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  display: 'block',
  padding: '12px 16px',
  backgroundColor: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: 8,
  textDecoration: 'none',
  color: 'inherit',
  cursor: 'pointer',
};

const cardHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 6,
};

const cardBodyStyle: React.CSSProperties = {
  display: 'flex',
  gap: 12,
  alignItems: 'center',
  flexWrap: 'wrap',
};

const listStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: '0 16px',
};

const emptyStyle: React.CSSProperties = {
  padding: '48px 16px',
  textAlign: 'center',
  color: '#6b7280',
};

const paginationStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
};

const pageBtnStyle: React.CSSProperties = {
  padding: '4px 12px',
  border: '1px solid #d1d5db',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: '0.85rem',
};
