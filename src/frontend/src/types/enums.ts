/**
 * Enum types — SSOT-2 §2-1 / SSOT-3 §5-3.
 *
 * Must stay in sync with backend app/schemas/enums.py.
 */

// ---------------------------------------------------------------------------
// Lifecycle stages (17 values — SSOT-2 §2-1)
// ---------------------------------------------------------------------------

export type LifecycleStage =
  | 'discovered'
  | 'scored'
  | 'under_review'
  | 'planned'
  | 'skipped'
  | 'reading_queued'
  | 'reading_in_progress'
  | 'reading_completed'
  | 'reading_failed'
  | 'judging_queued'
  | 'judging_in_progress'
  | 'judging_completed'
  | 'judging_failed'
  | 'checklist_generating'
  | 'checklist_active'
  | 'checklist_completed'
  | 'archived';

export const LIFECYCLE_STAGES: readonly LifecycleStage[] = [
  'discovered',
  'scored',
  'under_review',
  'planned',
  'skipped',
  'reading_queued',
  'reading_in_progress',
  'reading_completed',
  'reading_failed',
  'judging_queued',
  'judging_in_progress',
  'judging_completed',
  'judging_failed',
  'checklist_generating',
  'checklist_active',
  'checklist_completed',
  'archived',
] as const;

// ---------------------------------------------------------------------------
// Stage groups (for filtering)
// ---------------------------------------------------------------------------

export type StageGroup =
  | 'Discovery'
  | 'Reading'
  | 'Judging'
  | 'Preparation'
  | 'Archive';

export const STAGE_GROUPS: Record<StageGroup, LifecycleStage[]> = {
  Discovery: ['discovered', 'scored', 'under_review', 'planned', 'skipped'],
  Reading: [
    'reading_queued',
    'reading_in_progress',
    'reading_completed',
    'reading_failed',
  ],
  Judging: [
    'judging_queued',
    'judging_in_progress',
    'judging_completed',
    'judging_failed',
  ],
  Preparation: ['checklist_generating', 'checklist_active', 'checklist_completed'],
  Archive: ['archived'],
};

// ---------------------------------------------------------------------------
// UI label & color mapping (SSOT-2 §2-1)
// ---------------------------------------------------------------------------

export interface StageMeta {
  label: string;
  color: string;
  pulse?: boolean;
}

export const STAGE_META: Record<LifecycleStage, StageMeta> = {
  discovered: { label: '新着', color: 'gray' },
  scored: { label: 'スコア済', color: 'blue' },
  under_review: { label: '確認中', color: 'blue' },
  planned: { label: '応札予定', color: 'indigo' },
  skipped: { label: '見送り', color: 'gray' },
  reading_queued: { label: '読解待ち', color: 'yellow' },
  reading_in_progress: { label: '読解中…', color: 'yellow', pulse: true },
  reading_completed: { label: '読解完了', color: 'green' },
  reading_failed: { label: '読解失敗', color: 'red' },
  judging_queued: { label: '判定待ち', color: 'yellow' },
  judging_in_progress: { label: '判定中…', color: 'yellow', pulse: true },
  judging_completed: { label: '判定完了', color: 'green' },
  judging_failed: { label: '判定失敗', color: 'red' },
  checklist_generating: { label: '生成中…', color: 'yellow', pulse: true },
  checklist_active: { label: '準備中', color: 'orange' },
  checklist_completed: { label: '準備完了', color: 'green' },
  archived: { label: 'アーカイブ', color: 'gray' },
};

// ---------------------------------------------------------------------------
// Other enums
// ---------------------------------------------------------------------------

export type CaseStatus = 'new' | 'reviewed' | 'planned' | 'skipped' | 'archived';

export type Verdict = 'eligible' | 'ineligible' | 'uncertain';

export type ChecklistItemStatus = 'pending' | 'done';

export type TriggeredBy = 'system' | 'user' | 'batch' | 'cascade';

export type SortField =
  | 'deadline_at'
  | 'score'
  | 'first_seen_at'
  | 'case_name'
  | 'needs_review';

export type SortDirection = 'asc' | 'desc';

export type RiskLevel = 'low' | 'medium' | 'high';

export type ExtractionMethod = 'text' | 'ocr' | 'text_failed';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** True when the stage indicates processing is in progress. */
export function isProcessingStage(stage: LifecycleStage): boolean {
  return (
    stage.endsWith('_queued') ||
    stage.endsWith('_in_progress') ||
    stage === 'checklist_generating'
  );
}

/** True when the stage represents a stable state. */
export function isStableStage(stage: LifecycleStage): boolean {
  return !isProcessingStage(stage);
}

/** True when the stage represents a failure. */
export function isFailedStage(stage: LifecycleStage): boolean {
  return stage.endsWith('_failed');
}
