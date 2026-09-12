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
