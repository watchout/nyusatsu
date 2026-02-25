/**
 * CaseOverview — overview tab for case detail (SSOT-2 §6-5).
 *
 * Shows: case_name, issuing_org, bid_type, category, deadline, score.
 */

import type { Case } from '../types/case';
import ScoreBadge from './ScoreBadge';
import ActionButtons from './ActionButtons';

interface CaseOverviewProps {
  caseData: Case;
  onAction: (action: string) => void;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function ScoreDetailView({ detail }: { detail: Record<string, number | undefined> | null }) {
  if (!detail) return null;
  const parts = Object.entries(detail)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${k}:${v}`)
    .join(' ');
  if (!parts) return null;
  return <span style={{ color: '#6b7280', fontSize: '0.85rem' }}>({parts})</span>;
}

export default function CaseOverview({ caseData, onAction }: CaseOverviewProps) {
  return (
    <div data-testid="case-overview">
      <table style={tableStyle}>
        <tbody>
          <Row label="案件名" value={caseData.case_name} />
          <Row label="発注機関" value={caseData.issuing_org} />
          <Row label="入札方式" value={caseData.bid_type ?? '—'} />
          <Row label="カテゴリ" value={caseData.category ?? '—'} />
          <Row label="地域" value={caseData.region ?? '—'} />
          <Row label="等級" value={caseData.grade ?? '—'} />
          <Row label="提出期限" value={formatDate(caseData.submission_deadline)} />
          <Row label="開札日" value={formatDate(caseData.opening_date)} />
          <tr>
            <td style={labelCellStyle}>スコア</td>
            <td style={valueCellStyle}>
              <ScoreBadge score={caseData.score} />{' '}
              <ScoreDetailView detail={caseData.score_detail} />
            </td>
          </tr>
        </tbody>
      </table>

      <ActionButtons
        stage={caseData.current_lifecycle_stage}
        onAction={onAction}
      />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td style={labelCellStyle}>{label}</td>
      <td style={valueCellStyle}>{value}</td>
    </tr>
  );
}

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
};

const labelCellStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontWeight: 600,
  fontSize: '0.875rem',
  color: '#374151',
  width: 120,
  verticalAlign: 'top',
  borderBottom: '1px solid #f3f4f6',
};

const valueCellStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: '0.875rem',
  borderBottom: '1px solid #f3f4f6',
};
