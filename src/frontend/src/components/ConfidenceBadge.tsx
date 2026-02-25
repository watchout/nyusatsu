/**
 * ConfidenceBadge — displays confidence score with color coding (SSOT-2 §7-2).
 *
 * red:    < 0.4
 * yellow: 0.4–0.6
 * green:  > 0.6
 */

interface ConfidenceBadgeProps {
  score: number | null;
}

function getColor(score: number): { bg: string; text: string } {
  if (score < 0.4) return { bg: '#fee2e2', text: '#991b1b' };
  if (score <= 0.6) return { bg: '#fef3c7', text: '#92400e' };
  return { bg: '#d1fae5', text: '#065f46' };
}

export default function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  if (score === null || score === undefined) return null;

  const { bg, text } = getColor(score);
  const pct = Math.round(score * 100);

  return (
    <span
      data-testid="confidence-badge"
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: '0.8rem',
        fontWeight: 600,
        backgroundColor: bg,
        color: text,
      }}
    >
      信頼度 {pct}%
    </span>
  );
}
