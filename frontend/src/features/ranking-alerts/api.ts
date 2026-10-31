import type { AuthenticatedRequest } from "@/features/auth/session";

export interface AlertPreferences {
  enabled: boolean;
  notify_entered_top10: boolean;
  notify_left_top10: boolean;
  notify_improvement: boolean;
  notify_decline: boolean;
  movement_threshold: number;
  email_enabled: boolean;
}
export interface PreferencesResponse extends AlertPreferences {
  email_available: boolean;
}
export interface RankingAlert {
  id: string;
  project_id: string;
  keyword_id: string;
  tracked_site_id: string | null;
  alert_type:
    | "entered_top10"
    | "left_top10"
    | "rank_improved"
    | "rank_declined";
  previous_observation_id: string;
  current_observation_id: string;
  previous_rank: number | null;
  current_rank: number | null;
  rank_delta: number | null;
  keyword: string;
  project_name: string;
  site_name: string;
  device: string;
  observed_at: string;
  created_at: string;
  read_at: string | null;
}
export interface AlertList {
  items: RankingAlert[];
  next_cursor: string | null;
  has_more: boolean;
}
export const alertKeys = (userId?: string) =>
  ["ranking-alerts", userId] as const;
export const listAlerts = (
  request: AuthenticatedRequest,
  filters: { project_id?: string; unread_only?: boolean; cursor?: string },
) => {
  const params = new URLSearchParams({ limit: "25" });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, String(value));
  });
  return request<AlertList>(`/api/v1/ranking-alerts?${params}`);
};
export const unreadCount = (request: AuthenticatedRequest) =>
  request<{ count: number }>("/api/v1/ranking-alerts/unread-count");
export const readAlert = (request: AuthenticatedRequest, id: string) =>
  request<RankingAlert>(`/api/v1/ranking-alerts/${id}/read`, {
    method: "PATCH",
  });
export const readAllAlerts = (
  request: AuthenticatedRequest,
  projectId: string,
) =>
  request<void>(
    `/api/v1/ranking-alerts/mark-all-read${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`,
    { method: "POST" },
  );
export const getPreferences = (
  request: AuthenticatedRequest,
  projectId: string,
) =>
  request<PreferencesResponse>(
    `/api/v1/projects/${projectId}/ranking-alert-preferences`,
  );
export const savePreferences = (
  request: AuthenticatedRequest,
  projectId: string,
  body: AlertPreferences,
) =>
  request<PreferencesResponse>(
    `/api/v1/projects/${projectId}/ranking-alert-preferences`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
export const alertLabels = {
  entered_top10: "Entered Top 10",
  left_top10: "Left Top 10",
  rank_improved: "Improved",
  rank_declined: "Declined",
};
export const rankLabel = (rank: number | null) =>
  rank === null ? "Not found in Top 10" : `#${rank}`;
