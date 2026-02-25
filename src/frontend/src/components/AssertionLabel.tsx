/**
 * AssertionLabel — displays assertion_type labels (SSOT-2 §7-2, F-002 §3-B-2).
 *
 * fact:     normal display (gray)
 * inferred: ⚠️ yellow "推定" label
 * caution:  ⚠️ red "注意" label
 */

type AssertionType = 'fact' | 'inferred' | 'caution';

interface AssertionLabelProps {
  type: AssertionType;
}

const LABEL_MAP: Record<
  AssertionType,
  { label: string; bg: string; color: string; icon: string }
> = {
  fact: { label: '確認済み', bg: '#f3f4f6', color: '#374151', icon: '' },
  inferred: { label: '推定', bg: '#fef3c7', color: '#92400e', icon: '⚠️ ' },
  caution: { label: '注意', bg: '#fee2e2', color: '#991b1b', icon: '⚠️ ' },
};

export default function AssertionLabel({ type }: AssertionLabelProps) {
  const meta = LABEL_MAP[type] ?? LABEL_MAP.fact;

  return (
    <span
      data-testid={`assertion-${type}`}
      style={{
        display: 'inline-block',
        padding: '1px 6px',
        borderRadius: 3,
        fontSize: '0.75rem',
        fontWeight: 600,
        backgroundColor: meta.bg,
        color: meta.color,
      }}
    >
      {meta.icon}{meta.label}
    </span>
  );
}
