import type { AuthenticatedRequest } from "@/features/auth/session";
import type {
  LatestRankingResponse,
  ProjectRankCheckResponse,
  RankCheckDetail,
  RankCheckListResponse,
  RankCheckStatus,
} from "./types";

const json = (body: object): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
  signal: AbortSignal.timeout(60_000),
});

export const rankingKeys = {
  all: (projectId: string) => ["projects", projectId, "rankings"] as const,
  latest: (projectId: string) =>
    ["projects", projectId, "rankings", "latest"] as const,
  history: (projectId: string, keywordId: string) =>
    ["projects", projectId, "keywords", keywordId, "rank-checks"] as const,
  detail: (projectId: string, keywordId: string, checkId: string) =>
    [
      "projects",
      projectId,
      "keywords",
      keywordId,
      "rank-checks",
      checkId,
    ] as const,
};

export const checkProject = (
  request: AuthenticatedRequest,
  projectId: string,
  keywordIds: string[] | null = null,
) =>
  request<ProjectRankCheckResponse>(
    `/api/v1/projects/${projectId}/rank-checks`,
    json({ keyword_ids: keywordIds }),
  );

export const checkKeyword = (
  request: AuthenticatedRequest,
  projectId: string,
  keywordId: string,
) =>
  request<RankCheckDetail>(
    `/api/v1/projects/${projectId}/keywords/${keywordId}/rank-checks`,
    json({}),
  );

export const listRankChecks = (
  request: AuthenticatedRequest,
  projectId: string,
  keywordId: string,
  options: {
    status?: RankCheckStatus | "all";
    limit?: number;
    cursor?: string | null;
  } = {},
) => {
  const query = new URLSearchParams();
  if (options.status) query.set("status", options.status);
  if (options.limit) query.set("limit", String(options.limit));
  if (options.cursor) query.set("cursor", options.cursor);
  const suffix = query.size ? `?${query}` : "";
  return request<RankCheckListResponse>(
    `/api/v1/projects/${projectId}/keywords/${keywordId}/rank-checks${suffix}`,
  );
};

export const getRankCheck = (
  request: AuthenticatedRequest,
  projectId: string,
  keywordId: string,
  checkId: string,
) =>
  request<RankCheckDetail>(
    `/api/v1/projects/${projectId}/keywords/${keywordId}/rank-checks/${checkId}`,
  );

export const getLatestRankings = (
  request: AuthenticatedRequest,
  projectId: string,
) =>
  request<LatestRankingResponse>(
    `/api/v1/projects/${projectId}/rankings/latest`,
  );
