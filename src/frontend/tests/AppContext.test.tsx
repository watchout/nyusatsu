/**
 * Tests for AppContext — TASK-39.
 *
 * Validates state management, dispatch, and convenience hooks.
 */

import { render, screen, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import {
  AppProvider,
  useAppState,
  useAppDispatch,
  useCases,
} from '../src/contexts/AppContext';

function TestConsumer() {
  const state = useAppState();
  const dispatch = useAppDispatch();
  const cases = useCases();

  return (
    <div>
      <span data-testid="loading">{String(cases.loading)}</span>
      <span data-testid="total">{cases.total}</span>
      <span data-testid="page">{cases.page}</span>
      <span data-testid="filter-archived">
        {String(cases.filter.exclude_archived)}
      </span>
      <span data-testid="sort-field">{cases.sort.field}</span>
      <span data-testid="active-case-id">{state.activeCase.caseId ?? 'null'}</span>
      <button
        data-testid="load-cases"
        onClick={() =>
          dispatch({
            type: 'CASES_LOADED',
            items: [{ id: 'c1', case_name: 'Test' } as never],
            total: 1,
            totalPages: 1,
          })
        }
      />
      <button
        data-testid="set-filter"
        onClick={() =>
          dispatch({
            type: 'CASES_SET_FILTER',
            filter: { search: 'test' },
          })
        }
      />
      <button
        data-testid="set-page"
        onClick={() => dispatch({ type: 'CASES_SET_PAGE', page: 3 })}
      />
    </div>
  );
}

function renderWithProvider() {
  return render(
    <AppProvider>
      <TestConsumer />
    </AppProvider>,
  );
}

describe('AppContext', () => {
  it('provides initial state', () => {
    renderWithProvider();
    expect(screen.getByTestId('loading').textContent).toBe('false');
    expect(screen.getByTestId('total').textContent).toBe('0');
    expect(screen.getByTestId('page').textContent).toBe('1');
    expect(screen.getByTestId('filter-archived').textContent).toBe('true');
    expect(screen.getByTestId('sort-field').textContent).toBe('score');
    expect(screen.getByTestId('active-case-id').textContent).toBe('null');
  });

  it('dispatches CASES_LOADED and updates state', () => {
    renderWithProvider();
    act(() => {
      screen.getByTestId('load-cases').click();
    });
    expect(screen.getByTestId('total').textContent).toBe('1');
  });

  it('dispatches CASES_SET_FILTER and resets page to 1', () => {
    renderWithProvider();
    // First set page to 3
    act(() => {
      screen.getByTestId('set-page').click();
    });
    expect(screen.getByTestId('page').textContent).toBe('3');
    // Then set filter → page resets to 1
    act(() => {
      screen.getByTestId('set-filter').click();
    });
    expect(screen.getByTestId('page').textContent).toBe('1');
  });

  it('dispatches CASES_SET_PAGE', () => {
    renderWithProvider();
    act(() => {
      screen.getByTestId('set-page').click();
    });
    expect(screen.getByTestId('page').textContent).toBe('3');
  });
});

describe('useAppState outside provider', () => {
  it('throws when used outside AppProvider', () => {
    function BadConsumer() {
      useAppState();
      return null;
    }
    expect(() => render(<BadConsumer />)).toThrow(
      'useAppState must be used within AppProvider',
    );
  });
});
