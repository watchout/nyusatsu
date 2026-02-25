/**
 * Tests for ChecklistTab — TASK-44.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const baseChecklist = {
  id: 'cl-1',
  case_id: 'c1',
  case_card_id: 'card-1',
  eligibility_result_id: 'elig-1',
  version: 1,
  is_current: true,
  checklist_items: [
    {
      item_id: 'item-1',
      name: '入札書の準備',
      phase: 'bid_time',
      is_checked: false,
      status: 'pending',
      deadline: '2026-03-15T17:00:00Z',
      is_critical: true,
      notes: '機関指定書式を使用',
      source: 'ai',
    },
    {
      item_id: 'item-2',
      name: '全省庁統一資格の確認',
      phase: 'bid_time',
      is_checked: true,
      status: 'done',
      deadline: null,
      is_critical: false,
      notes: null,
      source: 'ai',
    },
    {
      item_id: 'item-3',
      name: '納品報告書テンプレート作成',
      phase: 'performance_time',
      is_checked: false,
      status: 'pending',
      deadline: null,
      is_critical: false,
      notes: '毎月末提出',
      source: 'manual',
    },
  ],
  schedule_items: [
    { name: '仕様説明会', date: '2026-03-01T14:00:00Z', is_critical: false },
    { name: '入札書提出期限', date: '2026-03-15T17:00:00Z', is_critical: true },
    { name: '開札日', date: '2026-03-20T10:00:00Z', is_critical: true },
  ],
  warnings: ['下見積もり期限が迫っています（残り2日）'],
  progress: { total: 3, done: 1, rate: 0.333 },
  status: 'active',
  generated_at: '2026-03-02T12:00:00Z',
  completed_at: null,
  created_at: '2026-03-02T12:00:00Z',
};

const baseCaseData = {
  id: 'c1',
  source: 'test',
  source_id: 'T-001',
  case_name: '配送業務委託',
  issuing_org: '○○省',
  bid_type: '一般競争入札',
  category: '役務の提供',
  region: '関東',
  grade: 'D',
  submission_deadline: '2026-03-15T17:00:00Z',
  opening_date: null,
  spec_url: null,
  notice_url: null,
  detail_url: null,
  status: 'new',
  current_lifecycle_stage: 'checklist_active',
  score: 85,
  score_detail: { competition: 25, scale: 20, margin: 22, fit: 18 },
  first_seen_at: '2026-02-01T00:00:00Z',
  last_updated_at: '2026-02-01T00:00:00Z',
  card: null,
  eligibility: null,
  checklist: baseChecklist,
  latest_events: [],
};

function setupMock(caseData: Record<string, unknown> = baseCaseData) {
  mockFetch.mockImplementation((...args: unknown[]) => {
    const url = String(args[0] ?? '');
    if (url.includes('/api/v1/cases/c1')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: caseData }),
      });
    }
    if (url.includes('/api/v1/batch/latest')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null }),
      });
    }
    if (url.includes('/api/v1/cases')) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [],
            meta: { page: 1, limit: 20, total: 0, total_pages: 0 },
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ data: null }),
    });
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

function renderCaseDetail() {
  return render(
    <MemoryRouter initialEntries={['/cases/c1']}>
      <App />
    </MemoryRouter>,
  );
}

async function switchToChecklistTab() {
  await waitFor(() => {
    expect(screen.getByTestId('tab-checklist')).toBeInTheDocument();
  });
  await userEvent.click(screen.getByTestId('tab-checklist'));
}

// ---- ProgressBar ----

describe('ChecklistTab — Progress', () => {
  it('shows progress bar with correct values', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const progress = screen.getByTestId('checklist-progress');
    expect(progress).toHaveTextContent('1 / 3');
    expect(progress).toHaveTextContent('33%');
  });

  it('renders progress fill element', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    expect(screen.getByTestId('progress-fill')).toBeInTheDocument();
  });
});

// ---- Warnings ----

describe('ChecklistTab — Warnings', () => {
  it('shows warnings', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const warnings = screen.getByTestId('checklist-warnings');
    expect(warnings).toHaveTextContent('下見積もり期限が迫っています');
  });
});

// ---- Schedule ----

describe('ChecklistTab — Schedule', () => {
  it('renders schedule timeline', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const timeline = screen.getByTestId('schedule-timeline');
    expect(timeline).toBeInTheDocument();
    expect(timeline).toHaveTextContent('仕様説明会');
    expect(timeline).toHaveTextContent('入札書提出期限');
    expect(timeline).toHaveTextContent('開札日');
  });

  it('marks critical schedule items', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const timeline = screen.getByTestId('schedule-timeline');
    // Two critical items
    const criticalBadges = timeline.querySelectorAll('span');
    const criticalLabels = Array.from(criticalBadges).filter(
      (el) => el.textContent === '重要',
    );
    expect(criticalLabels.length).toBe(2);
  });
});

// ---- Checklist items ----

describe('ChecklistTab — Items', () => {
  it('renders bid-time items section', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    expect(screen.getByTestId('bid-time-items')).toBeInTheDocument();
    expect(screen.getByTestId('bid-time-items')).toHaveTextContent('入札書の準備');
    expect(screen.getByTestId('bid-time-items')).toHaveTextContent('全省庁統一資格の確認');
  });

  it('renders performance-time items section', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    expect(screen.getByTestId('performance-time-items')).toBeInTheDocument();
    expect(screen.getByTestId('performance-time-items')).toHaveTextContent(
      '納品報告書テンプレート作成',
    );
  });

  it('shows checked state for completed items', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const checkbox = screen.getByTestId('checkbox-item-2') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('shows unchecked state for pending items', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const checkbox = screen.getByTestId('checkbox-item-1') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
  });

  it('shows critical badge on critical items', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const item = screen.getByTestId('checklist-item-item-1');
    expect(item).toHaveTextContent('必須');
  });

  it('shows manual badge on manual items', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const item = screen.getByTestId('checklist-item-item-3');
    expect(item).toHaveTextContent('手動');
  });

  it('shows deadline for items with deadline', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    const item = screen.getByTestId('checklist-item-item-1');
    expect(item).toHaveTextContent('期限:');
  });

  it('shows notes for items with notes', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    expect(screen.getByTestId('checklist-item-item-1')).toHaveTextContent('機関指定書式を使用');
  });
});

// ---- Empty state ----

describe('ChecklistTab — EmptyState', () => {
  it('shows empty state when no checklist', async () => {
    setupMock({ ...baseCaseData, checklist: null });
    renderCaseDetail();
    await switchToChecklistTab();
    expect(screen.getByTestId('tab-content-checklist')).toHaveTextContent(
      'チェックリストが自動生成されます',
    );
  });
});

// ---- Meta info ----

describe('ChecklistTab — Meta', () => {
  it('shows version and generated date', async () => {
    setupMock();
    renderCaseDetail();
    await switchToChecklistTab();
    expect(screen.getByTestId('checklist-tab')).toHaveTextContent('バージョン: 1');
  });
});
