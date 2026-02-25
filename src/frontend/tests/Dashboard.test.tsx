/**
 * Tests for Dashboard page — TASK-40.
 *
 * Tests rendering, empty state, case list, filters, pagination, and batch status.
 */

import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

// ---------------------------------------------------------------------------
// Mock fetch
// ---------------------------------------------------------------------------

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function mockCasesResponse(
  cases: Record<string, unknown>[] = [],
  total = 0,
  totalPages = 0,
) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        data: cases,
        meta: { page: 1, limit: 20, total, total_pages: totalPages },
      }),
  };
}

function mockBatchResponse(data: Record<string, unknown> | null = null) {
  return {
    ok: true,
    json: () => Promise.resolve({ data }),
  };
}

function setupMocks(
  cases: Record<string, unknown>[] = [],
  total = 0,
  totalPages = 0,
  batch: Record<string, unknown> | null = null,
) {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/api/v1/cases')) {
      return Promise.resolve(mockCasesResponse(cases, total, totalPages));
    }
    if (url.includes('/api/v1/batch/latest')) {
      return Promise.resolve(mockBatchResponse(batch));
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: null }) });
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Dashboard', () => {
  it('renders the Dashboard heading', async () => {
    setupMocks();
    await act(async () => {
      renderDashboard();
    });
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
  });

  it('shows empty state when no cases', async () => {
    setupMocks([], 0, 0);
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getByTestId('case-list-empty')).toBeInTheDocument();
    });
  });

  it('renders case list with items', async () => {
    const cases = [
      {
        id: 'c1',
        case_name: '配送業務委託',
        issuing_org: '○○省',
        current_lifecycle_stage: 'scored',
        score: 85,
        submission_deadline: '2026-03-15T17:00:00Z',
        status: 'new',
        source: 'test',
        source_id: 'T-001',
        first_seen_at: '2026-02-01T00:00:00Z',
        last_updated_at: '2026-02-01T00:00:00Z',
        bid_type: null,
        category: null,
        region: null,
        grade: null,
        opening_date: null,
        score_detail: null,
      },
      {
        id: 'c2',
        case_name: '事務用品調達',
        issuing_org: '○○局',
        current_lifecycle_stage: 'judging_in_progress',
        score: 72,
        submission_deadline: '2026-03-20T17:00:00Z',
        status: 'planned',
        source: 'test',
        source_id: 'T-002',
        first_seen_at: '2026-02-01T00:00:00Z',
        last_updated_at: '2026-02-01T00:00:00Z',
        bid_type: null,
        category: null,
        region: null,
        grade: null,
        opening_date: null,
        score_detail: null,
      },
    ];
    setupMocks(cases, 2, 1);
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getAllByTestId('case-row')).toHaveLength(2);
    });
    expect(screen.getByText('配送業務委託')).toBeInTheDocument();
    expect(screen.getByText('事務用品調達')).toBeInTheDocument();
  });

  it('displays score badges', async () => {
    setupMocks(
      [
        {
          id: 'c1',
          case_name: 'Test',
          issuing_org: 'Org',
          current_lifecycle_stage: 'scored',
          score: 85,
          submission_deadline: null,
          status: 'new',
          source: 'test',
          source_id: 'T-001',
          first_seen_at: '2026-02-01T00:00:00Z',
          last_updated_at: '2026-02-01T00:00:00Z',
          bid_type: null,
          category: null,
          region: null,
          grade: null,
          opening_date: null,
          score_detail: null,
        },
      ],
      1,
      1,
    );
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getByTestId('score-badge')).toHaveTextContent('85');
    });
  });

  it('displays stage badges', async () => {
    setupMocks(
      [
        {
          id: 'c1',
          case_name: 'Test',
          issuing_org: 'Org',
          current_lifecycle_stage: 'scored',
          score: 50,
          submission_deadline: null,
          status: 'new',
          source: 'test',
          source_id: 'T-001',
          first_seen_at: '2026-02-01T00:00:00Z',
          last_updated_at: '2026-02-01T00:00:00Z',
          bid_type: null,
          category: null,
          region: null,
          grade: null,
          opening_date: null,
          score_detail: null,
        },
      ],
      1,
      1,
    );
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getByTestId('stage-badge')).toHaveTextContent('スコア済');
    });
  });

  it('renders batch status bar', async () => {
    setupMocks([], 0, 0, {
      id: 'b1',
      status: 'success',
      started_at: '2026-02-25T06:00:00Z',
      new_count: 5,
      source: 'chotatku_portal',
      feature_origin: 'F-001',
      batch_type: 'case_fetch',
      total_fetched: 10,
      updated_count: 2,
      unchanged_count: 3,
      error_count: 0,
    });
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      const el = screen.getByTestId('batch-status');
      expect(el).toBeInTheDocument();
    });
  });

  it('renders filter controls', async () => {
    setupMocks();
    await act(async () => {
      renderDashboard();
    });
    expect(screen.getByTestId('case-filters')).toBeInTheDocument();
    expect(screen.getByTestId('filter-group')).toBeInTheDocument();
    expect(screen.getByTestId('filter-sort')).toBeInTheDocument();
    expect(screen.getByTestId('filter-search')).toBeInTheDocument();
  });

  it('renders pagination controls', async () => {
    const cases = Array.from({ length: 3 }, (_, i) => ({
      id: `c${i}`,
      case_name: `Case ${i}`,
      issuing_org: 'Org',
      current_lifecycle_stage: 'scored',
      score: 50,
      submission_deadline: null,
      status: 'new',
      source: 'test',
      source_id: `T-${i}`,
      first_seen_at: '2026-02-01T00:00:00Z',
      last_updated_at: '2026-02-01T00:00:00Z',
      bid_type: null,
      category: null,
      region: null,
      grade: null,
      opening_date: null,
      score_detail: null,
    }));
    setupMocks(cases, 50, 3);
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getByTestId('pagination')).toBeInTheDocument();
      expect(screen.getByText('全 50 件')).toBeInTheDocument();
      expect(screen.getByText('1 / 3')).toBeInTheDocument();
    });
  });

  it('calls API with sort parameter', async () => {
    setupMocks();
    await act(async () => {
      renderDashboard();
    });
    // Default sort is score:desc
    const casesCall = mockFetch.mock.calls.find((c: string[]) =>
      c[0].includes('/api/v1/cases'),
    );
    expect(casesCall).toBeDefined();
    expect(casesCall![0]).toContain('sort=score%3Adesc');
  });

  it('sends search parameter when filter is set', async () => {
    setupMocks();
    await act(async () => {
      renderDashboard();
    });

    const searchInput = screen.getByTestId('filter-search');
    await act(async () => {
      await userEvent.type(searchInput, '配送');
    });

    // Wait for the API call with search param
    await waitFor(() => {
      const calls = mockFetch.mock.calls.filter((c: string[]) =>
        c[0].includes('/api/v1/cases') && c[0].includes('search'),
      );
      expect(calls.length).toBeGreaterThan(0);
    });
  });

  it('shows batch trigger button', async () => {
    setupMocks();
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getByTestId('batch-trigger-btn')).toBeInTheDocument();
    });
    expect(screen.getByTestId('batch-trigger-btn')).toHaveTextContent('バッチ実行');
  });

  it('calls POST /batch/trigger when button is clicked', async () => {
    setupMocks();
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getByTestId('batch-trigger-btn')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByTestId('batch-trigger-btn'));

    await waitFor(() => {
      const triggerCalls = mockFetch.mock.calls.filter(
        (c: unknown[]) =>
          String(c[0]).includes('/api/v1/batch/trigger'),
      );
      expect(triggerCalls.length).toBeGreaterThan(0);
      // Verify it was a POST request
      const opts = triggerCalls[0][1] as Record<string, unknown> | undefined;
      expect(opts?.method).toBe('POST');
    });
  });

  it('disables trigger button when batch is running', async () => {
    setupMocks([], 0, 0, {
      id: 'b1',
      status: 'running',
      started_at: '2026-02-25T06:00:00Z',
      new_count: 0,
      source: 'chotatku_portal',
      feature_origin: 'F-001',
      batch_type: 'case_fetch',
      total_fetched: 0,
      updated_count: 0,
      unchanged_count: 0,
      error_count: 0,
    });
    await act(async () => {
      renderDashboard();
    });
    await waitFor(() => {
      expect(screen.getByTestId('batch-trigger-btn')).toBeInTheDocument();
    });
    expect(screen.getByTestId('batch-trigger-btn')).toBeDisabled();
  });
});
