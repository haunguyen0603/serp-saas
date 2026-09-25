import type { AuthenticatedRequest } from "@/features/auth/session";
import type {
  AnalyticsRange,
  KeywordRankingHistory,
  ProjectAnalyticsSummary,
  RankingMovers,
} from "./types";

export const projectAnalytics = {
  all: (projectId: string) =>
    ["projects", projectId, "rankings", "analytics"] as const,
  summary: (projectId: string, device: string, range: AnalyticsRange) =>
    [...projectAnalytics.all(projectId), "summary", device, range] as const,
  movers: (projectId: string, device: string, range: AnalyticsRange) =>
    [...projectAnalytics.all(projectId), "movers", device, range] as const,
  history: (
    projectId: string,
    keywordId: string,
    trackedSiteId: string,
    device: string,
    range: AnalyticsRange,
  ) =>
    [
      ...projectAnalytics.all(projectId),
      "history",
      keywordId,
      trackedSiteId,
      device,
      range,
    ] as const,
  organization: (
    projectId: string,
    scope: string,
    device: string,
    range: AnalyticsRange,
  ) =>
    [
      ...projectAnalytics.all(projectId),
      "organization",
      scope,
      device,
      range,
    ] as const,
};

const parameters = (device: string, range: AnalyticsRange) =>
  new URLSearchParams({ device, range }).toString();

export const getProjectAnalytics = (
  request: AuthenticatedRequest,
  projectId: string,
  device: string,
  range: AnalyticsRange,
) =>
  request<ProjectAnalyticsSummary>(
    `/api/v1/projects/${projectId}/analytics/summary?${parameters(device, range)}`,
  );

export const getProjectMovers = (
  request: AuthenticatedRequest,
  projectId: string,
  device: string,
  range: AnalyticsRange,
) =>
  request<RankingMovers>(
    `/api/v1/projects/${projectId}/analytics/movers?${parameters(device, range)}&limit=10`,
  );

export const getOrganizationAnalytics = (
  request: AuthenticatedRequest,
  projectId: string,
  device: string,
  range: AnalyticsRange,
  scope: { group_id: string } | { tag_id: string },
) =>
  request<ProjectAnalyticsSummary>(
    `/api/v1/projects/${projectId}/analytics/organization-summary?${new URLSearchParams(
      { device, range, ...scope },
    )}`,
  );

export const getKeywordRankingHistory = (
  request: AuthenticatedRequest,
  projectId: string,
  keywordId: string,
  trackedSiteId: string,
  device: string,
  range: AnalyticsRange,
) =>
  request<KeywordRankingHistory>(
    `/api/v1/projects/${projectId}/keywords/${keywordId}/ranking-history?${new URLSearchParams(
      { tracked_site_id: trackedSiteId, device, range },
    )}`,
  );
