/**
 * ChecklistTab — checklist management tab (SSOT-2 §6-5).
 *
 * Shows: progress bar, checklist items grouped by phase (bid_time / performance_time),
 * schedule timeline, warnings, and item check/uncheck toggles.
 */

import { useCallback } from 'react';
import type { Checklist, ChecklistItem, ScheduleItem } from '../types/case';

interface ChecklistTabProps {
  checklist: Checklist;
  onToggleItem: (itemId: string, checked: boolean) => void;
}

// ---- Progress bar ----

function ProgressBar({ total, done, rate }: { total: number; done: number; rate: number }) {
  const pct = Math.round(rate * 100);
  const barColor = pct === 100 ? '#059669' : '#2563eb';

  return (
    <div data-testid="checklist-progress">
      <div style={progressHeaderStyle}>
        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>進捗</span>
        <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>
          {done} / {total} ({pct}%)
        </span>
      </div>
      <div style={progressBarBgStyle}>
        <div
          data-testid="progress-fill"
          style={{
            ...progressBarFillStyle,
            width: `${pct}%`,
            backgroundColor: barColor,
          }}
        />
      </div>
    </div>
  );
}

// ---- Warnings ----

function WarningsList({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <div data-testid="checklist-warnings" style={warningsStyle}>
      {warnings.map((w, i) => (
        <div key={i} style={warningItemStyle}>⚠️ {w}</div>
      ))}
    </div>
  );
}

// ---- Schedule timeline ----

function ScheduleTimeline({ items }: { items: ScheduleItem[] }) {
  if (items.length === 0) return null;

  return (
    <div data-testid="schedule-timeline">
      <h4 style={sectionHeaderStyle}>スケジュール</h4>
      <div style={timelineContainerStyle}>
        {items.map((item, i) => (
          <div key={i} style={timelineItemStyle}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: item.is_critical ? '#dc2626' : '#3b82f6',
                flexShrink: 0,
              }} />
              <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{item.name}</span>
              {item.is_critical && (
                <span style={criticalBadgeStyle}>重要</span>
              )}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#6b7280', paddingLeft: 14 }}>
              {new Date(item.date).toLocaleDateString('ja-JP')}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Checklist item ----

function ChecklistItemRow({
  item,
  onToggle,
}: {
  item: ChecklistItem;
  onToggle: (itemId: string, checked: boolean) => void;
}) {
  const handleChange = useCallback(() => {
    onToggle(item.item_id, !item.is_checked);
  }, [item.item_id, item.is_checked, onToggle]);

  return (
    <div
      data-testid={`checklist-item-${item.item_id}`}
      style={{
        ...itemRowStyle,
        opacity: item.is_checked ? 0.7 : 1,
      }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <input
          type="checkbox"
          checked={item.is_checked}
          onChange={handleChange}
          data-testid={`checkbox-${item.item_id}`}
          style={{ marginTop: 2 }}
        />
        <div style={{ flex: 1 }}>
          <div style={{
            fontWeight: 600,
            fontSize: '0.85rem',
            textDecoration: item.is_checked ? 'line-through' : 'none',
            color: item.is_checked ? '#9ca3af' : '#1f2937',
          }}>
            {item.name}
            {item.is_critical && (
              <span style={{ ...criticalBadgeStyle, marginLeft: 6 }}>必須</span>
            )}
            {item.source === 'manual' && (
              <span style={manualBadgeStyle}>手動</span>
            )}
          </div>
          {item.deadline && (
            <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
              期限: {new Date(item.deadline).toLocaleDateString('ja-JP')}
            </div>
          )}
          {item.notes && (
            <div style={{ fontSize: '0.8rem', color: '#6b7280', fontStyle: 'italic' }}>
              {item.notes}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---- Main component ----

export default function ChecklistTab({ checklist, onToggleItem }: ChecklistTabProps) {
  const bidTimeItems = checklist.checklist_items.filter((i) => i.phase === 'bid_time');
  const perfTimeItems = checklist.checklist_items.filter((i) => i.phase === 'performance_time');

  return (
    <div data-testid="checklist-tab">
      {/* Progress bar */}
      <ProgressBar
        total={checklist.progress.total}
        done={checklist.progress.done}
        rate={checklist.progress.rate}
      />

      {/* Warnings */}
      <WarningsList warnings={checklist.warnings} />

      {/* Schedule timeline */}
      <ScheduleTimeline items={checklist.schedule_items} />

      {/* Bid-time items */}
      {bidTimeItems.length > 0 && (
        <div data-testid="bid-time-items">
          <h4 style={sectionHeaderStyle}>入札参加時の準備</h4>
          {bidTimeItems.map((item) => (
            <ChecklistItemRow key={item.item_id} item={item} onToggle={onToggleItem} />
          ))}
        </div>
      )}

      {/* Performance-time items */}
      {perfTimeItems.length > 0 && (
        <div data-testid="performance-time-items">
          <h4 style={sectionHeaderStyle}>履行時の準備</h4>
          {perfTimeItems.map((item) => (
            <ChecklistItemRow key={item.item_id} item={item} onToggle={onToggleItem} />
          ))}
        </div>
      )}

      {/* Meta info */}
      <div style={metaStyle}>
        バージョン: {checklist.version} | 生成日:{' '}
        {new Date(checklist.generated_at).toLocaleString('ja-JP')}
        {checklist.completed_at && (
          <> | 完了日: {new Date(checklist.completed_at).toLocaleString('ja-JP')}</>
        )}
      </div>
    </div>
  );
}

// ---- Styles ----

const progressHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  marginBottom: 4,
};

const progressBarBgStyle: React.CSSProperties = {
  width: '100%',
  height: 8,
  backgroundColor: '#e5e7eb',
  borderRadius: 4,
  overflow: 'hidden',
};

const progressBarFillStyle: React.CSSProperties = {
  height: '100%',
  borderRadius: 4,
  transition: 'width 0.3s ease',
};

const warningsStyle: React.CSSProperties = {
  margin: '12px 0',
};

const warningItemStyle: React.CSSProperties = {
  padding: '6px 10px',
  marginBottom: 4,
  backgroundColor: '#fef3c7',
  borderRadius: 4,
  fontSize: '0.85rem',
  color: '#92400e',
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: '0.9rem',
  fontWeight: 700,
  color: '#1f2937',
  margin: '16px 0 8px',
  paddingBottom: 4,
  borderBottom: '1px solid #e5e7eb',
};

const timelineContainerStyle: React.CSSProperties = {
  padding: '4px 0',
};

const timelineItemStyle: React.CSSProperties = {
  padding: '4px 0',
};

const criticalBadgeStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '0px 4px',
  borderRadius: 3,
  fontSize: '0.7rem',
  fontWeight: 700,
  backgroundColor: '#fee2e2',
  color: '#991b1b',
};

const manualBadgeStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '0px 4px',
  borderRadius: 3,
  fontSize: '0.7rem',
  fontWeight: 600,
  backgroundColor: '#e0e7ff',
  color: '#3730a3',
  marginLeft: 6,
};

const itemRowStyle: React.CSSProperties = {
  padding: '6px 0',
  borderBottom: '1px solid #f3f4f6',
};

const metaStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#9ca3af',
  marginTop: 16,
  padding: '8px 0',
  borderTop: '1px solid #e5e7eb',
};
