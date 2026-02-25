/**
 * StageBadge — lifecycle stage display with label and color (SSOT-2 §2-1).
 */

import { STAGE_META, type LifecycleStage } from '../types/enums';

interface StageBadgeProps {
  stage: LifecycleStage;
}

const COLOR_MAP: Record<string, { bg: string; text: string }> = {
  gray: { bg: '#f3f4f6', text: '#4b5563' },
  blue: { bg: '#dbeafe', text: '#1d4ed8' },
  indigo: { bg: '#e0e7ff', text: '#4338ca' },
  yellow: { bg: '#fef3c7', text: '#92400e' },
  green: { bg: '#d1fae5', text: '#065f46' },
  red: { bg: '#fee2e2', text: '#991b1b' },
  orange: { bg: '#ffedd5', text: '#9a3412' },
};

export default function StageBadge({ stage }: StageBadgeProps) {
  const meta = STAGE_META[stage];
  const colors = COLOR_MAP[meta.color] ?? COLOR_MAP.gray;

  return (
    <span
      data-testid="stage-badge"
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        backgroundColor: colors.bg,
        color: colors.text,
        animation: meta.pulse ? 'pulse 2s ease-in-out infinite' : undefined,
      }}
    >
      {meta.label}
    </span>
  );
}
