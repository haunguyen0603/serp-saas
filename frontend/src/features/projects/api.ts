import type { AuthenticatedRequest } from "@/features/auth/session";
import type {
  Keyword,
  KeywordBulkCreate,
  KeywordBulkOrganization,
  KeywordBulkOrganizationResult,
  KeywordBulkResult,
  KeywordCreate,
  KeywordFilters,
  KeywordListResponse,
  KeywordOrganization,
  KeywordOrganizationList,
  KeywordUpdate,
  Project,
  ProjectCreate,
  ProjectCreateResult,
  ProjectFilters,
  ProjectListResponse,
  ProjectUpdate,
} from "./types";

function json(method: "POST" | "PATCH", body: object): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
function query(filters: object) {
  const parameters = new URLSearchParams();
  for (const [key, value] of Object.entries(filters))
    if (value !== undefined && value !== null && value !== "")
      parameters.set(key, String(value));
  const result = parameters.toString();
  return result ? `?${result}` : "";
}

export const projectKeys = {
  all: ["projects"] as const,
  lists: () => ["projects", "list"] as const,
  list: (filters: ProjectFilters) => ["projects", "list", filters] as const,
  detail: (id: string) => ["projects", id] as const,
  keywords: (id: string) => ["projects", id, "keywords"] as const,
  keywordList: (id: string, filters: KeywordFilters) =>
    ["projects", id, "keywords", filters] as const,
  groups: (id: string) => ["projects", id, "keyword-groups"] as const,
  tags: (id: string) => ["projects", id, "keyword-tags"] as const,
};
export const createProject = (
  request: AuthenticatedRequest,
  input: ProjectCreate,
) => request<ProjectCreateResult>("/api/v1/projects", json("POST", input));
export const listProjects = (
  request: AuthenticatedRequest,
  filters: ProjectFilters = {},
) => request<ProjectListResponse>(`/api/v1/projects${query(filters)}`);
export const getProject = (request: AuthenticatedRequest, id: string) =>
  request<Project>(`/api/v1/projects/${id}`);
export const updateProject = (
  request: AuthenticatedRequest,
  id: string,
  input: ProjectUpdate,
) => request<Project>(`/api/v1/projects/${id}`, json("PATCH", input));
export const deleteProject = (request: AuthenticatedRequest, id: string) =>
  request<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
const keywordPath = (id: string) => `/api/v1/projects/${id}/keywords`;
export const createKeyword = (
  request: AuthenticatedRequest,
  id: string,
  input: KeywordCreate,
) => request<Keyword>(keywordPath(id), json("POST", input));
export const bulkCreateKeywords = (
  request: AuthenticatedRequest,
  id: string,
  input: KeywordBulkCreate,
) => request<KeywordBulkResult>(`${keywordPath(id)}/bulk`, json("POST", input));
export const listKeywords = (
  request: AuthenticatedRequest,
  id: string,
  filters: KeywordFilters = {},
) => request<KeywordListResponse>(`${keywordPath(id)}${query(filters)}`);
export const getKeyword = (
  request: AuthenticatedRequest,
  id: string,
  keywordId: string,
) => request<Keyword>(`${keywordPath(id)}/${keywordId}`);
export const updateKeyword = (
  request: AuthenticatedRequest,
  id: string,
  keywordId: string,
  input: KeywordUpdate,
) => request<Keyword>(`${keywordPath(id)}/${keywordId}`, json("PATCH", input));
export const deleteKeyword = (
  request: AuthenticatedRequest,
  id: string,
  keywordId: string,
) => request<void>(`${keywordPath(id)}/${keywordId}`, { method: "DELETE" });

const organizationPath = (id: string, kind: "groups" | "tags") =>
  `/api/v1/projects/${id}/keyword-${kind}`;
export const listKeywordGroups = (request: AuthenticatedRequest, id: string) =>
  request<KeywordOrganizationList>(organizationPath(id, "groups"));
export const listKeywordTags = (request: AuthenticatedRequest, id: string) =>
  request<KeywordOrganizationList>(organizationPath(id, "tags"));
export const createKeywordOrganization = (
  request: AuthenticatedRequest,
  id: string,
  kind: "groups" | "tags",
  name: string,
) =>
  request<KeywordOrganization>(
    organizationPath(id, kind),
    json("POST", { name }),
  );
export const updateKeywordOrganization = (
  request: AuthenticatedRequest,
  id: string,
  kind: "groups" | "tags",
  entityId: string,
  name: string,
) =>
  request<KeywordOrganization>(
    `${organizationPath(id, kind)}/${entityId}`,
    json("PATCH", { name }),
  );
export const deleteKeywordOrganization = (
  request: AuthenticatedRequest,
  id: string,
  kind: "groups" | "tags",
  entityId: string,
) =>
  request<void>(`${organizationPath(id, kind)}/${entityId}`, {
    method: "DELETE",
  });
export const bulkOrganizeKeywords = (
  request: AuthenticatedRequest,
  id: string,
  input: KeywordBulkOrganization,
) =>
  request<KeywordBulkOrganizationResult>(
    `${keywordPath(id)}/bulk-organize`,
    json("POST", input),
  );
