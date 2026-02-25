/**
 * CaseFilters — filter and sort controls for the dashboard (SSOT-2 §6-4).
 *
 * Filters: lifecycle stage group, score range, deadline, search text.
 * Sort: score/deadline/first_seen_at.
 */

import { useCaseActions, useCases } from '../contexts/AppContext';
import { STAGE_GROUPS, type StageGroup, type LifecycleStage } from '../types/enums';
import type { CaseSort, CaseFilter } from '../contexts/AppContext';
import type { SortField, SortDirection } from '../types/enums';

const SORT_OPTIONS: { label: string; field: SortField; direction: SortDirection }[] = [
  { label: 'スコア順', field: 'score', direction: 'desc' },
  { label: '期限順', field: 'deadline_at', direction: 'asc' },
  { label: '新着順', field: 'first_seen_at', direction: 'desc' },
  { label: '名前順', field: 'case_name', direction: 'asc' },
];

export default function CaseFilters() {
  const cases = useCases();
  const { setFilter, setSort } = useCaseActions();

  const handleGroupFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === 'all') {
      setFilter({ lifecycle_stage: undefined } as Partial<CaseFilter>);
    } else {
      const stages = STAGE_GROUPS[value as StageGroup] as LifecycleStage[];
      setFilter({ lifecycle_stage: stages } as Partial<CaseFilter>);
    }
  };

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const opt = SORT_OPTIONS[Number(e.target.value)];
    if (opt) {
      setSort({ field: opt.field, direction: opt.direction } as CaseSort);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter({ search: e.target.value || undefined } as Partial<CaseFilter>);
  };

  const currentSortIndex = SORT_OPTIONS.findIndex(
    (o) => o.field === cases.sort.field && o.direction === cases.sort.direction,
  );

  return (
    <div data-testid="case-filters" style={containerStyle}>
      <div style={rowStyle}>
        <label style={labelStyle}>
          グループ:
          <select
            data-testid="filter-group"
            onChange={handleGroupFilter}
            style={selectStyle}
          >
            <option value="all">全て</option>
            {Object.keys(STAGE_GROUPS).map((group) => (
              <option key={group} value={group}>
                {group}
              </option>
            ))}
          </select>
        </label>

        <label style={labelStyle}>
          ソート:
          <select
            data-testid="filter-sort"
            value={currentSortIndex >= 0 ? currentSortIndex : 0}
            onChange={handleSortChange}
            style={selectStyle}
          >
            {SORT_OPTIONS.map((opt, i) => (
              <option key={opt.field} value={i}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label style={labelStyle}>
          検索:
          <input
            data-testid="filter-search"
            type="text"
            placeholder="案件名・発注機関..."
            value={cases.filter.search ?? ''}
            onChange={handleSearchChange}
            style={inputStyle}
          />
        </label>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  padding: '12px 16px',
  backgroundColor: '#ffffff',
  borderBottom: '1px solid #e5e7eb',
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  gap: 16,
  alignItems: 'center',
  flexWrap: 'wrap',
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  fontSize: '0.875rem',
  color: '#374151',
};

const selectStyle: React.CSSProperties = {
  padding: '4px 8px',
  border: '1px solid #d1d5db',
  borderRadius: 4,
  fontSize: '0.875rem',
};

const inputStyle: React.CSSProperties = {
  padding: '4px 8px',
  border: '1px solid #d1d5db',
  borderRadius: 4,
  fontSize: '0.875rem',
  width: 200,
};
