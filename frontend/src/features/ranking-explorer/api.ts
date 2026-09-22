import type { AuthenticatedRequest } from "@/features/auth/session";
import type { ExplorerParams, RankingExplorerResponse } from "./types";

export const rankingExplorerKeys = {
  all: (projectId: string) =>
    ["projects", projectId, "rankings", "explorer"] as const,
  list: (projectId: string, params: ExplorerParams) =>
    [...rankingExplorerKeys.all(projectId), params] as const,
};

export const getRankingExplorer = (
  request: AuthenticatedRequest,
  projectId: string,
  params: ExplorerParams,
) => {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params))
    if (value !== undefined && value !== "") query.set(key, String(value));
  return request<RankingExplorerResponse>(
    `/api/v1/projects/${projectId}/ranking-explorer?${query}`,
  );
};
