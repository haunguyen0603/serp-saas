import type { AuthenticatedRequest } from "@/features/auth/session";
import type {
  GeneratedReport,
  GeneratedReportList,
  ReportFilters,
  ReportPreview,
  ReportSchedule,
  ReportScheduleInput,
  ReportScheduleList,
  ReportScheduleUpdateInput,
  ReportType,
} from "./types";

export const reportKeys = {
  all: (projectId: string) => ["projects", projectId, "reports"] as const,
  preview: (projectId: string, filters: ReportFilters) =>
    [...reportKeys.all(projectId), "preview", filters] as const,
  recent: (projectId: string) =>
    [...reportKeys.all(projectId), "recent"] as const,
  schedules: (projectId: string) =>
    [...reportKeys.all(projectId), "schedules"] as const,
};

const json = (method: "POST" | "PATCH", body?: object): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body ? JSON.stringify(body) : undefined,
});

function query(filters: ReportFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === "") continue;
    params.set(key, Array.isArray(value) ? value.join(",") : String(value));
  }
  return params.toString();
}

export const previewReport = (
  request: AuthenticatedRequest,
  projectId: string,
  filters: ReportFilters,
) =>
  request<ReportPreview>(
    `/api/v1/projects/${projectId}/reports/preview?${query(filters)}`,
  );

export const createReport = (
  request: AuthenticatedRequest,
  projectId: string,
  reportType: ReportType,
  filters: ReportFilters,
  idempotencyKey: string,
) =>
  request<GeneratedReport>(
    `/api/v1/projects/${projectId}/reports`,
    json("POST", {
      ...filters,
      keyword_tag_ids: filters.keyword_tag_ids ?? [],
      report_type: reportType,
      idempotency_key: idempotencyKey,
    }),
  );

export const listReports = (
  request: AuthenticatedRequest,
  projectId: string,
  cursor?: string | null,
) =>
  request<GeneratedReportList>(
    `/api/v1/projects/${projectId}/reports?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
  );

export const retryReport = (
  request: AuthenticatedRequest,
  projectId: string,
  reportId: string,
) =>
  request<GeneratedReport>(
    `/api/v1/projects/${projectId}/reports/${reportId}/retry`,
    json("POST"),
  );

export const listReportSchedules = (
  request: AuthenticatedRequest,
  projectId: string,
) =>
  request<ReportScheduleList>(`/api/v1/projects/${projectId}/report-schedules`);

export const createReportSchedule = (
  request: AuthenticatedRequest,
  projectId: string,
  input: ReportScheduleInput,
) =>
  request<ReportSchedule>(
    `/api/v1/projects/${projectId}/report-schedules`,
    json("POST", input),
  );

export const updateReportSchedule = (
  request: AuthenticatedRequest,
  projectId: string,
  scheduleId: string,
  input: ReportScheduleUpdateInput,
) =>
  request<ReportSchedule>(
    `/api/v1/projects/${projectId}/report-schedules/${scheduleId}`,
    json("PATCH", input),
  );

export const deleteReportSchedule = (
  request: AuthenticatedRequest,
  projectId: string,
  scheduleId: string,
) =>
  request<void>(
    `/api/v1/projects/${projectId}/report-schedules/${scheduleId}`,
    { method: "DELETE" },
  );
