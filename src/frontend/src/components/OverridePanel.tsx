/**
 * OverridePanel — human override for uncertain eligibility (SSOT-2 §7-3, §2-2 G4).
 *
 * Shown only when verdict === 'uncertain' and stage === 'judging_completed'.
 * Allows setting human_override to 'eligible' or 'ineligible' with a reason.
 */

import { useState } from 'react';
import type { Verdict } from '../types/enums';

interface OverridePanelProps {
  currentOverride: Verdict | null;
  overrideReason: string | null;
  overriddenAt: string | null;
  onOverride: (verdict: Verdict, reason: string) => void;
  disabled?: boolean;
}

export default function OverridePanel({
  currentOverride,
  overrideReason,
  overriddenAt,
  onOverride,
  disabled = false,
}: OverridePanelProps) {
  const [reason, setReason] = useState('');

  // Already overridden — show read-only result
  if (currentOverride) {
    const label = currentOverride === 'eligible' ? '参加可能' : '参加不可';
    return (
      <div data-testid="override-panel" style={panelStyle}>
        <h4 style={headerStyle}>判定の上書き</h4>
        <div data-testid="override-result" style={resultStyle}>
          <span style={{ fontWeight: 600 }}>上書き結果: {label}</span>
          {overrideReason && (
            <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: 4 }}>
              理由: {overrideReason}
            </div>
          )}
          {overriddenAt && (
            <div style={{ color: '#9ca3af', fontSize: '0.8rem', marginTop: 2 }}>
              {new Date(overriddenAt).toLocaleString('ja-JP')}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Not yet overridden — show interactive panel
  const canSubmit = reason.trim().length > 0 && !disabled;

  return (
    <div data-testid="override-panel" style={panelStyle}>
      <h4 style={headerStyle}>判定を上書き</h4>

      <div style={inputGroupStyle}>
        <label style={labelStyle}>理由</label>
        <textarea
          data-testid="override-reason-input"
          placeholder="判定を変更した理由を入力してください"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          maxLength={500}
          disabled={disabled}
          style={textareaStyle}
        />
      </div>

      <div style={buttonGroupStyle}>
        <button
          data-testid="override-eligible-btn"
          onClick={() => onOverride('eligible', reason)}
          disabled={!canSubmit}
          style={{
            ...baseButtonStyle,
            ...eligibleButtonStyle,
            opacity: canSubmit ? 1 : 0.5,
            cursor: canSubmit ? 'pointer' : 'not-allowed',
          }}
        >
          eligible に変更
        </button>
        <button
          data-testid="override-ineligible-btn"
          onClick={() => onOverride('ineligible', reason)}
          disabled={!canSubmit}
          style={{
            ...baseButtonStyle,
            ...ineligibleButtonStyle,
            opacity: canSubmit ? 1 : 0.5,
            cursor: canSubmit ? 'pointer' : 'not-allowed',
          }}
        >
          ineligible に変更
        </button>
      </div>

      <div style={warningStyle}>
        ⚠️ eligible に変更すると、チェックリストが自動生成されます
      </div>
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  marginTop: 16,
  padding: 12,
  backgroundColor: '#fffbeb',
  border: '1px solid #fcd34d',
  borderRadius: 8,
};

const headerStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '0.9rem',
  fontWeight: 700,
  color: '#92400e',
};

const resultStyle: React.CSSProperties = {
  padding: '8px 0',
};

const inputGroupStyle: React.CSSProperties = {
  marginBottom: 8,
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.85rem',
  fontWeight: 600,
  color: '#374151',
  marginBottom: 4,
};

const textareaStyle: React.CSSProperties = {
  width: '100%',
  minHeight: 60,
  padding: 8,
  border: '1px solid #d1d5db',
  borderRadius: 6,
  fontSize: '0.85rem',
  resize: 'vertical',
  boxSizing: 'border-box',
};

const buttonGroupStyle: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  marginBottom: 8,
};

const baseButtonStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: 6,
  fontSize: '0.85rem',
  fontWeight: 600,
  border: 'none',
};

const eligibleButtonStyle: React.CSSProperties = {
  backgroundColor: '#059669',
  color: '#fff',
};

const ineligibleButtonStyle: React.CSSProperties = {
  backgroundColor: '#dc2626',
  color: '#fff',
};

const warningStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  color: '#92400e',
  fontStyle: 'italic',
};
