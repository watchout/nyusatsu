/**
 * EligibilityTab — eligibility judgment results (SSOT-2 §7-3).
 *
 * Shows: verdict badge, confidence, hard fail reasons, soft gaps,
 * and override panel for uncertain verdicts.
 */

import type { EligibilityResult, HardFailReason, SoftGap } from '../types/case';
import type { Verdict } from '../types/enums';
import VerdictBadge from './VerdictBadge';
import ConfidenceBadge from './ConfidenceBadge';
import OverridePanel from './OverridePanel';

interface EligibilityTabProps {
  eligibility: EligibilityResult;
  stage: string;
  onOverride: (verdict: Verdict, reason: string) => void;
}

// ---- Sub-components ----

function HardFailReasonsList({ reasons }: { reasons: HardFailReason[] }) {
  if (reasons.length === 0) return null;

  return (
    <div data-testid="hard-fail-reasons">
      <h4 style={sectionHeaderStyle}>不適合理由</h4>
      {reasons.map((r, i) => (
        <div key={i} style={reasonCardStyle}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={failIconStyle}>❌</span>
            <span style={reasonLabelStyle}>{r.code}</span>
          </div>
          <div style={reasonDescStyle}>{r.description}</div>
          {r.source_text && (
            <div style={sourceTextStyle}>根拠: 「{r.source_text}」</div>
          )}
        </div>
      ))}
    </div>
  );
}

function SoftGapsList({ gaps }: { gaps: SoftGap[] }) {
  if (gaps.length === 0) return null;

  const severityColors: Record<string, { bg: string; text: string }> = {
    high: { bg: '#fee2e2', text: '#991b1b' },
    medium: { bg: '#fef3c7', text: '#92400e' },
    low: { bg: '#dbeafe', text: '#1e40af' },
  };

  const severityLabel: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低',
  };

  return (
    <div data-testid="soft-gaps">
      <h4 style={sectionHeaderStyle}>追加確認事項</h4>
      {gaps.map((g, i) => {
        const colors = severityColors[g.severity] ?? severityColors.medium;
        return (
          <div key={i} style={gapCardStyle}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={cautionIconStyle}>⚠️</span>
              <span style={reasonLabelStyle}>{g.code}</span>
              <span
                data-testid={`severity-${g.severity}`}
                style={{
                  padding: '1px 6px',
                  borderRadius: 3,
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  backgroundColor: colors.bg,
                  color: colors.text,
                }}
              >
                {severityLabel[g.severity] ?? g.severity}
              </span>
            </div>
            <div style={reasonDescStyle}>{g.description}</div>
          </div>
        );
      })}
    </div>
  );
}

// ---- Main component ----

export default function EligibilityTab({
  eligibility,
  stage,
  onOverride,
}: EligibilityTabProps) {
  const isJudgingCompleted = stage === 'judging_completed';
  const isUncertain = eligibility.verdict === 'uncertain';
  const showOverridePanel = isUncertain;

  return (
    <div data-testid="eligibility-tab">
      {/* Header: verdict + confidence */}
      <div style={headerStyle}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <span style={labelStyle}>判定:</span>
            <VerdictBadge verdict={eligibility.verdict} />
          </div>
          <div>
            <span style={labelStyle}>信頼度:</span>
            <ConfidenceBadge score={eligibility.confidence} />
          </div>
        </div>
        <div style={metaStyle}>
          バージョン: {eligibility.version} | 判定日: {new Date(eligibility.judged_at).toLocaleString('ja-JP')}
        </div>
      </div>

      {/* Hard fail reasons */}
      <HardFailReasonsList reasons={eligibility.hard_fail_reasons} />

      {/* Soft gaps */}
      <SoftGapsList gaps={eligibility.soft_gaps} />

      {/* No issues for eligible */}
      {eligibility.verdict === 'eligible' &&
        eligibility.hard_fail_reasons.length === 0 &&
        eligibility.soft_gaps.length === 0 && (
          <div data-testid="eligible-message" style={eligibleMsgStyle}>
            ✅ 全ての参加要件を満たしています。
          </div>
        )}

      {/* Override panel (uncertain only) */}
      {showOverridePanel && (
        <OverridePanel
          currentOverride={eligibility.human_override}
          overrideReason={eligibility.override_reason}
          overriddenAt={eligibility.overridden_at}
          onOverride={onOverride}
          disabled={!isJudgingCompleted}
        />
      )}

      {/* Show past override result for non-uncertain verdicts */}
      {!isUncertain && eligibility.human_override && (
        <div data-testid="past-override" style={pastOverrideStyle}>
          <span style={{ fontWeight: 600 }}>上書き済み:</span>{' '}
          {eligibility.human_override === 'eligible' ? '参加可能' : '参加不可'}
          {eligibility.override_reason && (
            <span style={{ color: '#6b7280' }}> — {eligibility.override_reason}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ---- Styles ----

const headerStyle: React.CSSProperties = {
  padding: '8px 0 12px',
  borderBottom: '1px solid #e5e7eb',
  marginBottom: 12,
};

const labelStyle: React.CSSProperties = {
  fontSize: '0.85rem',
  fontWeight: 600,
  color: '#6b7280',
  marginRight: 6,
};

const metaStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#9ca3af',
  marginTop: 6,
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: '0.9rem',
  fontWeight: 700,
  color: '#1f2937',
  margin: '12px 0 6px',
};

const reasonCardStyle: React.CSSProperties = {
  padding: '6px 10px',
  marginBottom: 4,
  backgroundColor: '#fef2f2',
  borderRadius: 4,
  borderLeft: '3px solid #f87171',
};

const gapCardStyle: React.CSSProperties = {
  padding: '6px 10px',
  marginBottom: 4,
  backgroundColor: '#fffbeb',
  borderRadius: 4,
  borderLeft: '3px solid #fbbf24',
};

const failIconStyle: React.CSSProperties = {
  fontSize: '0.85rem',
};

const cautionIconStyle: React.CSSProperties = {
  fontSize: '0.85rem',
};

const reasonLabelStyle: React.CSSProperties = {
  fontWeight: 600,
  fontSize: '0.85rem',
  color: '#374151',
};

const reasonDescStyle: React.CSSProperties = {
  fontSize: '0.85rem',
  color: '#4b5563',
  marginTop: 2,
};

const sourceTextStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  color: '#6b7280',
  fontStyle: 'italic',
  marginTop: 2,
};

const eligibleMsgStyle: React.CSSProperties = {
  padding: '12px 16px',
  backgroundColor: '#ecfdf5',
  borderRadius: 6,
  color: '#065f46',
  fontWeight: 600,
  fontSize: '0.9rem',
};

const pastOverrideStyle: React.CSSProperties = {
  marginTop: 12,
  padding: '8px 12px',
  backgroundColor: '#f3f4f6',
  borderRadius: 6,
  fontSize: '0.85rem',
};
