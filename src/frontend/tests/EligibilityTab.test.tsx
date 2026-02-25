/**
 * Tests for EligibilityTab, VerdictBadge, OverridePanel — TASK-43.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const baseEligibility = {
  id: 'elig-1',
  case_id: 'c1',
  case_card_id: 'card-1',
  version: 1,
  is_current: true,
  verdict: 'uncertain',
  confidence: 0.72,
  hard_fail_reasons: [
    {
      code: 'hard_5',
      description: 'その他の参加資格に記載あり — 確認が必要',
      source_text: 'その他の参加資格を有する者',
    },
  ],
  soft_gaps: [
    {
      code: 'soft_1_experience',
      description: '同種業務の履行実績が求められています',
      severity: 'high',
    },
    {
      code: 'soft_3_iso',
      description: 'ISO9001認証の保有が推奨されています',
      severity: 'medium',
    },
  ],
  check_details: {},
  company_profile_snapshot: {},
  human_override: null,
  override_reason: null,
  overridden_at: null,
  judged_at: '2026-03-02T10:00:00Z',
  created_at: '2026-03-02T10:00:00Z',
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
  current_lifecycle_stage: 'judging_completed',
  score: 85,
  score_detail: { competition: 25, scale: 20, margin: 22, fit: 18 },
  first_seen_at: '2026-02-01T00:00:00Z',
  last_updated_at: '2026-02-01T00:00:00Z',
  card: null,
  eligibility: baseEligibility,
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

async function switchToEligibilityTab() {
  await waitFor(() => {
    expect(screen.getByTestId('tab-eligibility')).toBeInTheDocument();
  });
  await userEvent.click(screen.getByTestId('tab-eligibility'));
}

// ---- VerdictBadge ----

describe('EligibilityTab — VerdictBadge', () => {
  it('shows uncertain verdict badge', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    const badge = screen.getByTestId('verdict-badge');
    expect(badge).toHaveTextContent('確認必要');
  });

  it('shows eligible verdict badge', async () => {
    setupMock({
      ...baseCaseData,
      eligibility: { ...baseEligibility, verdict: 'eligible', hard_fail_reasons: [], soft_gaps: [] },
    });
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('verdict-badge')).toHaveTextContent('参加可能');
  });

  it('shows ineligible verdict badge', async () => {
    setupMock({
      ...baseCaseData,
      eligibility: { ...baseEligibility, verdict: 'ineligible' },
    });
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('verdict-badge')).toHaveTextContent('参加不可');
  });
});

// ---- Confidence ----

describe('EligibilityTab — Confidence', () => {
  it('shows confidence badge', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('confidence-badge')).toHaveTextContent('信頼度 72%');
  });
});

// ---- Hard fail reasons ----

describe('EligibilityTab — HardFailReasons', () => {
  it('renders hard fail reasons', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    const section = screen.getByTestId('hard-fail-reasons');
    expect(section).toBeInTheDocument();
    expect(section).toHaveTextContent('hard_5');
    expect(section).toHaveTextContent('確認が必要');
  });

  it('shows source text evidence', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('hard-fail-reasons')).toHaveTextContent(
      'その他の参加資格を有する者',
    );
  });
});

// ---- Soft gaps ----

describe('EligibilityTab — SoftGaps', () => {
  it('renders soft gaps with severity badges', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    const section = screen.getByTestId('soft-gaps');
    expect(section).toBeInTheDocument();
    expect(section).toHaveTextContent('同種業務の履行実績');
    expect(section).toHaveTextContent('ISO9001認証');
  });

  it('shows severity labels', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('severity-high')).toHaveTextContent('高');
    expect(screen.getByTestId('severity-medium')).toHaveTextContent('中');
  });
});

// ---- Override panel ----

describe('EligibilityTab — OverridePanel', () => {
  it('shows override panel for uncertain verdict', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('override-panel')).toBeInTheDocument();
    expect(screen.getByTestId('override-reason-input')).toBeInTheDocument();
  });

  it('shows override buttons', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('override-eligible-btn')).toHaveTextContent('eligible に変更');
    expect(screen.getByTestId('override-ineligible-btn')).toHaveTextContent('ineligible に変更');
  });

  it('disables buttons when reason is empty', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('override-eligible-btn')).toBeDisabled();
    expect(screen.getByTestId('override-ineligible-btn')).toBeDisabled();
  });

  it('enables buttons after entering reason', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    await userEvent.type(
      screen.getByTestId('override-reason-input'),
      'ISO取得済みのため問題なし',
    );
    expect(screen.getByTestId('override-eligible-btn')).not.toBeDisabled();
  });

  it('hides override panel for eligible verdict', async () => {
    setupMock({
      ...baseCaseData,
      eligibility: { ...baseEligibility, verdict: 'eligible', hard_fail_reasons: [], soft_gaps: [] },
    });
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.queryByTestId('override-panel')).not.toBeInTheDocument();
  });

  it('shows past override result when already overridden', async () => {
    setupMock({
      ...baseCaseData,
      eligibility: {
        ...baseEligibility,
        human_override: 'eligible',
        override_reason: '確認済み',
        overridden_at: '2026-03-03T12:00:00Z',
      },
    });
    renderCaseDetail();
    await switchToEligibilityTab();
    const panel = screen.getByTestId('override-panel');
    expect(panel).toBeInTheDocument();
    expect(screen.getByTestId('override-result')).toHaveTextContent('参加可能');
    expect(screen.getByTestId('override-result')).toHaveTextContent('確認済み');
  });

  it('shows warning about checklist auto-generation', async () => {
    setupMock();
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('override-panel')).toHaveTextContent(
      'チェックリストが自動生成されます',
    );
  });
});

// ---- Eligible message ----

describe('EligibilityTab — EligibleMessage', () => {
  it('shows all-clear message for eligible with no issues', async () => {
    setupMock({
      ...baseCaseData,
      eligibility: {
        ...baseEligibility,
        verdict: 'eligible',
        hard_fail_reasons: [],
        soft_gaps: [],
      },
    });
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('eligible-message')).toHaveTextContent(
      '全ての参加要件を満たしています',
    );
  });
});

// ---- Empty state ----

describe('EligibilityTab — EmptyState', () => {
  it('shows empty state when no eligibility result', async () => {
    setupMock({ ...baseCaseData, eligibility: null });
    renderCaseDetail();
    await switchToEligibilityTab();
    expect(screen.getByTestId('tab-content-eligibility')).toHaveTextContent(
      '自動で判定が実行されます',
    );
  });
});
