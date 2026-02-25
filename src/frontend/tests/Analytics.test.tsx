/**
 * Tests for Analytics page — TASK-46.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const baseSummary = {
  total_records: 150,
  period: { from_date: '2025-02-01', to_date: '2026-02-01' },
  amount_stats: {
    median: 5000000,
    q1: 2000000,
    q3: 10000000,
    mean: 7500000,
    min: 100000,
    max: 50000000,
  },
  participants_stats: {
    median: 3,
    mean: 4.2,
    single_bid_rate: 0.15,
  },
  winning_rate_by_amount: [
    { range: '100万円未満', win_rate: 0.45 },
    { range: '100万〜500万円', win_rate: 0.32 },
    { range: '500万〜1000万円', win_rate: 0.18 },
  ],
  trend_by_quarter: [
    { quarter: '2025Q3', median_amount: 4500000, avg_participants: 3.8 },
    { quarter: '2025Q4', median_amount: 5200000, avg_participants: 4.1 },
    { quarter: '2026Q1', median_amount: 5000000, avg_participants: 4.5 },
  ],
};

function setupMock(summaryData: Record<string, unknown> | null = baseSummary) {
  mockFetch.mockImplementation((...args: unknown[]) => {
    const url = String(args[0] ?? '');
    if (url.includes('/api/v1/analytics/price-summary')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: summaryData }),
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

function renderAnalytics() {
  return render(
    <MemoryRouter initialEntries={['/analytics']}>
      <App />
    </MemoryRouter>,
  );
}

describe('Analytics', () => {
  it('renders Analytics heading', async () => {
    setupMock();
    renderAnalytics();
    expect(screen.getByRole('heading', { name: /analytics/i })).toBeInTheDocument();
  });

  it('shows filter controls', async () => {
    setupMock();
    renderAnalytics();
    await waitFor(() => {
      expect(screen.getByTestId('analytics-filters')).toBeInTheDocument();
    });
    expect(screen.getByTestId('filter-keyword')).toBeInTheDocument();
    expect(screen.getByTestId('filter-category')).toBeInTheDocument();
    expect(screen.getByTestId('filter-period')).toBeInTheDocument();
  });

  it('shows stats cards with data', async () => {
    setupMock();
    renderAnalytics();
    await waitFor(() => {
      expect(screen.getByTestId('stats-cards')).toBeInTheDocument();
    });
    expect(screen.getByTestId('stats-cards')).toHaveTextContent('150件');
  });

  it('shows winning rate table', async () => {
    setupMock();
    renderAnalytics();
    await waitFor(() => {
      expect(screen.getByTestId('winning-rate-table')).toBeInTheDocument();
    });
    expect(screen.getByTestId('winning-rate-table')).toHaveTextContent('100万円未満');
  });

  it('shows trend table', async () => {
    setupMock();
    renderAnalytics();
    await waitFor(() => {
      expect(screen.getByTestId('trend-table')).toBeInTheDocument();
    });
    expect(screen.getByTestId('trend-table')).toHaveTextContent('2025Q3');
  });

  it('shows empty state when no data', async () => {
    setupMock(null);
    renderAnalytics();
    await waitFor(() => {
      expect(screen.getByTestId('analytics-empty')).toBeInTheDocument();
    });
    expect(screen.getByTestId('analytics-empty')).toHaveTextContent('データがありません');
  });
});
