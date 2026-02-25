/**
 * CaseDetail (P2) — 5-tab case detail page (SSOT-2 §6-5).
 *
 * Tabs: 概要 / AI読解 / 参加可否 / チェックリスト / 履歴
 * Polling: 5s when processing, stopped when stable (SSOT-2 §6-6).
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAppDispatch, useActiveCase } from '../contexts/AppContext';
import { usePolling, POLL_CASE_DETAIL_MS } from '../hooks';
import { fetchJson, postJson } from '../services/api-client';
import { isProcessingStage } from '../types/enums';
import type { Case } from '../types/case';
import StageBadge from '../components/StageBadge';
import CaseOverview from '../components/CaseOverview';
import ReadingTab from '../components/ReadingTab';
import EligibilityTab from '../components/EligibilityTab';
import ChecklistTab from '../components/ChecklistTab';
import HistoryTab from '../components/HistoryTab';
import type { Verdict } from '../types/enums';
import { patchJson } from '../services/api-client';

type TabId = 'overview' | 'reading' | 'eligibility' | 'checklist' | 'history';

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: '概要' },
  { id: 'reading', label: 'AI読解' },
  { id: 'eligibility', label: '参加可否' },
  { id: 'checklist', label: 'チェックリスト' },
  { id: 'history', label: '履歴' },
];

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const dispatch = useAppDispatch();
  const { caseData, loading, error } = useActiveCase();
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  const loadCase = useCallback(async () => {
    if (!id) return;
    dispatch({ type: 'ACTIVE_CASE_LOADING', caseId: id });
    try {
      const include = 'card_current,eligibility_current,checklist_current,latest_events';
      const data = await fetchJson<Case>(`/cases/${id}?include=${include}`);
      dispatch({
        type: 'ACTIVE_CASE_LOADED',
        caseData: data,
        card: data.card,
        eligibility: data.eligibility,
        checklist: data.checklist,
        events: data.latest_events ?? [],
      });
    } catch (err) {
      dispatch({
        type: 'ACTIVE_CASE_ERROR',
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }, [id, dispatch]);

  useEffect(() => {
    loadCase();
    return () => {
      dispatch({ type: 'ACTIVE_CASE_CLEAR' });
    };
  }, [loadCase, dispatch]);

  // Poll 5s during processing stages (SSOT-2 §6-6)
  const shouldPoll =
    caseData !== null && isProcessingStage(caseData.current_lifecycle_stage);
  usePolling(loadCase, {
    intervalMs: POLL_CASE_DETAIL_MS,
    enabled: shouldPoll,
  });

  const handleAction = useCallback(
    async (action: string) => {
      if (!id) return;
      try {
        await postJson(`/cases/${id}/actions/${action}`);
        await loadCase(); // Refresh after action
      } catch (err) {
        // TODO: show error toast
        console.error('Action failed:', err);
      }
    },
    [id, loadCase],
  );

  const handleOverride = useCallback(
    async (verdict: Verdict, reason: string) => {
      if (!id) return;
      try {
        await postJson(`/cases/${id}/eligibility/override`, {
          verdict,
          override_reason: reason,
        });
        await loadCase();
      } catch (err) {
        console.error('Override failed:', err);
      }
    },
    [id, loadCase],
  );

  const handleToggleItem = useCallback(
    async (itemId: string, checked: boolean) => {
      if (!id || !caseData?.checklist) return;
      try {
        await patchJson(`/checklists/${caseData.checklist.id}/items/${itemId}`, {
          is_checked: checked,
        });
        await loadCase();
      } catch (err) {
        console.error('Toggle failed:', err);
      }
    },
    [id, caseData?.checklist, loadCase],
  );

  if (loading && !caseData) {
    return (
      <div style={pageStyle}>
        <div data-testid="case-detail-loading">読み込み中…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={pageStyle}>
        <div data-testid="case-detail-error">
          エラーが発生しました: {error}
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div style={pageStyle}>
        <div>案件が見つかりません</div>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <Link to="/" style={backLinkStyle}>← 戻る</Link>
        <h1 style={titleStyle}>{caseData.case_name}</h1>
      </div>

      {/* Stage indicator */}
      <div style={stageBarStyle}>
        <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>ステージ:</span>
        <StageBadge stage={caseData.current_lifecycle_stage} />
      </div>

      {/* Tab bar */}
      <div data-testid="tab-bar" style={tabBarStyle}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            data-testid={`tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...tabButtonStyle,
              ...(activeTab === tab.id ? activeTabStyle : {}),
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={tabContentStyle}>
        {activeTab === 'overview' && (
          <CaseOverview caseData={caseData} onAction={handleAction} />
        )}
        {activeTab === 'reading' && (
          <div data-testid="tab-content-reading">
            {caseData.card ? (
              <ReadingTab
                card={caseData.card}
                onMarkReviewed={() => handleAction('mark_reviewed')}
              />
            ) : (
              'この案件はまだ AI 読解されていません。'
            )}
          </div>
        )}
        {activeTab === 'eligibility' && (
          <div data-testid="tab-content-eligibility">
            {caseData.eligibility ? (
              <EligibilityTab
                eligibility={caseData.eligibility}
                stage={caseData.current_lifecycle_stage}
                onOverride={handleOverride}
              />
            ) : (
              'AI 読解が完了すると、自動で判定が実行されます。'
            )}
          </div>
        )}
        {activeTab === 'checklist' && (
          <div data-testid="tab-content-checklist">
            {caseData.checklist ? (
              <ChecklistTab
                checklist={caseData.checklist}
                onToggleItem={handleToggleItem}
              />
            ) : (
              '参加可能と判定されると、チェックリストが自動生成されます。'
            )}
          </div>
        )}
        {activeTab === 'history' && (
          <div data-testid="tab-content-history">
            <HistoryTab events={caseData.latest_events ?? []} />
          </div>
        )}
      </div>
    </div>
  );
}

const pageStyle: React.CSSProperties = { padding: 0 };

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 16,
  padding: '12px 16px',
  borderBottom: '1px solid #e5e7eb',
};

const backLinkStyle: React.CSSProperties = {
  color: '#2563eb',
  textDecoration: 'none',
  fontSize: '0.875rem',
};

const titleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '1.125rem',
  fontWeight: 700,
};

const stageBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  alignItems: 'center',
  padding: '8px 16px',
  backgroundColor: '#f9fafb',
  borderBottom: '1px solid #e5e7eb',
};

const tabBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 0,
  borderBottom: '2px solid #e5e7eb',
  padding: '0 16px',
};

const tabButtonStyle: React.CSSProperties = {
  padding: '10px 16px',
  background: 'none',
  border: 'none',
  borderBottom: '2px solid transparent',
  marginBottom: -2,
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: 500,
  color: '#6b7280',
};

const activeTabStyle: React.CSSProperties = {
  color: '#2563eb',
  borderBottomColor: '#2563eb',
  fontWeight: 600,
};

const tabContentStyle: React.CSSProperties = {
  padding: 16,
};
