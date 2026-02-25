/**
 * Analytics (P3) — price summary analytics page (SSOT-2 §6-7, SSOT-3 §4-9).
 *
 * Shows: price summary stats, winning rate by amount range, trend by quarter.
 * Filters: keyword, issuing_org, category, period_months.
 */

import { useCallback, useEffect, useState } from 'react';
import { fetchJson, buildQuery } from '../services/api-client';
import type { PriceSummary } from '../types/case';

interface Filters {
  keyword: string;
  issuing_org: string;
  category: string;
  period_months: number;
}

const defaultFilters: Filters = {
  keyword: '',
  issuing_org: '',
  category: '',
  period_months: 12,
};

function formatAmount(val: number | null): string {
  if (val === null) return '—';
  return val.toLocaleString('ja-JP') + '円';
}

function formatRate(val: number | null): string {
  if (val === null) return '—';
  return `${(val * 100).toFixed(1)}%`;
}

// ---- Sub-components ----

function StatsCards({ summary }: { summary: PriceSummary }) {
  const { amount_stats, participants_stats, total_records } = summary;

  return (
    <div data-testid="stats-cards" style={statsGridStyle}>
      <div style={statCardStyle}>
        <div style={statLabelStyle}>対象件数</div>
        <div style={statValueStyle}>{total_records.toLocaleString()}件</div>
      </div>
      <div style={statCardStyle}>
        <div style={statLabelStyle}>落札額（中央値）</div>
        <div style={statValueStyle}>{formatAmount(amount_stats.median)}</div>
      </div>
      <div style={statCardStyle}>
        <div style={statLabelStyle}>落札額（平均）</div>
        <div style={statValueStyle}>{formatAmount(amount_stats.mean)}</div>
      </div>
      <div style={statCardStyle}>
        <div style={statLabelStyle}>参加者数（平均）</div>
        <div style={statValueStyle}>
          {participants_stats.mean !== null ? participants_stats.mean.toFixed(1) + '社' : '—'}
        </div>
      </div>
      <div style={statCardStyle}>
        <div style={statLabelStyle}>1社入札率</div>
        <div style={statValueStyle}>{formatRate(participants_stats.single_bid_rate)}</div>
      </div>
      <div style={statCardStyle}>
        <div style={statLabelStyle}>落札額レンジ</div>
        <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          {formatAmount(amount_stats.min)} 〜 {formatAmount(amount_stats.max)}
        </div>
      </div>
    </div>
  );
}

function WinningRateTable({ data }: { data: PriceSummary['winning_rate_by_amount'] }) {
  if (!data || data.length === 0) return null;

  return (
    <div data-testid="winning-rate-table">
      <h3 style={sectionHeaderStyle}>金額帯別落札率</h3>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>金額帯</th>
            <th style={thStyle}>落札率</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              <td style={tdStyle}>{row.range}</td>
              <td style={tdStyle}>{formatRate(row.win_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TrendTable({ data }: { data: PriceSummary['trend_by_quarter'] }) {
  if (!data || data.length === 0) return null;

  return (
    <div data-testid="trend-table">
      <h3 style={sectionHeaderStyle}>四半期別トレンド</h3>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>四半期</th>
            <th style={thStyle}>落札額（中央値）</th>
            <th style={thStyle}>参加者数（平均）</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              <td style={tdStyle}>{row.quarter}</td>
              <td style={tdStyle}>{formatAmount(row.median_amount)}</td>
              <td style={tdStyle}>
                {row.avg_participants !== null ? row.avg_participants.toFixed(1) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---- Main component ----

export default function Analytics() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [summary, setSummary] = useState<PriceSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = buildQuery({
        keyword: filters.keyword || undefined,
        issuing_org: filters.issuing_org || undefined,
        category: filters.category || undefined,
        period_months: filters.period_months,
      });
      const data = await fetchJson<PriceSummary>(`/analytics/price-summary${query}`);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleFilterChange = (key: keyof Filters, value: string | number) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div style={pageStyle}>
      <h1 style={titleStyle}>Analytics</h1>

      {/* Filters */}
      <div data-testid="analytics-filters" style={filterBarStyle}>
        <input
          data-testid="filter-keyword"
          type="text"
          placeholder="キーワード検索"
          value={filters.keyword}
          onChange={(e) => handleFilterChange('keyword', e.target.value)}
          style={inputStyle}
        />
        <input
          data-testid="filter-issuing-org"
          type="text"
          placeholder="発注機関"
          value={filters.issuing_org}
          onChange={(e) => handleFilterChange('issuing_org', e.target.value)}
          style={inputStyle}
        />
        <select
          data-testid="filter-category"
          value={filters.category}
          onChange={(e) => handleFilterChange('category', e.target.value)}
          style={selectStyle}
        >
          <option value="">全カテゴリ</option>
          <option value="物品の販売">物品の販売</option>
          <option value="役務の提供">役務の提供</option>
          <option value="物品の製造">物品の製造</option>
        </select>
        <select
          data-testid="filter-period"
          value={filters.period_months}
          onChange={(e) => handleFilterChange('period_months', Number(e.target.value))}
          style={selectStyle}
        >
          <option value={6}>6ヶ月</option>
          <option value={12}>12ヶ月</option>
          <option value={24}>24ヶ月</option>
        </select>
      </div>

      {/* Loading/Error/Content */}
      {loading && <div data-testid="analytics-loading">読み込み中…</div>}
      {error && <div data-testid="analytics-error">エラー: {error}</div>}

      {summary && !loading && (
        <div data-testid="analytics-content">
          <StatsCards summary={summary} />
          <WinningRateTable data={summary.winning_rate_by_amount} />
          <TrendTable data={summary.trend_by_quarter} />

          <div style={periodStyle}>
            対象期間: {summary.period.from_date} 〜 {summary.period.to_date}
          </div>
        </div>
      )}

      {!summary && !loading && !error && (
        <div data-testid="analytics-empty" style={emptyStyle}>
          データがありません。
        </div>
      )}
    </div>
  );
}

// ---- Styles ----

const pageStyle: React.CSSProperties = {
  padding: 16,
};

const titleStyle: React.CSSProperties = {
  fontSize: '1.25rem',
  fontWeight: 700,
  margin: '0 0 16px',
};

const filterBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
  marginBottom: 16,
};

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  fontSize: '0.85rem',
};

const selectStyle: React.CSSProperties = {
  padding: '6px 10px',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  fontSize: '0.85rem',
  backgroundColor: '#fff',
};

const statsGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
  gap: 12,
  marginBottom: 24,
};

const statCardStyle: React.CSSProperties = {
  padding: 12,
  backgroundColor: '#f9fafb',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
};

const statLabelStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  fontWeight: 600,
  color: '#6b7280',
  marginBottom: 4,
};

const statValueStyle: React.CSSProperties = {
  fontSize: '1.1rem',
  fontWeight: 700,
  color: '#1f2937',
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: '1rem',
  fontWeight: 700,
  margin: '16px 0 8px',
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  marginBottom: 16,
};

const thStyle: React.CSSProperties = {
  padding: '8px 12px',
  textAlign: 'left',
  fontSize: '0.8rem',
  fontWeight: 600,
  color: '#6b7280',
  borderBottom: '2px solid #e5e7eb',
};

const tdStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: '0.85rem',
  borderBottom: '1px solid #f3f4f6',
};

const periodStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#9ca3af',
  marginTop: 16,
};

const emptyStyle: React.CSSProperties = {
  color: '#6b7280',
  fontSize: '0.9rem',
  padding: 24,
  textAlign: 'center',
};
