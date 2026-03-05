/**
 * ReadingTab — AI reading results tab (SSOT-2 §6-5, §7-2).
 *
 * Displays 5 extraction categories:
 *   1. eligibility    — 参加条件
 *   2. schedule       — スケジュール
 *   3. business_content — 業務内容
 *   4. submission_items — 提出物
 *   5. risk_factors   — リスク要因
 *
 * Also shows: confidence score, assertion counts, scanned-PDF warning,
 * needs_review badge, and per-field evidence panels.
 */

import type { CaseCard, AssertionCounts } from '../types/case';
import ConfidenceBadge from './ConfidenceBadge';
import AssertionLabel from './AssertionLabel';
import EvidencePanel from './EvidencePanel';

interface ReadingTabProps {
  card: CaseCard;
  onMarkReviewed?: () => void;
}

// ---- Section renderers ----

function formatDate(val: unknown): string {
  if (typeof val !== 'string') return '—';
  return new Date(val).toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function SectionHeader({ title, testId }: { title: string; testId: string }) {
  return <h3 data-testid={testId} style={sectionHeaderStyle}>{title}</h3>;
}

function FieldRow({
  label,
  value,
  assertionType,
  fieldKey,
  evidence,
}: {
  label: string;
  value: string;
  assertionType?: string;
  fieldKey?: string;
  evidence?: Record<string, unknown> | null;
}) {
  const aType = (assertionType === 'fact' || assertionType === 'inferred' || assertionType === 'caution')
    ? assertionType
    : undefined;

  return (
    <div style={fieldRowStyle}>
      <div style={fieldLabelStyle}>{label}</div>
      <div style={fieldValueStyle}>
        {value}
        {aType && (
          <span style={{ marginLeft: 6 }}>
            <AssertionLabel type={aType} />
          </span>
        )}
      </div>
      {fieldKey && evidence && <EvidencePanel evidence={evidence} fieldKey={fieldKey} />}
    </div>
  );
}

function EligibilitySection({
  data,
  evidence,
}: {
  data: Record<string, unknown>;
  evidence: Record<string, unknown> | null;
}) {
  return (
    <div data-testid="section-eligibility">
      <SectionHeader title="参加条件" testId="section-header-eligibility" />
      <FieldRow
        label="全省庁統一資格"
        value={data.unified_qualification ? 'あり' : 'なし'}
        assertionType={data.unified_qualification_assertion as string}
        fieldKey="eligibility.unified_qualification"
        evidence={evidence}
      />
      {!!data.grade && (
        <FieldRow
          label="等級"
          value={String(data.grade)}
          assertionType={data.grade_assertion as string}
          fieldKey="eligibility.grade"
          evidence={evidence}
        />
      )}
      {!!data.business_category && (
        <FieldRow
          label="営業品目"
          value={String(data.business_category)}
          fieldKey="eligibility.business_category"
          evidence={evidence}
        />
      )}
      {!!data.region && (
        <FieldRow
          label="競争参加地域"
          value={String(data.region)}
          fieldKey="eligibility.region"
          evidence={evidence}
        />
      )}
      {!!data.additional_requirements && (
        <FieldRow
          label="その他要件"
          value={
            Array.isArray(data.additional_requirements)
              ? (data.additional_requirements as string[]).join('、')
              : String(data.additional_requirements)
          }
          fieldKey="eligibility.additional_requirements"
          evidence={evidence}
        />
      )}
    </div>
  );
}

function ScheduleSection({
  data,
  evidence,
}: {
  data: Record<string, unknown>;
  evidence: Record<string, unknown> | null;
}) {
  const fields: { key: string; label: string }[] = [
    { key: 'spec_meeting_date', label: '仕様説明会' },
    { key: 'submission_deadline', label: '提出期限' },
    { key: 'opening_date', label: '開札日' },
    { key: 'equivalent_deadline', label: '同等品申請期限' },
    { key: 'quote_deadline', label: '下見積もり期限' },
    { key: 'performance_deadline', label: '履行期限' },
  ];

  return (
    <div data-testid="section-schedule">
      <SectionHeader title="スケジュール" testId="section-header-schedule" />
      {fields.map((f) =>
        data[f.key] ? (
          <FieldRow
            key={f.key}
            label={f.label}
            value={formatDate(data[f.key])}
            assertionType={data[`${f.key}_assertion`] as string}
            fieldKey={`schedule.${f.key}`}
            evidence={evidence}
          />
        ) : null,
      )}
    </div>
  );
}

function BusinessContentSection({
  data,
  evidence,
}: {
  data: Record<string, unknown>;
  evidence: Record<string, unknown> | null;
}) {
  return (
    <div data-testid="section-business_content">
      <SectionHeader title="業務内容" testId="section-header-business_content" />
      {!!data.business_type && (
        <FieldRow label="業務種別" value={String(data.business_type)} />
      )}
      {!!data.summary && (
        <FieldRow
          label="概要"
          value={String(data.summary)}
          fieldKey="business_content.summary"
          evidence={evidence}
        />
      )}
      {!!data.contract_type && (
        <FieldRow label="契約種別" value={String(data.contract_type)} />
      )}
      {data.has_spec_meeting !== undefined && (
        <FieldRow label="仕様説明会" value={data.has_spec_meeting ? 'あり' : 'なし'} />
      )}
      {data.has_quote_requirement !== undefined && (
        <FieldRow label="下見積もり" value={data.has_quote_requirement ? '必要' : '不要'} />
      )}
      {Array.isArray(data.delivery_locations) && (data.delivery_locations as string[]).length > 0 && (
        <FieldRow
          label="納入場所"
          value={(data.delivery_locations as string[]).join('、')}
        />
      )}
    </div>
  );
}

function SubmissionItemsSection({
  data,
  evidence,
}: {
  data: Record<string, unknown>[];
  evidence: Record<string, unknown> | null;
}) {
  // Group by phase
  const bidTime = data.filter((d) => d.phase === 'bid_time' || !d.phase);
  const perfTime = data.filter((d) => d.phase === 'performance_time');

  return (
    <div data-testid="section-submission_items">
      <SectionHeader title="提出物" testId="section-header-submission_items" />
      {bidTime.length > 0 && (
        <>
          <div style={subHeaderStyle}>入札参加時</div>
          {bidTime.map((item, i) => (
            <div key={i} style={itemCardStyle}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {String(item.name ?? '—')}
                {!!item.assertion_type && (
                  <span style={{ marginLeft: 6 }}>
                    <AssertionLabel type={item.assertion_type as 'fact' | 'inferred' | 'caution'} />
                  </span>
                )}
              </div>
              {!!item.deadline && (
                <div style={itemDetailStyle}>期限: {formatDate(item.deadline)}</div>
              )}
              {!!item.template_source && (
                <div style={itemDetailStyle}>書式: {String(item.template_source)}</div>
              )}
              {!!item.notes && (
                <div style={itemDetailStyle}>{String(item.notes)}</div>
              )}
              {evidence && (
                <EvidencePanel evidence={evidence} fieldKey={`submission_items.${i}`} />
              )}
            </div>
          ))}
        </>
      )}
      {perfTime.length > 0 && (
        <>
          <div style={subHeaderStyle}>履行時</div>
          {perfTime.map((item, i) => (
            <div key={i} style={itemCardStyle}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {String(item.name ?? '—')}
                {!!item.assertion_type && (
                  <span style={{ marginLeft: 6 }}>
                    <AssertionLabel type={item.assertion_type as 'fact' | 'inferred' | 'caution'} />
                  </span>
                )}
              </div>
              {!!item.notes && (
                <div style={itemDetailStyle}>{String(item.notes)}</div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function RiskFactorsSection({ data }: { data: Record<string, unknown>[] }) {
  const severityColor: Record<string, { bg: string; text: string }> = {
    '高': { bg: '#fee2e2', text: '#991b1b' },
    'high': { bg: '#fee2e2', text: '#991b1b' },
    '中': { bg: '#fef3c7', text: '#92400e' },
    'medium': { bg: '#fef3c7', text: '#92400e' },
    '低': { bg: '#d1fae5', text: '#065f46' },
    'low': { bg: '#d1fae5', text: '#065f46' },
  };

  return (
    <div data-testid="section-risk_factors">
      <SectionHeader title="リスク要因" testId="section-header-risk_factors" />
      {data.length === 0 && (
        <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>リスクは検出されていません。</div>
      )}
      {data.map((risk, i) => {
        const sev = String(risk.severity ?? risk.risk_type ?? '');
        const colors = severityColor[sev] ?? { bg: '#f3f4f6', text: '#374151' };
        return (
          <div key={i} style={{ ...itemCardStyle, borderLeft: `3px solid ${colors.text}` }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span
                style={{
                  padding: '1px 6px',
                  borderRadius: 3,
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: colors.bg,
                  color: colors.text,
                }}
              >
                {sev}
              </span>
              <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {String(risk.description ?? risk.risk_type ?? '—')}
              </span>
            </div>
            {!!risk.detection_condition && (
              <div style={itemDetailStyle}>{String(risk.detection_condition)}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---- AssertionSummary ----

function AssertionSummary({ counts }: { counts: AssertionCounts | null }) {
  if (!counts) return null;
  return (
    <div data-testid="assertion-summary" style={summaryStyle}>
      <span style={{ color: '#374151' }}>確認: {counts.fact}件</span>
      {counts.inferred > 0 && (
        <span style={{ color: '#92400e' }}>⚠️ 推定: {counts.inferred}件</span>
      )}
      {counts.caution > 0 && (
        <span style={{ color: '#991b1b' }}>⚠️ 注意: {counts.caution}件</span>
      )}
    </div>
  );
}

// ---- Main component ----

export default function ReadingTab({ card, onMarkReviewed }: ReadingTabProps) {
  const needsReview = card.status === 'needs_review';

  return (
    <div data-testid="reading-tab">
      {/* Header bar: confidence + status + scan warning */}
      <div style={headerBarStyle}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <ConfidenceBadge score={card.confidence_score} />
          {needsReview && (
            <span data-testid="needs-review-badge" style={needsReviewStyle}>
              要確認
            </span>
          )}
          {card.is_scanned && (
            <span data-testid="scanned-warning" style={scannedWarningStyle}>
              ⚠️ 画像PDF — テキスト抽出に制限あり
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {card.extracted_at && (
            <span style={{ color: '#6b7280', fontSize: '0.8rem' }}>
              抽出: {formatDate(card.extracted_at)}
            </span>
          )}
          {needsReview && onMarkReviewed && (
            <button
              data-testid="mark-reviewed-btn"
              onClick={onMarkReviewed}
              style={reviewButtonStyle}
            >
              確認済みにする
            </button>
          )}
        </div>
      </div>

      {/* Assertion summary */}
      <AssertionSummary counts={card.assertion_counts} />

      {/* Meta info */}
      {card.llm_model && (
        <div style={metaStyle}>
          モデル: {card.llm_model} | バージョン: {card.version}
          {card.extraction_method && ` | 抽出: ${card.extraction_method}`}
        </div>
      )}

      {/* 5 category sections */}
      {card.eligibility && (
        <EligibilitySection data={card.eligibility} evidence={card.evidence} />
      )}

      {card.schedule && (
        <ScheduleSection data={card.schedule} evidence={card.evidence} />
      )}

      {card.business_content && (
        <BusinessContentSection data={card.business_content} evidence={card.evidence} />
      )}

      {card.submission_items && card.submission_items.length > 0 && (
        <SubmissionItemsSection data={card.submission_items} evidence={card.evidence} />
      )}

      {card.risk_factors !== null && card.risk_factors !== undefined && (
        <RiskFactorsSection data={card.risk_factors} />
      )}

      {/* Empty state if no sections at all */}
      {!card.eligibility &&
        !card.schedule &&
        !card.business_content &&
        (!card.submission_items || card.submission_items.length === 0) &&
        (!card.risk_factors || card.risk_factors.length === 0) && (
          <div style={{ color: '#6b7280', padding: 16 }}>
            抽出データがありません。
          </div>
        )}
    </div>
  );
}

// ---- Styles ----

const headerBarStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: 8,
  padding: '8px 0',
  borderBottom: '1px solid #e5e7eb',
  marginBottom: 12,
};

const needsReviewStyle: React.CSSProperties = {
  padding: '2px 8px',
  borderRadius: 4,
  fontSize: '0.8rem',
  fontWeight: 600,
  backgroundColor: '#fef3c7',
  color: '#92400e',
};

const scannedWarningStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  color: '#92400e',
};

const reviewButtonStyle: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: 6,
  border: '1px solid #d1d5db',
  backgroundColor: '#fff',
  cursor: 'pointer',
  fontSize: '0.8rem',
  fontWeight: 600,
};

const summaryStyle: React.CSSProperties = {
  display: 'flex',
  gap: 12,
  fontSize: '0.85rem',
  padding: '6px 0',
};

const metaStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#9ca3af',
  padding: '4px 0 12px',
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: '1rem',
  fontWeight: 700,
  color: '#1f2937',
  margin: '16px 0 8px',
  paddingBottom: 4,
  borderBottom: '1px solid #e5e7eb',
};

const subHeaderStyle: React.CSSProperties = {
  fontSize: '0.85rem',
  fontWeight: 600,
  color: '#6b7280',
  margin: '8px 0 4px',
};

const fieldRowStyle: React.CSSProperties = {
  padding: '4px 0',
};

const fieldLabelStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  fontWeight: 600,
  color: '#6b7280',
};

const fieldValueStyle: React.CSSProperties = {
  fontSize: '0.875rem',
  color: '#1f2937',
};

const itemCardStyle: React.CSSProperties = {
  padding: '6px 10px',
  marginBottom: 6,
  backgroundColor: '#f9fafb',
  borderRadius: 4,
};

const itemDetailStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  color: '#6b7280',
  marginTop: 2,
};
