/**
 * BatchStatusBar — batch execution status display + manual trigger (SSOT-2 §6-4).
 */

import { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useBatchStatus } from '../contexts/AppContext';
import { usePolling, POLL_BATCH_STATUS_MS } from '../hooks';
import { fetchJson, postJson } from '../services/api-client';
import type { BatchLog } from '../types/case';

export default function BatchStatusBar() {
  const { lastRun } = useBatchStatus();
  const dispatch = useAppDispatch();
  const [triggering, setTriggering] = useState(false);

  const loadBatch = useCallback(async () => {
    try {
      const data = await fetchJson<BatchLog | null>('/batch/latest');
      dispatch({ type: 'BATCH_STATUS_LOADED', lastRun: data });
    } catch {
      // Silently fail — batch status is informational
    }
  }, [dispatch]);

  // Initial load
  useEffect(() => {
    loadBatch();
  }, [loadBatch]);

  // Poll every 60s
  usePolling(loadBatch, { intervalMs: POLL_BATCH_STATUS_MS });

  const handleTrigger = useCallback(async () => {
    setTriggering(true);
    try {
      await postJson('/batch/trigger');
      await loadBatch();
    } catch {
      // TODO: show error toast
    } finally {
      setTriggering(false);
    }
  }, [loadBatch]);

  if (!lastRun) {
    return (
      <div data-testid="batch-status" style={barStyle}>
        <span>バッチ状態: まだ実行されていません</span>
        <button
          data-testid="batch-trigger-btn"
          onClick={handleTrigger}
          disabled={triggering}
          style={{
            ...triggerBtnStyle,
            opacity: triggering ? 0.5 : 1,
          }}
        >
          {triggering ? '実行中…' : 'バッチ実行'}
        </button>
      </div>
    );
  }

  const isSuccess = lastRun.status === 'success';
  const isRunning = lastRun.status === 'running';
  const icon = isSuccess ? '✅' : isRunning ? '🔄' : '❌';
  const dateStr = lastRun.started_at
    ? new Date(lastRun.started_at).toLocaleString('ja-JP')
    : '不明';
  const statusLabel = isSuccess ? '成功' : isRunning ? '実行中' : '失敗';

  return (
    <div data-testid="batch-status" style={barStyle}>
      <span>
        バッチ状態: {icon} 最終実行 {dateStr} ({statusLabel})
        {lastRun.new_count > 0 && (
          <span style={{ marginLeft: 8, color: '#2563eb', fontWeight: 600 }}>
            新着 {lastRun.new_count} 件
          </span>
        )}
      </span>
      <button
        data-testid="batch-trigger-btn"
        onClick={handleTrigger}
        disabled={triggering || isRunning}
        style={{
          ...triggerBtnStyle,
          opacity: triggering || isRunning ? 0.5 : 1,
        }}
      >
        {triggering ? '実行中…' : 'バッチ実行'}
      </button>
    </div>
  );
}

const barStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '8px 16px',
  backgroundColor: '#f9fafb',
  borderBottom: '1px solid #e5e7eb',
  fontSize: '0.875rem',
};

const triggerBtnStyle: React.CSSProperties = {
  padding: '4px 12px',
  borderRadius: 6,
  border: '1px solid #d1d5db',
  backgroundColor: '#fff',
  fontSize: '0.8rem',
  fontWeight: 600,
  cursor: 'pointer',
};
