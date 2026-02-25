/**
 * VerdictBadge — displays eligibility verdict (SSOT-2 §7-2, §7-3).
 *
 * eligible:   green "参加可能"
 * ineligible: red "参加不可"
 * uncertain:  orange "確認必要"
 */

import type { Verdict } from '../types/enums';

interface VerdictBadgeProps {
  verdict: Verdict;
}

const VERDICT_META: Record<
  Verdict,
  { label: string; icon: string; bg: string; color: string; border: string }
> = {
  eligible: {
    label: '参加可能',
    icon: '✅',
    bg: '#d1fae5',
    color: '#065f46',
    border: '#34d399',
  },
  ineligible: {
    label: '参加不可',
    icon: '❌',
    bg: '#fee2e2',
    color: '#991b1b',
    border: '#f87171',
  },
  uncertain: {
    label: '確認必要',
    icon: '⚠️',
    bg: '#fff7ed',
    color: '#9a3412',
    border: '#fb923c',
  },
};

export default function VerdictBadge({ verdict }: VerdictBadgeProps) {
  const meta = VERDICT_META[verdict] ?? VERDICT_META.uncertain;

  return (
    <span
      data-testid="verdict-badge"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '4px 10px',
        borderRadius: 6,
        fontSize: '0.875rem',
        fontWeight: 700,
        backgroundColor: meta.bg,
        color: meta.color,
        border: `1px solid ${meta.border}`,
      }}
    >
      {meta.icon} {meta.label}
    </span>
  );
}
