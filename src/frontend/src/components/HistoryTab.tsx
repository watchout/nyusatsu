/**
 * HistoryTab — case event history tab (SSOT-2 §6-5).
 *
 * Shows timeline of CaseEvents: lifecycle transitions, actions, and folded
 * check operations. Events are ordered newest-first.
 */

import type { CaseEvent, FoldedCheckOperations } from '../types/case';
import type { TriggeredBy } from '../types/enums';

interface HistoryTabProps {
  events: CaseEvent[];
}

// ---- Event card ----

const TRIGGER_LABELS: Record<TriggeredBy, string> = {
  system: 'システム',
  user: 'ユーザー',
  batch: 'バッチ',
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  lifecycle_transition: 'ステージ遷移',
  scoring_completed: 'スコアリング完了',
  reading_started: 'AI読解開始',
  reading_completed: 'AI読解完了',
  reading_failed: 'AI読解失敗',
  judging_started: '判定開始',
  judging_completed: '判定完了',
  judging_failed: '判定失敗',
  eligibility_overridden: '判定上書き',
  checklist_generated: 'チェックリスト生成',
  checklist_completed: 'チェックリスト完了',
  checklist_item_checked: 'チェック済み',
  checklist_item_unchecked: 'チェック解除',
  case_archived: 'アーカイブ',
  case_restored: '復帰',
  mark_planned: '応札予定に設定',
  mark_skipped: '見送り設定',
  _folded_check_operations: 'チェック操作',
};

function getEventTypeColor(eventType: string): { bg: string; text: string; dot: string } {
  if (eventType.includes('failed')) {
    return { bg: '#fef2f2', text: '#991b1b', dot: '#ef4444' };
  }
  if (eventType.includes('completed') || eventType.includes('generated')) {
    return { bg: '#ecfdf5', text: '#065f46', dot: '#10b981' };
  }
  if (eventType.includes('started') || eventType.includes('queued')) {
    return { bg: '#eff6ff', text: '#1e40af', dot: '#3b82f6' };
  }
  if (eventType.includes('archived') || eventType.includes('skipped')) {
    return { bg: '#f3f4f6', text: '#374151', dot: '#6b7280' };
  }
  if (eventType.includes('override')) {
    return { bg: '#fffbeb', text: '#92400e', dot: '#f59e0b' };
  }
  return { bg: '#f9fafb', text: '#374151', dot: '#9ca3af' };
}

function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString('ja-JP', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function isFolded(event: CaseEvent | FoldedCheckOperations): event is FoldedCheckOperations {
  return event.event_type === '_folded_check_operations';
}

function EventCard({ event }: { event: CaseEvent }) {
  const colors = getEventTypeColor(event.event_type);
  const label = EVENT_TYPE_LABELS[event.event_type] ?? event.event_type;
  const trigger = TRIGGER_LABELS[event.triggered_by] ?? event.triggered_by;

  return (
    <div data-testid={`event-${event.id}`} style={{ ...eventCardStyle, backgroundColor: colors.bg }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <span style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          backgroundColor: colors.dot,
          flexShrink: 0,
          marginTop: 4,
        }} />
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: '0.85rem', color: colors.text }}>
              {label}
            </span>
            <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
              {formatTimestamp(event.created_at)}
            </span>
          </div>

          {/* Stage transition */}
          {event.from_status && event.to_status && (
            <div style={transitionStyle}>
              {event.from_status} → {event.to_status}
            </div>
          )}

          {/* Trigger + actor */}
          <div style={metaRowStyle}>
            <span style={triggerBadgeStyle}>{trigger}</span>
            {event.feature_origin && (
              <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                {event.feature_origin}
              </span>
            )}
          </div>

          {/* Payload summary */}
          {event.payload && Object.keys(event.payload).length > 0 && (
            <div style={payloadStyle}>
              {Object.entries(event.payload)
                .filter(([, v]) => v !== null && v !== undefined)
                .slice(0, 3)
                .map(([k, v]) => (
                  <span key={k} style={{ marginRight: 8 }}>
                    {k}: {String(v)}
                  </span>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FoldedEventCard({ event }: { event: FoldedCheckOperations }) {
  const colors = getEventTypeColor(event.event_type);

  return (
    <div data-testid="folded-event" style={{ ...eventCardStyle, backgroundColor: colors.bg }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          backgroundColor: colors.dot,
          flexShrink: 0,
        }} />
        <div>
          <span style={{ fontWeight: 600, fontSize: '0.85rem', color: colors.text }}>
            チェック操作 ({event.count}件)
          </span>
          <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
            {formatTimestamp(event.first_at)} 〜 {formatTimestamp(event.last_at)}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Main component ----

export default function HistoryTab({ events }: HistoryTabProps) {
  if (events.length === 0) {
    return (
      <div data-testid="history-tab">
        <div data-testid="history-empty" style={emptyStyle}>
          イベント履歴はまだありません。
        </div>
      </div>
    );
  }

  return (
    <div data-testid="history-tab">
      <div style={headerStyle}>
        <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>イベント履歴</span>
        <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          {events.length}件
        </span>
      </div>
      <div style={timelineStyle}>
        {events.map((event, i) =>
          isFolded(event) ? (
            <FoldedEventCard key={`folded-${i}`} event={event} />
          ) : (
            <EventCard key={event.id} event={event} />
          ),
        )}
      </div>
    </div>
  );
}

// ---- Styles ----

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '4px 0 8px',
  borderBottom: '1px solid #e5e7eb',
  marginBottom: 8,
};

const timelineStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
};

const eventCardStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderRadius: 6,
};

const transitionStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  color: '#6b7280',
  fontFamily: 'monospace',
  marginTop: 2,
};

const metaRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  alignItems: 'center',
  marginTop: 2,
};

const triggerBadgeStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '0px 4px',
  borderRadius: 3,
  fontSize: '0.7rem',
  fontWeight: 600,
  backgroundColor: '#e5e7eb',
  color: '#374151',
};

const payloadStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#6b7280',
  marginTop: 4,
  fontFamily: 'monospace',
};

const emptyStyle: React.CSSProperties = {
  color: '#6b7280',
  fontSize: '0.9rem',
  padding: 16,
  textAlign: 'center',
};
