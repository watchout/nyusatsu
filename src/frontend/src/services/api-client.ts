/**
 * API client — SSOT-3 §3 envelope auto-unwrap.
 *
 * All responses follow { data, meta? } or { error: { code, message } }.
 * This client transparently unwraps the envelope and throws ApiError
 * for non-2xx responses with structured error information.
 */

import { ApiError } from '../types/api';
import type {
  ErrorResponse,
  PaginatedMeta,
  PaginatedResponse,
  SuccessResponse,
} from '../types/api';

const API_BASE = '/api/v1';

// ---------------------------------------------------------------------------
// Low-level fetch wrapper
// ---------------------------------------------------------------------------

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const init: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  const res = await fetch(url, init);

  if (!res.ok) {
    let errorBody: ErrorResponse | null = null;
    try {
      errorBody = (await res.json()) as ErrorResponse;
    } catch {
      // Non-JSON error response
    }
    throw new ApiError(
      res.status,
      errorBody?.error?.code ?? `HTTP_${res.status}`,
      errorBody?.error?.message ?? `API error: ${res.status}`,
      errorBody?.error?.details,
    );
  }

  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Public API — single-item operations
// ---------------------------------------------------------------------------

/** GET with auto-unwrap of SuccessResponse envelope → data. */
export async function fetchJson<T>(path: string): Promise<T> {
  const envelope = await request<SuccessResponse<T>>('GET', path);
  return envelope.data;
}

/** GET that returns the full envelope (useful when meta is needed). */
export async function fetchEnvelope<T>(
  path: string,
): Promise<SuccessResponse<T>> {
  return request<SuccessResponse<T>>('GET', path);
}

/** GET paginated list — returns { data, meta }. */
export async function fetchPaginated<T>(
  path: string,
): Promise<{ data: T[]; meta: PaginatedMeta }> {
  const envelope = await request<PaginatedResponse<T>>('GET', path);
  return { data: envelope.data, meta: envelope.meta };
}

/** POST with auto-unwrap. */
export async function postJson<T>(
  path: string,
  body?: unknown,
): Promise<T> {
  const envelope = await request<SuccessResponse<T>>('POST', path, body);
  return envelope.data;
}

/** PATCH with auto-unwrap. */
export async function patchJson<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const envelope = await request<SuccessResponse<T>>('PATCH', path, body);
  return envelope.data;
}

/** DELETE with auto-unwrap (returns data which may be null). */
export async function deleteJson<T = null>(
  path: string,
): Promise<T> {
  const envelope = await request<SuccessResponse<T>>('DELETE', path);
  return envelope.data;
}

// ---------------------------------------------------------------------------
// Query-string helpers
// ---------------------------------------------------------------------------

/** Build a query string from a params object. Skips null/undefined values. */
export function buildQuery(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== null && v !== undefined && v !== '',
  );
  if (entries.length === 0) return '';
  const qs = entries
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  return `?${qs}`;
}
