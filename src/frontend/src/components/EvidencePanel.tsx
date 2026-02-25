/**
 * EvidencePanel — displays source evidence for extracted fields (SSOT-2 §7-2).
 *
 * Shows quote, source location (page/section for PDF, heading_path for HTML),
 * and assertion_type for each evidence entry.
 */

import AssertionLabel from './AssertionLabel';

interface EvidenceEntry {
  source_type: 'pdf' | 'html';
  page?: number;
  section?: string;
  selector?: string;
  heading_path?: string;
  quote: string;
  assertion_type: 'fact' | 'inferred' | 'caution';
}

interface EvidencePanelProps {
  evidence: Record<string, unknown> | null;
  fieldKey: string;
}

function isEvidenceEntry(v: unknown): v is EvidenceEntry {
  if (typeof v !== 'object' || v === null) return false;
  const obj = v as Record<string, unknown>;
  return typeof obj.quote === 'string' && typeof obj.source_type === 'string';
}

function formatSource(entry: EvidenceEntry): string {
  if (entry.source_type === 'pdf') {
    const parts: string[] = [];
    if (entry.page !== undefined) parts.push(`p.${entry.page}`);
    if (entry.section) parts.push(entry.section);
    return parts.join(' — ') || 'PDF';
  }
  return entry.heading_path ?? entry.selector ?? 'HTML';
}

export default function EvidencePanel({ evidence, fieldKey }: EvidencePanelProps) {
  if (!evidence) return null;

  const entry = evidence[fieldKey];
  if (!entry) return null;

  // Evidence can be a single entry or an array
  const entries: EvidenceEntry[] = Array.isArray(entry)
    ? entry.filter(isEvidenceEntry)
    : isEvidenceEntry(entry)
      ? [entry]
      : [];

  if (entries.length === 0) return null;

  return (
    <div data-testid={`evidence-${fieldKey}`} style={panelStyle}>
      {entries.map((e, i) => (
        <div key={i} style={entryStyle}>
          <div style={sourceLineStyle}>
            <span style={sourceTagStyle}>{formatSource(e)}</span>
            <AssertionLabel type={e.assertion_type} />
          </div>
          <blockquote style={quoteStyle}>「{e.quote}」</blockquote>
        </div>
      ))}
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  marginTop: 4,
  padding: '6px 10px',
  backgroundColor: '#f9fafb',
  borderLeft: '3px solid #d1d5db',
  borderRadius: 4,
  fontSize: '0.8rem',
};

const entryStyle: React.CSSProperties = {
  marginBottom: 4,
};

const sourceLineStyle: React.CSSProperties = {
  display: 'flex',
  gap: 6,
  alignItems: 'center',
  marginBottom: 2,
};

const sourceTagStyle: React.CSSProperties = {
  color: '#6b7280',
  fontSize: '0.75rem',
};

const quoteStyle: React.CSSProperties = {
  margin: 0,
  padding: '2px 0',
  color: '#374151',
  fontStyle: 'italic',
};
