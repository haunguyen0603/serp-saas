export type ReportPeriod = "7d" | "30d" | "90d" | "custom";
export type ReportType = "comparison_csv" | "history_csv" | "project_pdf";
export type ReportStatus =
  | "pending"
  | "queued"
  | "running"
  | "ready"
  | "failed"
  | "expired";

export interface ReportFilters {
  period: ReportPeriod;
  start_date?: string;
  end_date?: string;
  tracked_site_id?: string;
  keyword_group_id?: string;
  keyword_tag_ids?: string[];
  tag_match: "any" | "all";
  include_keyword_details: boolean;
}

export interface ReportObservation {
  checked_at_utc: string;
  position: number | null;
  depth: number;
  status: "ranked" | "not_found_in_depth";
}

export interface ReportPreviewRow {
  keyword_id: string;
  keyword: string;
  tracked_site_id: string;
  tracked_site_name: string;
  comparison: ReportObservation | null;
  current: ReportObservation | null;
  movement_type: string;
  numeric_change: number | null;
}

export interface ReportMetrics {
  distinct_keywords: number;
  keyword_site_pairs: number;
  distinct_tracked_sites: number;
  observed_pairs: number;
  never_checked: number;
  effective_depth: number;
  latest_successful_check_at: string | null;
  comparison_basis: string;
  distribution: Record<string, number>;
  movements: Record<string, number>;
  biggest_winners: ReportPreviewRow[];
  biggest_losers: ReportPreviewRow[];
}

export interface ReportPreview {
  project_id: string;
  project_name: string;
  device: string;
  period_start_utc: string;
  period_end_utc: string;
  report_timezone: "UTC";
  active_scope: "active_keywords_and_tracked_sites";
  no_matching_keywords: boolean;
  matching_keywords_without_observations: boolean;
  filters: Record<string, unknown>;
  metrics: ReportMetrics;
  sample: ReportPreviewRow[];
}

export interface GeneratedReport {
  id: string;
  project_id: string;
  report_schedule_id: string | null;
  report_type: ReportType;
  status: ReportStatus;
  period_start_utc: string;
  period_end_utc: string;
  filters_snapshot: Record<string, unknown>;
  metrics_snapshot: Record<string, unknown> | null;
  schema_version: number;
  mime_type: string | null;
  byte_size: number | null;
  filename: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  expires_at: string;
  error_code: string | null;
  attempt_count: number;
}

export interface GeneratedReportList {
  items: GeneratedReport[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface ReportSchedule {
  id: string;
  project_id: string;
  name: string;
  report_type: "project_pdf";
  frequency: "weekly" | "monthly";
  report_timezone: "UTC";
  scheduled_hour: number;
  weekday: number | null;
  month_day: number | null;
  filters: Record<string, unknown>;
  active: boolean;
  delivery_configured: boolean;
  recipient_mode: "verified_account";
  next_run_at_utc: string;
  last_run_at_utc: string | null;
  last_delivery_status: string | null;
  last_error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportScheduleList {
  items: ReportSchedule[];
  delivery_configured: boolean;
  recipient_mode: "verified_account";
}

export interface ReportScheduleInput extends ReportFilters {
  name: string;
  frequency: "weekly" | "monthly";
  scheduled_hour: number;
  weekday?: number;
  month_day?: number;
  active: boolean;
}

export interface ReportScheduleUpdateInput {
  name?: string;
  frequency?: "weekly" | "monthly";
  scheduled_hour?: number;
  weekday?: number | null;
  month_day?: number | null;
  active?: boolean;
  tracked_site_id?: string | null;
  keyword_group_id?: string | null;
  keyword_tag_ids?: string[];
  tag_match?: "any" | "all";
  include_keyword_details?: boolean;
}
