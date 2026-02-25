/**
 * usePolling — interval-based polling hook (SSOT-2 §6-6).
 *
 * Polling intervals:
 *   - Case detail (processing):  5 seconds
 *   - Case list (dashboard):     30 seconds
 *   - Batch status:              60 seconds
 *
 * Automatically stops when the component unmounts.
 */

import { useEffect, useRef } from 'react';

export interface UsePollingOptions {
  /** Polling interval in milliseconds. */
  intervalMs: number;
  /** Whether polling is enabled. Pass false to pause. */
  enabled?: boolean;
}

/**
 * Periodically calls `callback` at `intervalMs` intervals.
 *
 * The callback is NOT invoked immediately — only after the first interval.
 * Use useApi for the initial fetch.
 */
export function usePolling(
  callback: () => void | Promise<void>,
  options: UsePollingOptions,
): void {
  const { intervalMs, enabled = true } = options;
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;

    const id = setInterval(() => {
      callbackRef.current();
    }, intervalMs);

    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}

// Predefined interval constants (SSOT-2 §6-6)
export const POLL_CASE_DETAIL_MS = 5_000;
export const POLL_CASE_LIST_MS = 30_000;
export const POLL_BATCH_STATUS_MS = 60_000;
