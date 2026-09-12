export type RankCheckStatus = "pending" | "running" | "succeeded" | "failed";

export interface Ranking {
  tracked_site_id: string | null;
  tracked_domain_id: string | null;
  tracked_site_name: string;
  matched_domain: string;
  position: number;
  result_url: string;
  result_hostname: string;
  title: string | null;
}

export interface OrganicResult {
  position: number;
  title: string | null;
  url: string;
  hostname: string;
  displayed_url: string | null;
  snippet: string | null;
}

export interface ProviderAttempt {
  provider: string;
  attempt_number: number;
  status: "succeeded" | "failed";
  started_at: string;
  completed_at: string;
  error_code: string | null;
  provider_request_count: number;
}

export const providerName = (provider: string) => {
  if (provider === "serpapi") return "SerpApi";
  if (provider === "serper") return "Serper";
  if (provider === "fake") return "Test Provider";
  return provider;
};

export interface RankCheck {
  id: string;
  project_id: string;
  keyword_id: string;
  provider: string;
  status: RankCheckStatus;
  query_snapshot: string;
  search_engine_snapshot: string;
  country_code_snapshot: string;
  language_code_snapshot: string;
  device_snapshot: string;
  location_snapshot: string | null;
  result_limit: number;
  provider_request_count: number;
  provider_request_id: string | null;
  requested_at: string;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  result_count: number;
  rankings: Ranking[];
  provider_attempts: ProviderAttempt[];
  created_at: string;
}

export interface RankCheckDetail extends RankCheck {
  organic_results: OrganicResult[];
}

export interface RankCheckListResponse {
  items: RankCheck[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface ProjectRankCheckOutcome {
  keyword_id: string;
  check: RankCheck | null;
  error_code: string | null;
}

export interface ProjectRankCheckResponse {
  project_id: string;
  submitted_keywords: number;
  succeeded: number;
  failed: number;
  checks: ProjectRankCheckOutcome[];
}

export interface LatestKeywordRanking {
  keyword_id: string;
  keyword: string;
  latest_check: RankCheck | null;
}

export interface LatestRankingResponse {
  items: LatestKeywordRanking[];
}
