/**
 * API response envelope types — SSOT-3 §3.
 *
 * Matches backend app/schemas/envelope.py.
 */

/** Successful single-item response. */
export interface SuccessResponse<T = unknown> {
  data: T;
  meta?: Record<string, unknown>;
}

/** Successful paginated response. */
export interface PaginatedResponse<T = unknown> {
  data: T[];
  meta: PaginatedMeta;
}

export interface PaginatedMeta {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

/** Error response. */
export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

/** API error class with structured error data. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}
