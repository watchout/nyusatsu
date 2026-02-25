/**
 * Tests for API client — TASK-39.
 *
 * Validates envelope auto-unwrap, error handling, pagination, and query builder.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchJson,
  fetchPaginated,
  postJson,
  patchJson,
  buildQuery,
} from '../src/services/api-client';
import { ApiError } from '../src/types/api';

// ---------------------------------------------------------------------------
// Mock fetch
// ---------------------------------------------------------------------------

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function mockOk(data: unknown, meta?: unknown) {
  const body = meta ? { data, meta } : { data };
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(body),
  });
}

function mockError(status: number, code: string, message: string) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    json: () => Promise.resolve({ error: { code, message } }),
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

// ---------------------------------------------------------------------------
// fetchJson — auto-unwrap
// ---------------------------------------------------------------------------

describe('fetchJson', () => {
  it('unwraps SuccessResponse envelope and returns data', async () => {
    mockOk({ id: '1', name: 'Test' });
    const result = await fetchJson<{ id: string; name: string }>('/cases/1');
    expect(result).toEqual({ id: '1', name: 'Test' });
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/cases/1', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  });

  it('throws ApiError on 404 with structured error', async () => {
    mockError(404, 'NOT_FOUND', 'Case not found');
    await expect(fetchJson('/cases/missing')).rejects.toThrow(ApiError);
    try {
      mockError(404, 'NOT_FOUND', 'Case not found');
      await fetchJson('/cases/missing');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(404);
      expect(apiErr.code).toBe('NOT_FOUND');
      expect(apiErr.message).toBe('Case not found');
    }
  });

  it('throws ApiError on 409 conflict', async () => {
    mockError(409, 'LIFECYCLE_STAGE_MISMATCH', 'Stage changed');
    try {
      await fetchJson('/cases/1');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(409);
      expect((err as ApiError).code).toBe('LIFECYCLE_STAGE_MISMATCH');
    }
  });

  it('handles non-JSON error responses gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('Not JSON')),
    });
    try {
      await fetchJson('/broken');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(500);
      expect((err as ApiError).code).toBe('HTTP_500');
    }
  });
});

// ---------------------------------------------------------------------------
// fetchPaginated
// ---------------------------------------------------------------------------

describe('fetchPaginated', () => {
  it('returns data and meta from paginated response', async () => {
    mockOk(
      [{ id: '1' }, { id: '2' }],
      { page: 1, limit: 20, total: 50, total_pages: 3 },
    );
    const result = await fetchPaginated<{ id: string }>('/cases');
    expect(result.data).toHaveLength(2);
    expect(result.meta.total).toBe(50);
    expect(result.meta.total_pages).toBe(3);
  });
});

// ---------------------------------------------------------------------------
// postJson / patchJson
// ---------------------------------------------------------------------------

describe('postJson', () => {
  it('sends POST with body and unwraps response', async () => {
    mockOk({ batch_log_id: 'abc', status: 'running' });
    const result = await postJson('/batch/trigger', {
      source: 'chotatku_portal',
      batch_type: 'case_fetch',
    });
    expect(result).toEqual({ batch_log_id: 'abc', status: 'running' });
    const [, init] = mockFetch.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      source: 'chotatku_portal',
      batch_type: 'case_fetch',
    });
  });
});

describe('patchJson', () => {
  it('sends PATCH with body and unwraps response', async () => {
    mockOk({ grade: 'C' });
    const result = await patchJson('/company-profile', { grade: 'C' });
    expect(result).toEqual({ grade: 'C' });
    const [, init] = mockFetch.mock.calls[0];
    expect(init.method).toBe('PATCH');
  });
});

// ---------------------------------------------------------------------------
// buildQuery
// ---------------------------------------------------------------------------

describe('buildQuery', () => {
  it('builds query string from params', () => {
    const qs = buildQuery({ page: 1, limit: 20, search: 'test' });
    expect(qs).toBe('?page=1&limit=20&search=test');
  });

  it('skips null and undefined values', () => {
    const qs = buildQuery({ page: 1, search: null, status: undefined });
    expect(qs).toBe('?page=1');
  });

  it('returns empty string when no params', () => {
    expect(buildQuery({})).toBe('');
    expect(buildQuery({ a: null, b: undefined })).toBe('');
  });

  it('encodes special characters', () => {
    const qs = buildQuery({ search: '配送 業務' });
    expect(qs).toContain(encodeURIComponent('配送 業務'));
  });
});
