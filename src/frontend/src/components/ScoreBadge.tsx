/**
 * ScoreBadge — color-coded score display (SSOT-2 §6-4).
 *
 * Colors: red (<40), yellow (40-69), green (>=70).
 */

interface ScoreBadgeProps {
  score: number | null;
}

function scoreColor(score: number): string {
  if (score >= 70) return '#16a34a'; // green
  if (score >= 40) return '#ca8a04'; // yellow
  return '#dc2626'; // red
}

export default function ScoreBadge({ score }: ScoreBadgeProps) {
  if (score === null) {
    return <span style={{ color: '#9ca3af' }}>—</span>;
  }

  return (
    <span
      data-testid="score-badge"
      style={{
        fontWeight: 700,
        color: scoreColor(score),
        fontSize: '1.1em',
      }}
    >
      {score}
    </span>
  );
}
