/**
 * Tests for HistoryTab — TASK-45.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const baseEvents = [
  {
    id: 'evt-1',
    case_id: 'c1',
    event_type: 'lifecycle_transition',
    from_status: 'new',
    to_status: 'scored',
    triggered_by: 'system',
    actor_id: 'system',
    feature_origin: 'F-001',
    payload: { score: 85 },
    created_at: '2026-02-01T00:00:00Z',
  },
  {
    id: 'evt-2',
    case_id: 'c1',
    event_type: 'reading_completed',
    from_status: 'reading_in_progress',
    to_status: 'reading_completed',
    triggered_by: 'system',
    actor_id: 'system',
    feature_origin: 'F-002',
    payload: { confidence_score: 0.85 },
    created_at: '2026-02-02T06:15:00Z',
  },
  {
    id: 'evt-3',
    case_id: 'c1',
    event_type: 'mark_planned',
    from_status: 'under_review',
    to_status: 'planned',
    triggered_by: 'user',
    actor_id: 'user-1',
    feature_origin: 'F-001',
    payload: null,
    created_at: '2026-02-03T10:00:00Z',
  },
  {
    id: 'evt-4',
    case_id: 'c1',
    event_type: 'reading_failed',
    from_status: 'reading_in_progress',
    to_status: 'reading_failed',
    triggered_by: 'system',
    actor_id: 'system',
    feature_origin: 'F-002',
    payload: { error: 'timeout' },
    created_at: '2026-02-04T12:00:00Z',
  },
];

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
  current_lifecycle_stage: 'under_review',
  score: 85,
  score_detail: { competition: 25, scale: 20, margin: 22, fit: 18 },
  first_seen_at: '2026-02-01T00:00:00Z',
  last_updated_at: '2026-02-01T00:00:00Z',
  card: null,
  eligibility: null,
  checklist: null,
  latest_events: baseEvents,
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

async function switchToHistoryTab() {
  await waitFor(() => {
    expect(screen.getByTestId('tab-history')).toBeInTheDocument();
  });
  await userEvent.click(screen.getByTestId('tab-history'));
}

// ---- Event list ----

describe('HistoryTab — EventList', () => {
  it('renders event count', async () => {
    setupMock();
    renderCaseDetail();
    await switchToHistoryTab();
    const tab = screen.getByTestId('history-tab');
    expect(tab).toHaveTextContent('4件');
  });

  it('renders all events', async () => {
    setupMock();
    renderCaseDetail();
    await switchToHistoryTab();
    expect(screen.getByTestId('event-evt-1')).toBeInTheDocument();
    expect(screen.getByTestId('event-evt-2')).toBeInTheDocument();
    expect(screen.getByTestId('event-evt-3')).toBeInTheDocument();
    expect(screen.getByTestId('event-evt-4')).toBeInTheDocument();
  });

  it('shows event type labels', async () => {
    setupMock();
    renderCaseDetail();
    await switchToHistoryTab();
    expect(screen.getByTestId('event-evt-1')).toHaveTextContent('ステージ遷移');
    expect(screen.getByTestId('event-evt-2')).toHaveTextContent('AI読解完了');
    expect(screen.getByTestId('event-evt-3')).toHaveTextContent('応札予定に設定');
    expect(screen.getByTestId('event-evt-4')).toHaveTextContent('AI読解失敗');
  });

  it('shows stage transitions', async () => {
    setupMock();
    renderCaseDetail();
    await switchToHistoryTab();
    expect(screen.getByTestId('event-evt-1')).toHaveTextContent('new → scored');
  });

  it('shows trigger labels', async () => {
    setupMock();
    renderCaseDetail();
    await switchToHistoryTab();
    expect(screen.getByTestId('event-evt-1')).toHaveTextContent('システム');
    expect(screen.getByTestId('event-evt-3')).toHaveTextContent('ユーザー');
  });

  it('shows payload data', async () => {
    setupMock();
    renderCaseDetail();
    await switchToHistoryTab();
    expect(screen.getByTestId('event-evt-1')).toHaveTextContent('score: 85');
  });
});

// ---- Empty state ----

describe('HistoryTab — EmptyState', () => {
  it('shows empty state when no events', async () => {
    setupMock({ ...baseCaseData, latest_events: [] });
    renderCaseDetail();
    await switchToHistoryTab();
    expect(screen.getByTestId('history-empty')).toHaveTextContent(
      'イベント履歴はまだありません',
    );
  });
});

// ---- Feature origin ----

describe('HistoryTab — FeatureOrigin', () => {
  it('shows feature origin', async () => {
    setupMock();
    renderCaseDetail();
    await switchToHistoryTab();
    expect(screen.getByTestId('event-evt-1')).toHaveTextContent('F-001');
  });
});
