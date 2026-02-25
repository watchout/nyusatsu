/**
 * Dashboard (P1) — case list with filters, sort, pagination, batch status.
 *
 * SSOT-2 §6-4: default view is all stages (except archived), score desc.
 * Polling: 30s list refresh (SSOT-2 §6-6).
 */

import { useCallback, useEffect } from 'react';
import { useAppDispatch, useCases } from '../contexts/AppContext';
import { usePolling, POLL_CASE_LIST_MS } from '../hooks';
import { buildQuery, fetchPaginated } from '../services/api-client';
import type { Case } from '../types/case';
import BatchStatusBar from '../components/BatchStatusBar';
import CaseFilters from '../components/CaseFilters';
import CaseList from '../components/CaseList';

export default function Dashboard() {
  const dispatch = useAppDispatch();
  const cases = useCases();

  const loadCases = useCallback(async () => {
    dispatch({ type: 'CASES_LOADING' });
    try {
      const params: Record<string, string | number | boolean | null | undefined> = {
        page: cases.page,
        limit: cases.limit,
        sort: `${cases.sort.field}:${cases.sort.direction}`,
        exclude_archived: cases.filter.exclude_archived ?? true,
      };

      // Apply filters
      if (cases.filter.lifecycle_stage) {
        const stages = Array.isArray(cases.filter.lifecycle_stage)
          ? cases.filter.lifecycle_stage.join(',')
          : cases.filter.lifecycle_stage;
        params.lifecycle_stage = stages;
      }
      if (cases.filter.search) {
        params.search = cases.filter.search;
      }
      if (cases.filter.score_min !== undefined) {
        params.score_min = cases.filter.score_min;
      }
      if (cases.filter.score_max !== undefined) {
        params.score_max = cases.filter.score_max;
      }
      if (cases.filter.has_failed !== undefined) {
        params.has_failed = cases.filter.has_failed;
      }
      if (cases.filter.needs_review !== undefined) {
        params.needs_review = cases.filter.needs_review;
      }

      const qs = buildQuery(params);
      const result = await fetchPaginated<Case>(`/cases${qs}`);

      dispatch({
        type: 'CASES_LOADED',
        items: result.data,
        total: result.meta.total,
        totalPages: result.meta.total_pages,
      });
    } catch (err) {
      dispatch({
        type: 'CASES_ERROR',
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }, [
    dispatch,
    cases.page,
    cases.limit,
    cases.sort.field,
    cases.sort.direction,
    cases.filter.lifecycle_stage,
    cases.filter.search,
    cases.filter.score_min,
    cases.filter.score_max,
    cases.filter.has_failed,
    cases.filter.needs_review,
    cases.filter.exclude_archived,
  ]);

  // Initial load + reload on filter/sort/page change
  useEffect(() => {
    loadCases();
  }, [loadCases]);

  // Poll every 30s (SSOT-2 §6-6)
  usePolling(loadCases, { intervalMs: POLL_CASE_LIST_MS });

  return (
    <div>
      <h1 style={titleStyle}>Dashboard</h1>
      <BatchStatusBar />
      <CaseFilters />
      <CaseList />
    </div>
  );
}

const titleStyle: React.CSSProperties = {
  margin: 0,
  padding: '16px',
  fontSize: '1.25rem',
  fontWeight: 700,
  borderBottom: '1px solid #e5e7eb',
};
