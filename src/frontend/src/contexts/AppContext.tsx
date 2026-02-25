/**
 * AppContext — global state for the application (SSOT-2 §6-1).
 *
 * Phase1: React Context is sufficient. Phase2: migrate to Zustand if needed.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode,
} from 'react';
import type {
  BatchLog,
  Case,
  CaseCard,
  CaseEvent,
  Checklist,
  CompanyProfile,
  EligibilityResult,
} from '../types/case';
import type { LifecycleStage, SortDirection, SortField } from '../types/enums';

// ---------------------------------------------------------------------------
// State shape (SSOT-2 §6-1)
// ---------------------------------------------------------------------------

export interface CaseFilter {
  lifecycle_stage?: LifecycleStage | LifecycleStage[];
  status?: string;
  score_min?: number;
  score_max?: number;
  deadline_before?: string;
  deadline_after?: string;
  needs_review?: boolean;
  has_failed?: boolean;
  search?: string;
  exclude_archived?: boolean;
}

export interface CaseSort {
  field: SortField;
  direction: SortDirection;
}

export interface AppState {
  cases: {
    items: Case[];
    filter: CaseFilter;
    sort: CaseSort;
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    loading: boolean;
    error: string | null;
    lastFetchedAt: string | null;
  };
  activeCase: {
    caseId: string | null;
    caseData: Case | null;
    card: CaseCard | null;
    eligibility: EligibilityResult | null;
    checklist: Checklist | null;
    events: CaseEvent[];
    loading: boolean;
    error: string | null;
  };
  companyProfile: {
    data: CompanyProfile | null;
    loading: boolean;
  };
  batchStatus: {
    lastRun: BatchLog | null;
    running: boolean;
  };
}

const initialState: AppState = {
  cases: {
    items: [],
    filter: { exclude_archived: true },
    sort: { field: 'score', direction: 'desc' },
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
    loading: false,
    error: null,
    lastFetchedAt: null,
  },
  activeCase: {
    caseId: null,
    caseData: null,
    card: null,
    eligibility: null,
    checklist: null,
    events: [],
    loading: false,
    error: null,
  },
  companyProfile: {
    data: null,
    loading: false,
  },
  batchStatus: {
    lastRun: null,
    running: false,
  },
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

type Action =
  // Cases
  | { type: 'CASES_LOADING' }
  | {
      type: 'CASES_LOADED';
      items: Case[];
      total: number;
      totalPages: number;
    }
  | { type: 'CASES_ERROR'; error: string }
  | { type: 'CASES_SET_FILTER'; filter: Partial<CaseFilter> }
  | { type: 'CASES_SET_SORT'; sort: CaseSort }
  | { type: 'CASES_SET_PAGE'; page: number }
  // Active case
  | { type: 'ACTIVE_CASE_LOADING'; caseId: string }
  | {
      type: 'ACTIVE_CASE_LOADED';
      caseData: Case;
      card?: CaseCard | null;
      eligibility?: EligibilityResult | null;
      checklist?: Checklist | null;
      events?: CaseEvent[];
    }
  | { type: 'ACTIVE_CASE_ERROR'; error: string }
  | { type: 'ACTIVE_CASE_CLEAR' }
  | { type: 'ACTIVE_CASE_UPDATE_CARD'; card: CaseCard }
  | { type: 'ACTIVE_CASE_UPDATE_ELIGIBILITY'; eligibility: EligibilityResult }
  | { type: 'ACTIVE_CASE_UPDATE_CHECKLIST'; checklist: Checklist }
  | { type: 'ACTIVE_CASE_UPDATE_EVENTS'; events: CaseEvent[] }
  | { type: 'ACTIVE_CASE_UPDATE_STAGE'; stage: LifecycleStage }
  // Company profile
  | { type: 'PROFILE_LOADING' }
  | { type: 'PROFILE_LOADED'; data: CompanyProfile }
  // Batch
  | { type: 'BATCH_STATUS_LOADED'; lastRun: BatchLog | null }
  | { type: 'BATCH_RUNNING'; running: boolean };

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    // Cases
    case 'CASES_LOADING':
      return { ...state, cases: { ...state.cases, loading: true, error: null } };
    case 'CASES_LOADED':
      return {
        ...state,
        cases: {
          ...state.cases,
          items: action.items,
          total: action.total,
          totalPages: action.totalPages,
          loading: false,
          error: null,
          lastFetchedAt: new Date().toISOString(),
        },
      };
    case 'CASES_ERROR':
      return {
        ...state,
        cases: { ...state.cases, loading: false, error: action.error },
      };
    case 'CASES_SET_FILTER':
      return {
        ...state,
        cases: {
          ...state.cases,
          filter: { ...state.cases.filter, ...action.filter },
          page: 1, // Reset page on filter change
        },
      };
    case 'CASES_SET_SORT':
      return {
        ...state,
        cases: { ...state.cases, sort: action.sort, page: 1 },
      };
    case 'CASES_SET_PAGE':
      return {
        ...state,
        cases: { ...state.cases, page: action.page },
      };

    // Active case
    case 'ACTIVE_CASE_LOADING':
      return {
        ...state,
        activeCase: {
          ...state.activeCase,
          caseId: action.caseId,
          loading: true,
          error: null,
        },
      };
    case 'ACTIVE_CASE_LOADED':
      return {
        ...state,
        activeCase: {
          caseId: action.caseData.id,
          caseData: action.caseData,
          card: action.card ?? null,
          eligibility: action.eligibility ?? null,
          checklist: action.checklist ?? null,
          events: action.events ?? [],
          loading: false,
          error: null,
        },
      };
    case 'ACTIVE_CASE_ERROR':
      return {
        ...state,
        activeCase: { ...state.activeCase, loading: false, error: action.error },
      };
    case 'ACTIVE_CASE_CLEAR':
      return { ...state, activeCase: initialState.activeCase };
    case 'ACTIVE_CASE_UPDATE_CARD':
      return {
        ...state,
        activeCase: { ...state.activeCase, card: action.card },
      };
    case 'ACTIVE_CASE_UPDATE_ELIGIBILITY':
      return {
        ...state,
        activeCase: { ...state.activeCase, eligibility: action.eligibility },
      };
    case 'ACTIVE_CASE_UPDATE_CHECKLIST':
      return {
        ...state,
        activeCase: { ...state.activeCase, checklist: action.checklist },
      };
    case 'ACTIVE_CASE_UPDATE_EVENTS':
      return {
        ...state,
        activeCase: { ...state.activeCase, events: action.events },
      };
    case 'ACTIVE_CASE_UPDATE_STAGE':
      if (!state.activeCase.caseData) return state;
      return {
        ...state,
        activeCase: {
          ...state.activeCase,
          caseData: {
            ...state.activeCase.caseData,
            current_lifecycle_stage: action.stage,
          },
        },
      };

    // Company profile
    case 'PROFILE_LOADING':
      return {
        ...state,
        companyProfile: { ...state.companyProfile, loading: true },
      };
    case 'PROFILE_LOADED':
      return {
        ...state,
        companyProfile: { data: action.data, loading: false },
      };

    // Batch
    case 'BATCH_STATUS_LOADED':
      return {
        ...state,
        batchStatus: {
          ...state.batchStatus,
          lastRun: action.lastRun,
        },
      };
    case 'BATCH_RUNNING':
      return {
        ...state,
        batchStatus: { ...state.batchStatus, running: action.running },
      };

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<Action>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppState(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppState must be used within AppProvider');
  return ctx.state;
}

export function useAppDispatch(): React.Dispatch<Action> {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppDispatch must be used within AppProvider');
  return ctx.dispatch;
}

// ---------------------------------------------------------------------------
// Convenience hooks
// ---------------------------------------------------------------------------

export function useCases() {
  const { cases } = useAppState();
  return cases;
}

export function useActiveCase() {
  const { activeCase } = useAppState();
  return activeCase;
}

export function useCompanyProfile() {
  const { companyProfile } = useAppState();
  return companyProfile;
}

export function useBatchStatus() {
  const { batchStatus } = useAppState();
  return batchStatus;
}

// ---------------------------------------------------------------------------
// Action creators (memoized via useCallback in consuming components)
// ---------------------------------------------------------------------------

export function useCaseActions() {
  const dispatch = useAppDispatch();

  const setFilter = useCallback(
    (filter: Partial<CaseFilter>) =>
      dispatch({ type: 'CASES_SET_FILTER', filter }),
    [dispatch],
  );

  const setSort = useCallback(
    (sort: CaseSort) => dispatch({ type: 'CASES_SET_SORT', sort }),
    [dispatch],
  );

  const setPage = useCallback(
    (page: number) => dispatch({ type: 'CASES_SET_PAGE', page }),
    [dispatch],
  );

  return { setFilter, setSort, setPage, dispatch };
}
