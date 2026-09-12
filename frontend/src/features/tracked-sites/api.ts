import type { AuthenticatedRequest } from "@/features/auth/session";
import type {
  TrackedDomain,
  TrackedDomainCreate,
  TrackedDomainUpdate,
  TrackedSite,
  TrackedSiteCreate,
  TrackedSiteFilters,
  TrackedSiteListResponse,
  TrackedSiteUpdate,
} from "./types";
const json = (method: "POST" | "PATCH", body: object): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
function query(filters: TrackedSiteFilters) {
  const parameters = new URLSearchParams();
  for (const [key, value] of Object.entries(filters))
    if (value !== undefined && value !== null && value !== "")
      parameters.set(key, String(value));
  const value = parameters.toString();
  return value ? `?${value}` : "";
}
export const trackedSiteKeys = {
  all: ["tracked-sites"] as const,
  lists: () => ["tracked-sites", "list"] as const,
  list: (filters: TrackedSiteFilters) =>
    ["tracked-sites", "list", filters] as const,
  detail: (id: string) => ["tracked-sites", id] as const,
};
export const createTrackedSite = (
  request: AuthenticatedRequest,
  input: TrackedSiteCreate,
) => request<TrackedSite>("/api/v1/tracked-sites", json("POST", input));
export const listTrackedSites = (
  request: AuthenticatedRequest,
  filters: TrackedSiteFilters = {},
) => request<TrackedSiteListResponse>(`/api/v1/tracked-sites${query(filters)}`);
export const getTrackedSite = (request: AuthenticatedRequest, id: string) =>
  request<TrackedSite>(`/api/v1/tracked-sites/${id}`);
export const updateTrackedSite = (
  request: AuthenticatedRequest,
  id: string,
  input: TrackedSiteUpdate,
) => request<TrackedSite>(`/api/v1/tracked-sites/${id}`, json("PATCH", input));
export const deleteTrackedSite = (request: AuthenticatedRequest, id: string) =>
  request<void>(`/api/v1/tracked-sites/${id}`, { method: "DELETE" });
export const addTrackedDomain = (
  request: AuthenticatedRequest,
  id: string,
  input: TrackedDomainCreate,
) =>
  request<TrackedDomain>(
    `/api/v1/tracked-sites/${id}/domains`,
    json("POST", input),
  );
export const updateTrackedDomain = (
  request: AuthenticatedRequest,
  id: string,
  domainId: string,
  input: TrackedDomainUpdate,
) =>
  request<TrackedDomain>(
    `/api/v1/tracked-sites/${id}/domains/${domainId}`,
    json("PATCH", input),
  );
export const deleteTrackedDomain = (
  request: AuthenticatedRequest,
  id: string,
  domainId: string,
) =>
  request<void>(`/api/v1/tracked-sites/${id}/domains/${domainId}`, {
    method: "DELETE",
  });
