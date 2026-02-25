/**
 * Tests for TypeScript types and enums — TASK-39.
 *
 * Validates enum completeness, helper functions, and type constraints.
 */

import { describe, it, expect } from 'vitest';
import {
  LIFECYCLE_STAGES,
  STAGE_GROUPS,
  STAGE_META,
  isProcessingStage,
  isStableStage,
  isFailedStage,
} from '../src/types/enums';

describe('LifecycleStage enums', () => {
  it('has exactly 17 stages', () => {
    expect(LIFECYCLE_STAGES).toHaveLength(17);
  });

  it('starts with discovered and ends with archived', () => {
    expect(LIFECYCLE_STAGES[0]).toBe('discovered');
    expect(LIFECYCLE_STAGES[LIFECYCLE_STAGES.length - 1]).toBe('archived');
  });
});

describe('STAGE_GROUPS', () => {
  it('covers all 17 stages exactly once', () => {
    const allStages = Object.values(STAGE_GROUPS).flat();
    expect(allStages).toHaveLength(17);
    expect(new Set(allStages).size).toBe(17);
    // Every stage in LIFECYCLE_STAGES should be in a group
    for (const stage of LIFECYCLE_STAGES) {
      expect(allStages).toContain(stage);
    }
  });

  it('Discovery group has 5 stages', () => {
    expect(STAGE_GROUPS.Discovery).toHaveLength(5);
  });

  it('Reading group has 4 stages', () => {
    expect(STAGE_GROUPS.Reading).toHaveLength(4);
  });

  it('Judging group has 4 stages', () => {
    expect(STAGE_GROUPS.Judging).toHaveLength(4);
  });

  it('Preparation group has 3 stages', () => {
    expect(STAGE_GROUPS.Preparation).toHaveLength(3);
  });
});

describe('STAGE_META', () => {
  it('has metadata for all 17 stages', () => {
    const metaKeys = Object.keys(STAGE_META);
    expect(metaKeys).toHaveLength(17);
    for (const stage of LIFECYCLE_STAGES) {
      expect(STAGE_META[stage]).toBeDefined();
      expect(STAGE_META[stage].label).toBeTruthy();
      expect(STAGE_META[stage].color).toBeTruthy();
    }
  });

  it('marks processing stages with pulse', () => {
    expect(STAGE_META.reading_in_progress.pulse).toBe(true);
    expect(STAGE_META.judging_in_progress.pulse).toBe(true);
    expect(STAGE_META.checklist_generating.pulse).toBe(true);
  });

  it('does not pulse stable stages', () => {
    expect(STAGE_META.reading_completed.pulse).toBeUndefined();
    expect(STAGE_META.scored.pulse).toBeUndefined();
  });
});

describe('isProcessingStage', () => {
  it('returns true for queued stages', () => {
    expect(isProcessingStage('reading_queued')).toBe(true);
    expect(isProcessingStage('judging_queued')).toBe(true);
  });

  it('returns true for in_progress stages', () => {
    expect(isProcessingStage('reading_in_progress')).toBe(true);
    expect(isProcessingStage('judging_in_progress')).toBe(true);
  });

  it('returns true for checklist_generating', () => {
    expect(isProcessingStage('checklist_generating')).toBe(true);
  });

  it('returns false for stable stages', () => {
    expect(isProcessingStage('scored')).toBe(false);
    expect(isProcessingStage('reading_completed')).toBe(false);
    expect(isProcessingStage('checklist_active')).toBe(false);
    expect(isProcessingStage('archived')).toBe(false);
  });
});

describe('isStableStage', () => {
  it('is the inverse of isProcessingStage', () => {
    for (const stage of LIFECYCLE_STAGES) {
      expect(isStableStage(stage)).toBe(!isProcessingStage(stage));
    }
  });
});

describe('isFailedStage', () => {
  it('returns true for failed stages', () => {
    expect(isFailedStage('reading_failed')).toBe(true);
    expect(isFailedStage('judging_failed')).toBe(true);
  });

  it('returns false for non-failed stages', () => {
    expect(isFailedStage('reading_completed')).toBe(false);
    expect(isFailedStage('scored')).toBe(false);
    expect(isFailedStage('checklist_active')).toBe(false);
  });
});
