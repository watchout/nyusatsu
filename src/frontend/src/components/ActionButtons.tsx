/**
 * ActionButtons — gate-controlled action buttons (SSOT-2 §2-2, §5).
 *
 * Each button maps to a gate (G1-G9). Visibility and disabled state
 * depend on the current lifecycle stage.
 *
 * During processing stages (*_queued, *_in_progress, *_generating),
 * all buttons except archive are disabled.
 */

import { isProcessingStage, type LifecycleStage } from '../types/enums';

interface ActionButtonsProps {
  stage: LifecycleStage;
  onAction: (action: string) => void;
  disabled?: boolean;
}

interface ButtonDef {
  action: string;
  label: string;
  gate: string;
  /** Stages where this button is visible. */
  showWhen: LifecycleStage[];
  /** Color variant. */
  variant: 'primary' | 'danger' | 'secondary' | 'warning';
}

const BUTTONS: ButtonDef[] = [
  {
    action: 'mark-planned',
    label: '応札予定にする',
    gate: 'G1',
    showWhen: ['under_review'],
    variant: 'primary',
  },
  {
    action: 'mark-skipped',
    label: '見送り',
    gate: 'G2',
    showWhen: ['under_review'],
    variant: 'secondary',
  },
  {
    action: 'retry-reading',
    label: '再読解（リトライ）',
    gate: 'G3',
    showWhen: ['reading_failed'],
    variant: 'warning',
  },
  {
    action: 'retry-judging',
    label: '再判定（リトライ）',
    gate: 'G5',
    showWhen: ['judging_failed'],
    variant: 'warning',
  },
  {
    action: 'retry-reading',
    label: '再読解',
    gate: 'G6',
    showWhen: ['reading_completed'],
    variant: 'secondary',
  },
  {
    action: 'retry-judging',
    label: '再判定',
    gate: 'G7',
    showWhen: ['judging_completed'],
    variant: 'secondary',
  },
  {
    action: 'retry-checklist',
    label: '再生成',
    gate: 'G8',
    showWhen: ['checklist_active'],
    variant: 'secondary',
  },
  {
    action: 'restore',
    label: '復帰',
    gate: 'G9',
    showWhen: ['skipped'],
    variant: 'primary',
  },
  {
    action: 'archive',
    label: 'アーカイブ',
    gate: '-',
    showWhen: [], // Special: shown on all stages except archived
    variant: 'danger',
  },
];

const VARIANT_STYLES: Record<string, React.CSSProperties> = {
  primary: { backgroundColor: '#2563eb', color: '#fff', border: 'none' },
  secondary: { backgroundColor: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db' },
  danger: { backgroundColor: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5' },
  warning: { backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d' },
};

export default function ActionButtons({
  stage,
  onAction,
  disabled: externalDisabled = false,
}: ActionButtonsProps) {
  const processing = isProcessingStage(stage);

  return (
    <div data-testid="action-buttons" style={containerStyle}>
      {BUTTONS.map((btn) => {
        // Archive is shown on all stages except archived
        const isArchive = btn.action === 'archive';
        const visible = isArchive
          ? stage !== 'archived'
          : btn.showWhen.includes(stage);

        if (!visible) return null;

        // During processing, all buttons except archive are disabled
        const isDisabled =
          externalDisabled || (processing && !isArchive);

        return (
          <button
            key={btn.gate}
            data-testid={`action-${btn.gate}`}
            onClick={() => onAction(btn.action)}
            disabled={isDisabled}
            style={{
              ...baseButtonStyle,
              ...VARIANT_STYLES[btn.variant],
              opacity: isDisabled ? 0.5 : 1,
              cursor: isDisabled ? 'not-allowed' : 'pointer',
            }}
          >
            {btn.label}
          </button>
        );
      })}
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
  padding: '12px 0',
};

const baseButtonStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: 6,
  fontSize: '0.875rem',
  fontWeight: 600,
};
