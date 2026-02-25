/**
 * BatchStatusBar — batch execution status display (SSOT-2 §6-4).
 */

import { useCallback, useEffect } from 'react';
import { useAppDispatch, useBatchStatus } from '../contexts/AppContext';
import { usePolling, POLL_BATCH_STATUS_MS } from '../hooks';
import { fetchJson } from '../services/api-client';
import type { BatchLog } from '../types/case';

export default function BatchStatusBar() {
  const { lastRun } = useBatchStatus();
  const dispatch = useAppDispatch();

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

  if (!lastRun) {
    return (
      <div data-testid="batch-status" style={barStyle}>
        バッチ状態: まだ実行されていません
      </div>
    );
  }

  const isSuccess = lastRun.status === 'success';
  const icon = isSuccess ? '✅' : '❌';
  const dateStr = lastRun.started_at
    ? new Date(lastRun.started_at).toLocaleString('ja-JP')
    : '不明';
  const statusLabel = isSuccess ? '成功' : '失敗';

  return (
    <div data-testid="batch-status" style={barStyle}>
      バッチ状態: {icon} 最終実行 {dateStr} ({statusLabel})
      {lastRun.new_count > 0 && (
        <span style={{ marginLeft: 8, color: '#2563eb', fontWeight: 600 }}>
          新着 {lastRun.new_count} 件
        </span>
      )}
    </div>
  );
}

const barStyle: React.CSSProperties = {
  padding: '8px 16px',
  backgroundColor: '#f9fafb',
  borderBottom: '1px solid #e5e7eb',
  fontSize: '0.875rem',
};
