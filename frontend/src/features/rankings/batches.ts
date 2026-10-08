import type { AuthenticatedRequest } from "@/features/auth/session";

export type BatchAccepted = {
  batch_id: string;
  job_id: string | null;
  status: string;
  requested_keyword_count: number;
};
export type Batch = {
  id: string;
  status: string;
  trigger_type: string;
  requested_keyword_count: number;
  queued_keyword_count: number;
  running_keyword_count: number;
  succeeded_keyword_count: number;
  failed_keyword_count: number;
  cancelled_keyword_count: number;
  progress_percent: number;
  requested_at: string;
  started_at: string | null;
  completed_at: string | null;
};
export type Schedule = {
  id: string;
  enabled: boolean;
  frequency: "daily" | "weekly";
  local_time: string;
  timezone: string;
  weekday: number;
  next_run_at: string;
};
export type Job = {
  id: string;
  keyword_id: string;
  keyword: string;
  status: string;
  attempt_count: number;
  rank_check_id: string | null;
  last_error_code: string | null;
};
export type Page<T> = {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
};
export function rankingFailureMessage(code: string | null): string {
  switch (code) {
    case "SERP_PROVIDER_UNSUPPORTED_CONFIGURATION":
      return "Ranking checks are not available for this project's search settings. Please contact support.";
    case "SERP_PROVIDER_NOT_CONFIGURED":
    case "SERP_NO_PROVIDER_AVAILABLE":
      return "Ranking checks are currently unavailable for this project. Please contact support.";
    case "SERP_PROVIDER_AUTH_ERROR":
      return "The ranking service could not authenticate. Please contact support.";
    case "SERP_PROVIDER_QUOTA_EXHAUSTED":
    case "SERP_PROVIDER_BUDGET_EXHAUSTED":
      return "The ranking service has reached its usage limit. Please contact support.";
    case "SERP_PROVIDER_TIMEOUT":
      return "The ranking check timed out. Please try again.";
    case "SERP_PROVIDER_RATE_LIMITED":
      return "The ranking service is busy. Please try again later.";
    case "SERP_PROVIDER_UNAVAILABLE":
      return "The ranking service is temporarily unavailable. Please try again later.";
    default:
      return "Check could not be completed";
  }
}
export const terminalBatch = (status: string) =>
  ["completed", "completed_with_errors", "failed", "cancelled"].includes(
    status,
  );
export const batchKey = (id: string) => ["projects", id, "batches"] as const;
export const batchUrl = (id: string) =>
  `/api/v1/projects/${id}/rank-check-batches`;
export const getBatch = (
  request: AuthenticatedRequest,
  project: string,
  id: string,
) => request<Batch>(`${batchUrl(project)}/${id}`);
