export type TrackedSiteStatus = "active" | "archived";
export interface TrackedDomain {
  id: string;
  domain: string;
  is_primary: boolean;
  active: boolean;
  created_at: string;
  updated_at: string;
}
export interface TrackedSite {
  id: string;
  name: string;
  status: TrackedSiteStatus;
  primary_domain: string | null;
  domain_alias_count: number;
  domains: TrackedDomain[];
  created_at: string;
  updated_at: string;
}
export interface TrackedSiteListResponse {
  items: TrackedSite[];
  next_cursor: string | null;
  has_more: boolean;
}
export interface TrackedSiteCreate {
  name: string;
  primary_domain: string;
  aliases: string[];
}
export interface TrackedSiteUpdate {
  name?: string;
  status?: TrackedSiteStatus;
}
export interface TrackedDomainCreate {
  domain: string;
  make_primary: boolean;
}
export interface TrackedDomainUpdate {
  is_primary?: boolean;
  active?: boolean;
}
export interface TrackedSiteFilters {
  status?: TrackedSiteStatus | "all";
  search?: string;
  limit?: number;
  cursor?: string | null;
}
