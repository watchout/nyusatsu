/**
 * Tests for CaseDetail overview + action buttons — TASK-41.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

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

describe('CaseDetail — Overview', () => {
  it('renders case name in header', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '配送業務委託' })).toBeInTheDocument();
    });
  });

  it('shows stage badge', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('stage-badge')).toHaveTextContent('確認中');
    });
  });

  it('renders 5 tabs', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('tab-bar')).toBeInTheDocument();
    });
    expect(screen.getByTestId('tab-overview')).toBeInTheDocument();
    expect(screen.getByTestId('tab-reading')).toBeInTheDocument();
    expect(screen.getByTestId('tab-eligibility')).toBeInTheDocument();
    expect(screen.getByTestId('tab-checklist')).toBeInTheDocument();
    expect(screen.getByTestId('tab-history')).toBeInTheDocument();
  });

  it('shows overview tab content by default', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('case-overview')).toBeInTheDocument();
    });
    expect(screen.getByText('○○省')).toBeInTheDocument();
    expect(screen.getByText('一般競争入札')).toBeInTheDocument();
    expect(screen.getByText('役務の提供')).toBeInTheDocument();
  });

  it('displays score badge with value', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('score-badge')).toHaveTextContent('85');
    });
  });

  it('shows back link to dashboard', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByText('← 戻る')).toBeInTheDocument();
    });
  });
});

describe('CaseDetail — ActionButtons', () => {
  it('shows G1 and G2 buttons for under_review stage', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('action-mark_planned')).toBeInTheDocument();
    });
    expect(screen.getByTestId('action-mark_skipped')).toBeInTheDocument();
  });

  it('shows archive button on all non-archived stages', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('action-archive')).toBeInTheDocument();
    });
  });

  it('shows G3 retry button for reading_failed', async () => {
    setupMock({ ...baseCaseData, current_lifecycle_stage: 'reading_failed' });
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('action-retry_reading')).toBeInTheDocument();
    });
  });

  it('disables buttons during processing stages', async () => {
    setupMock({
      ...baseCaseData,
      current_lifecycle_stage: 'reading_in_progress',
    });
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('action-archive')).toBeInTheDocument();
    });
    // No gate buttons visible for reading_in_progress
    expect(
      screen.queryByTestId('action-mark_planned'),
    ).not.toBeInTheDocument();
  });

  it('hides G1/G2 on non-under_review stages', async () => {
    setupMock({ ...baseCaseData, current_lifecycle_stage: 'scored' });
    renderCaseDetail();
    // Wait for case to load
    await waitFor(() => {
      expect(screen.getByTestId('action-archive')).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId('action-mark_planned'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId('action-mark_skipped'),
    ).not.toBeInTheDocument();
  });
});

describe('CaseDetail — Tab switching', () => {
  it('switches to reading tab and shows empty state', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('tab-reading')).toBeInTheDocument();
    });
    await userEvent.click(screen.getByTestId('tab-reading'));
    expect(screen.getByTestId('tab-content-reading')).toHaveTextContent(
      'AI 読解されていません',
    );
  });

  it('switches to eligibility tab and shows empty state', async () => {
    setupMock();
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('tab-eligibility')).toBeInTheDocument();
    });
    await userEvent.click(screen.getByTestId('tab-eligibility'));
    expect(screen.getByTestId('tab-content-eligibility')).toHaveTextContent(
      '自動で判定が実行されます',
    );
  });

  it('shows error state when API fails', async () => {
    mockFetch.mockImplementation((...args: unknown[]) => {
      const url = String(args[0] ?? '');
      if (url.includes('/api/v1/cases/c1')) {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () =>
            Promise.resolve({
              error: { code: 'NOT_FOUND', message: 'Not found' },
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [],
            meta: { page: 1, limit: 20, total: 0, total_pages: 0 },
          }),
      });
    });
    renderCaseDetail();
    await waitFor(() => {
      expect(screen.getByTestId('case-detail-error')).toBeInTheDocument();
    });
  });
});
