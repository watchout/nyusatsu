/**
 * Tests for ReadingTab, ConfidenceBadge, AssertionLabel, EvidencePanel — TASK-42.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';
import type { CaseCard } from '../src/types/case';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const baseCard: CaseCard = {
  id: 'card-1',
  case_id: 'c1',
  version: 2,
  is_current: true,
  eligibility: {
    unified_qualification: true,
    grade: 'D',
    business_category: '物品の販売',
    region: '関東',
    additional_requirements: ['ISO9001', '実績3件以上'],
  },
  schedule: {
    submission_deadline: '2026-03-15T17:00:00Z',
    opening_date: '2026-03-20T10:00:00Z',
    spec_meeting_date: '2026-03-01T14:00:00Z',
  },
  business_content: {
    business_type: '役務の提供',
    summary: '配送業務の委託に関する案件',
    contract_type: 'スポット',
    has_spec_meeting: true,
    has_quote_requirement: false,
    delivery_locations: ['東京都千代田区', '横浜市中区'],
  },
  submission_items: [
    {
      name: '入札書',
      phase: 'bid_time',
      template_source: '機関指定書式',
      deadline: '2026-03-15T17:00:00Z',
      notes: '郵送の場合は書留',
      assertion_type: 'fact',
    },
    {
      name: '納品報告書',
      phase: 'performance_time',
      notes: '毎月末提出',
      assertion_type: 'inferred',
    },
  ],
  risk_factors: [
    {
      risk_type: '特殊許認可要件',
      description: 'ISO9001認証が必要',
      severity: 'high',
      detection_condition: 'additional_requirements に ISO 記載',
    },
    {
      risk_type: '複数納入先',
      description: '2箇所の納入先',
      severity: 'medium',
    },
  ],
  deadline_at: '2026-03-15T17:00:00Z',
  business_type: '役務の提供',
  risk_level: 'high',
  extraction_method: 'text',
  is_scanned: false,
  assertion_counts: { fact: 12, inferred: 3, caution: 1 },
  evidence: {
    'eligibility.unified_qualification': {
      source_type: 'pdf',
      page: 3,
      section: '第2条 参加資格',
      quote: '全省庁統一資格を有する者であること',
      assertion_type: 'fact',
    },
    'business_content.summary': {
      source_type: 'html',
      heading_path: '入札公告 > 業務概要',
      quote: '配送業務の委託',
      assertion_type: 'fact',
    },
  },
  confidence_score: 0.85,
  file_hash: 'sha256:abc123',
  status: 'needs_review',
  llm_model: 'claude-3-5-sonnet-20241022',
  token_usage: { input: 5000, output: 2000 },
  extracted_at: '2026-03-01T06:15:00Z',
  reviewed_at: null,
  reviewed_by: null,
  created_at: '2026-03-01T06:15:00Z',
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
  current_lifecycle_stage: 'reading_completed',
  score: 85,
  score_detail: { competition: 25, scale: 20, margin: 22, fit: 18 },
  first_seen_at: '2026-02-01T00:00:00Z',
  last_updated_at: '2026-02-01T00:00:00Z',
  card: baseCard,
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

async function switchToReadingTab() {
  await waitFor(() => {
    expect(screen.getByTestId('tab-reading')).toBeInTheDocument();
  });
  await userEvent.click(screen.getByTestId('tab-reading'));
}

// ---- ConfidenceBadge ----

describe('ReadingTab — ConfidenceBadge', () => {
  it('shows confidence score as percentage', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('confidence-badge')).toHaveTextContent('信頼度 85%');
  });

  it('shows green color for high confidence (>0.6)', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    const badge = screen.getByTestId('confidence-badge');
    expect(badge.style.backgroundColor).toBe('rgb(209, 250, 229)');
  });

  it('shows yellow color for medium confidence', async () => {
    setupMock({
      ...baseCaseData,
      card: { ...baseCard, confidence_score: 0.5 },
    });
    renderCaseDetail();
    await switchToReadingTab();
    const badge = screen.getByTestId('confidence-badge');
    expect(badge.style.backgroundColor).toBe('rgb(254, 243, 199)');
  });

  it('shows red color for low confidence (<0.4)', async () => {
    setupMock({
      ...baseCaseData,
      card: { ...baseCard, confidence_score: 0.3 },
    });
    renderCaseDetail();
    await switchToReadingTab();
    const badge = screen.getByTestId('confidence-badge');
    expect(badge.style.backgroundColor).toBe('rgb(254, 226, 226)');
  });
});

// ---- Needs review badge ----

describe('ReadingTab — NeedsReview', () => {
  it('shows needs_review badge when status is needs_review', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('needs-review-badge')).toHaveTextContent('要確認');
  });

  it('shows mark-reviewed button', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('mark-reviewed-btn')).toHaveTextContent('確認済みにする');
  });

  it('hides needs_review badge when status is completed', async () => {
    setupMock({
      ...baseCaseData,
      card: { ...baseCard, status: 'completed' },
    });
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.queryByTestId('needs-review-badge')).not.toBeInTheDocument();
  });
});

// ---- Scanned PDF warning ----

describe('ReadingTab — ScannedWarning', () => {
  it('shows scanned PDF warning when is_scanned is true', async () => {
    setupMock({
      ...baseCaseData,
      card: { ...baseCard, is_scanned: true },
    });
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('scanned-warning')).toHaveTextContent(
      '画像PDF',
    );
  });

  it('hides scanned warning when is_scanned is false', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.queryByTestId('scanned-warning')).not.toBeInTheDocument();
  });
});

// ---- AssertionSummary ----

describe('ReadingTab — AssertionSummary', () => {
  it('shows assertion counts', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    const summary = screen.getByTestId('assertion-summary');
    expect(summary).toHaveTextContent('確認: 12件');
    expect(summary).toHaveTextContent('推定: 3件');
    expect(summary).toHaveTextContent('注意: 1件');
  });
});

// ---- 5 Category Sections ----

describe('ReadingTab — EligibilitySection', () => {
  it('renders eligibility section with fields', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    const section = screen.getByTestId('section-eligibility');
    expect(section).toBeInTheDocument();
    expect(section).toHaveTextContent('全省庁統一資格');
    expect(section).toHaveTextContent('物品の販売');
    expect(section).toHaveTextContent('関東');
  });
});

describe('ReadingTab — ScheduleSection', () => {
  it('renders schedule section with dates', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('section-schedule')).toBeInTheDocument();
    expect(screen.getByTestId('section-header-schedule')).toHaveTextContent('スケジュール');
  });
});

describe('ReadingTab — BusinessContentSection', () => {
  it('renders business content section', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('section-business_content')).toBeInTheDocument();
    expect(screen.getByText('配送業務の委託に関する案件')).toBeInTheDocument();
    expect(screen.getByText('スポット')).toBeInTheDocument();
  });
});

describe('ReadingTab — SubmissionItemsSection', () => {
  it('renders submission items section', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('section-submission_items')).toBeInTheDocument();
    expect(screen.getByText('入札書')).toBeInTheDocument();
    expect(screen.getByText('納品報告書')).toBeInTheDocument();
  });

  it('shows bid_time and performance_time groups', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByText('入札参加時')).toBeInTheDocument();
    expect(screen.getByText('履行時')).toBeInTheDocument();
  });

  it('shows assertion labels on items', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    // 'fact' assertion on 入札書
    expect(screen.getAllByTestId('assertion-fact').length).toBeGreaterThan(0);
    // 'inferred' assertion on 納品報告書
    expect(screen.getAllByTestId('assertion-inferred').length).toBeGreaterThan(0);
  });
});

describe('ReadingTab — RiskFactorsSection', () => {
  it('renders risk factors section', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('section-risk_factors')).toBeInTheDocument();
    expect(screen.getByText('ISO9001認証が必要')).toBeInTheDocument();
    expect(screen.getByText('2箇所の納入先')).toBeInTheDocument();
  });

  it('shows severity labels', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByText('high')).toBeInTheDocument();
    expect(screen.getByText('medium')).toBeInTheDocument();
  });
});

// ---- Evidence panel ----

describe('ReadingTab — EvidencePanel', () => {
  it('renders evidence for eligibility field', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    const evidence = screen.getByTestId('evidence-eligibility.unified_qualification');
    expect(evidence).toBeInTheDocument();
    expect(evidence).toHaveTextContent('全省庁統一資格を有する者であること');
    expect(evidence).toHaveTextContent('p.3');
  });

  it('renders evidence for business content field', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    const evidence = screen.getByTestId('evidence-business_content.summary');
    expect(evidence).toBeInTheDocument();
    expect(evidence).toHaveTextContent('配送業務の委託');
    expect(evidence).toHaveTextContent('入札公告 > 業務概要');
  });
});

// ---- Empty state ----

describe('ReadingTab — EmptyState', () => {
  it('shows empty state when no card exists', async () => {
    setupMock({ ...baseCaseData, card: null });
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('tab-content-reading')).toHaveTextContent(
      'AI 読解されていません',
    );
  });
});

// ---- Meta info ----

describe('ReadingTab — MetaInfo', () => {
  it('shows LLM model and version', async () => {
    setupMock();
    renderCaseDetail();
    await switchToReadingTab();
    expect(screen.getByTestId('reading-tab')).toHaveTextContent('claude-3-5-sonnet-20241022');
    expect(screen.getByTestId('reading-tab')).toHaveTextContent('バージョン: 2');
  });
});
