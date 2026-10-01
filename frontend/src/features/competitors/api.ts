import type { AuthenticatedRequest } from "@/features/auth/session";
import type {
  CompetitorFilters,
  CompetitorKeywordList,
  CompetitorObservationDetail,
  CompetitorOverview,
  CompetitorSelection,
  CompetitorTrends,
} from "./types";

const base = (projectId: string) => `/api/v1/projects/${projectId}`;

function query(filters: CompetitorFilters, mode: "all" | "analytics") {
  const values = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === "" || value === false) continue;
    if (
      mode === "analytics" &&
      [
        "q",
        "comparison_state",
        "opportunity",
        "opponent_site_id",
        "sort",
        "order",
        "limit",
        "cursor",
      ].includes(key)
    )
      continue;
    values.set(key, String(value));
  }
  const serialized = values.toString();
  return serialized ? `?${serialized}` : "";
}

export const competitorKeys = {
  all: (projectId: string) => ["projects", projectId, "competitors"] as const,
  selection: (projectId: string) =>
    [...competitorKeys.all(projectId), "selection"] as const,
  overview: (projectId: string, filters: CompetitorFilters) =>
    [...competitorKeys.all(projectId), "overview", filters] as const,
  keywords: (projectId: string, filters: CompetitorFilters) =>
    [...competitorKeys.all(projectId), "keywords", filters] as const,
  trends: (projectId: string, filters: CompetitorFilters) =>
    [...competitorKeys.all(projectId), "trends", filters] as const,
  observation: (
    projectId: string,
    keywordId: string,
    range: CompetitorFilters["range"],
  ) =>
    [
      ...competitorKeys.all(projectId),
      "observation",
      keywordId,
      range,
    ] as const,
};

export const getCompetitorSelection = (
  request: AuthenticatedRequest,
  projectId: string,
) => request<CompetitorSelection>(`${base(projectId)}/competitor-sites`);

export const replaceCompetitorSelection = (
  request: AuthenticatedRequest,
  projectId: string,
  primaryId: string,
  competitorIds: string[],
) =>
  request<CompetitorSelection>(`${base(projectId)}/competitor-sites`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      primary_tracked_site_id: primaryId,
      competitor_tracked_site_ids: competitorIds,
    }),
  });

export const getCompetitorOverview = (
  request: AuthenticatedRequest,
  projectId: string,
  filters: CompetitorFilters,
) =>
  request<CompetitorOverview>(
    `${base(projectId)}/competitors/overview${query(filters, "analytics")}`,
  );

export const getCompetitorKeywords = (
  request: AuthenticatedRequest,
  projectId: string,
  filters: CompetitorFilters,
) =>
  request<CompetitorKeywordList>(
    `${base(projectId)}/competitors/keywords${query(filters, "all")}`,
  );

export const getCompetitorTrends = (
  request: AuthenticatedRequest,
  projectId: string,
  filters: CompetitorFilters,
) =>
  request<CompetitorTrends>(
    `${base(projectId)}/competitors/trends${query(filters, "analytics")}`,
  );

export const getCompetitorObservation = (
  request: AuthenticatedRequest,
  projectId: string,
  keywordId: string,
  range: CompetitorFilters["range"],
) =>
  request<CompetitorObservationDetail>(
    `${base(projectId)}/competitors/keywords/${keywordId}/observations?range=${range}`,
  );
