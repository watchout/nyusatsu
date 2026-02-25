/**
 * Case-related data types — SSOT-2 §6-2.
 *
 * Field names use camelCase (frontend convention) but the API returns
 * snake_case.  The api-client handles the conversion transparently.
 */

import type {
  CaseStatus,
  ChecklistItemStatus,
  ExtractionMethod,
  LifecycleStage,
  RiskLevel,
  TriggeredBy,
  Verdict,
} from './enums';

// ---------------------------------------------------------------------------
// Case
// ---------------------------------------------------------------------------

export interface Case {
  id: string;
  source: string;
  source_id: string;
  case_name: string;
  issuing_org: string;
  issuing_org_code?: string | null;
  bid_type: string | null;
  category: string | null;
  region: string | null;
  grade: string | null;
  submission_deadline: string | null; // ISO 8601
  opening_date: string | null;
  spec_url?: string | null;
  notice_url?: string | null;
  detail_url?: string | null;
  status: CaseStatus;
  current_lifecycle_stage: LifecycleStage;
  score: number | null;
  score_detail: ScoreDetail | null;
  first_seen_at: string;
  last_updated_at: string;
  // Embedded resources (from ?include= parameter)
  card?: CaseCard | null;
  eligibility?: EligibilityResult | null;
  checklist?: Checklist | null;
  latest_events?: CaseEvent[] | null;
}

export interface ScoreDetail {
  competition?: number;
  scale?: number;
  margin?: number;
  fit?: number;
  [key: string]: number | undefined;
}

// ---------------------------------------------------------------------------
// CaseCard (AI reading result)
// ---------------------------------------------------------------------------

export interface CaseCard {
  id: string;
  case_id: string;
  version: number;
  is_current: boolean;
  eligibility: Record<string, unknown> | null;
  schedule: Record<string, unknown> | null;
  business_content: Record<string, unknown> | null;
  submission_items: Record<string, unknown>[] | null;
  risk_factors: Record<string, unknown>[] | null;
  deadline_at: string | null;
  business_type: string | null;
  risk_level: RiskLevel | null;
  extraction_method: ExtractionMethod;
  is_scanned: boolean;
  assertion_counts: AssertionCounts | null;
  evidence: Record<string, unknown> | null;
  confidence_score: number | null;
  file_hash: string | null;
  status: string;
  llm_model: string | null;
  token_usage: Record<string, number> | null;
  extracted_at: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
  created_at: string;
}

export interface AssertionCounts {
  fact: number;
  inferred: number;
  caution: number;
}

// ---------------------------------------------------------------------------
// EligibilityResult
// ---------------------------------------------------------------------------

export interface EligibilityResult {
  id: string;
  case_id: string;
  case_card_id: string;
  version: number;
  is_current: boolean;
  verdict: Verdict;
  confidence: number;
  hard_fail_reasons: HardFailReason[];
  soft_gaps: SoftGap[];
  check_details: Record<string, unknown>;
  company_profile_snapshot: Record<string, unknown>;
  human_override: Verdict | null;
  override_reason: string | null;
  overridden_at: string | null;
  judged_at: string;
  created_at: string;
}

export interface HardFailReason {
  code: string;
  description: string;
  source_text?: string;
  [key: string]: unknown;
}

export interface SoftGap {
  code: string;
  description: string;
  severity: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Checklist
// ---------------------------------------------------------------------------

export interface Checklist {
  id: string;
  case_id: string;
  case_card_id: string;
  eligibility_result_id: string;
  version: number;
  is_current: boolean;
  checklist_items: ChecklistItem[];
  schedule_items: ScheduleItem[];
  warnings: string[];
  progress: ChecklistProgress;
  status: string;
  generated_at: string;
  completed_at: string | null;
  created_at: string;
}

export interface ChecklistItem {
  item_id: string;
  name: string;
  phase: 'bid_time' | 'performance_time';
  is_checked: boolean;
  status: ChecklistItemStatus;
  deadline: string | null;
  is_critical: boolean;
  notes: string | null;
  source: 'ai' | 'manual';
}

export interface ScheduleItem {
  name: string;
  date: string;
  is_critical: boolean;
  [key: string]: unknown;
}

export interface ChecklistProgress {
  total: number;
  done: number;
  rate: number;
}

// ---------------------------------------------------------------------------
// CaseEvent
// ---------------------------------------------------------------------------

export interface CaseEvent {
  id: string;
  case_id: string;
  event_type: string;
  from_status: string | null;
  to_status: string;
  triggered_by: TriggeredBy;
  actor_id: string;
  feature_origin: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface FoldedCheckOperations {
  event_type: '_folded_check_operations';
  count: number;
  first_at: string;
  last_at: string;
  summary: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Batch
// ---------------------------------------------------------------------------

export interface BatchLog {
  id: string;
  source: string;
  feature_origin: string;
  batch_type: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  total_fetched: number;
  new_count: number;
  updated_count: number;
  unchanged_count: number;
  error_count: number;
  error_details: Record<string, unknown>[] | null;
  metadata: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// CompanyProfile
// ---------------------------------------------------------------------------

export interface CompanyProfile {
  id: string;
  unified_qualification: boolean;
  grade: string;
  business_categories: string[];
  regions: string[];
  licenses: unknown[];
  certifications: unknown[];
  experience: unknown[];
  subcontractors: Record<string, unknown>[];
  updated_at: string;
  created_at: string;
}

export interface CompanyProfileUpdate {
  unified_qualification?: boolean;
  grade?: string;
  business_categories?: string[];
  regions?: string[];
  licenses?: unknown[];
  certifications?: unknown[];
  experience?: unknown[];
  subcontractors?: Record<string, unknown>[];
}

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export interface PriceSummary {
  total_records: number;
  period: { from_date: string; to_date: string };
  amount_stats: {
    median: number | null;
    q1: number | null;
    q3: number | null;
    mean: number | null;
    min: number | null;
    max: number | null;
  };
  participants_stats: {
    median: number | null;
    mean: number | null;
    single_bid_rate: number | null;
  };
  winning_rate_by_amount: { range: string; win_rate: number }[];
  trend_by_quarter: {
    quarter: string;
    median_amount: number | null;
    avg_participants: number | null;
  }[];
}
