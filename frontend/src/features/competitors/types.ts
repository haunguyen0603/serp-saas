export type CompetitorRange = "7d" | "30d" | "90d";
export type CompetitorStatus =
  | "ranked"
  | "not_found_in_checked_depth"
  | "not_observed"
  | "ambiguous_match";
export type CoverageQuality = "complete" | "partial" | "insufficient_data";

export interface SelectedCompetitorSite {
  tracked_site_id: string;
  name: string;
  primary_domain: string | null;
  role: "primary" | "competitor";
}

export interface CompetitorSelection {
  project_id: string;
  primary_site: SelectedCompetitorSite | null;
  competitor_sites: SelectedCompetitorSite[];
  max_competitors: number;
  selection_basis: "current_selection";
  historical_alias_semantics: "current_active_aliases";
}

export interface CompetitorFilters {
  range: CompetitorRange;
  q?: string;
  group_id?: string;
  tag_ids?: string;
  tag_match?: "any" | "all";
  comparison_state?: string;
  opportunity?: boolean;
  opponent_site_id?: string;
  sort?: string;
  order?: "asc" | "desc";
  limit?: 25 | 50 | 100;
  cursor?: string;
}

export interface CompetitorSiteMetric {
  tracked_site_id: string;
  name: string;
  top_3: number;
  top_n: number;
  comparable_keywords: number;
  observed_top_n_coverage_pct: number;
  not_found_in_checked_depth: number;
  not_observed: number;
  ambiguous_match: number;
}

export interface HeadToHeadMetric {
  opponent_site_id: string;
  opponent_name: string;
  both_numeric_ranked: number;
  primary_ahead: number;
  tied: number;
  competitor_ahead: number;
  excluded_unpaired: number;
  opportunities: number;
}

export interface CompetitorOverview {
  project_id: string;
  device: string;
  range: CompetitorRange | "custom";
  as_of: string;
  effective_depth: number;
  top_n: number;
  keyword_cohort: number;
  qualifying_keywords: number;
  partial_or_unobserved_keywords: number;
  primary_site: SelectedCompetitorSite;
  sites: CompetitorSiteMetric[];
  comparisons: HeadToHeadMetric[];
  coverage_quality: CoverageQuality;
  latest_successful_check_at: string | null;
}

export interface CompetitorSiteObservation {
  tracked_site_id: string;
  name: string;
  status: CompetitorStatus;
  position: number | null;
  checked_depth: number;
  matched_url: string | null;
  matched_hostname: string | null;
}

export interface CompetitorKeywordRow {
  keyword_id: string;
  keyword: string;
  checked_at: string;
  rank_check_id: string;
  checked_depth: number;
  snapshot_complete: boolean;
  sites: CompetitorSiteObservation[];
  opponent_site_id: string | null;
  position_gap: number | null;
  comparison_state:
    | "both_ranked"
    | "my_site_ahead"
    | "competitor_ahead"
    | "tied"
    | "not_comparable";
  opportunity: boolean;
}

export interface CompetitorKeywordList {
  project_id: string;
  items: CompetitorKeywordRow[];
  next_cursor: string | null;
  has_more: boolean;
  total: number;
  top_n: number;
  opponent_site_id: string | null;
}

export interface CompetitorTrendSitePoint {
  tracked_site_id: string;
  name: string;
  top_n_appearances: number;
  comparable_keywords: number;
  observed_top_n_coverage_pct: number;
  not_observed: number;
}

export interface CompetitorTrendPoint {
  date: string;
  observed_keywords: number;
  coverage_quality: CoverageQuality;
  sites: CompetitorTrendSitePoint[];
}

export interface CompetitorTrends {
  project_id: string;
  range: CompetitorRange | "custom";
  top_n: number;
  points: CompetitorTrendPoint[];
  gaps_are_not_interpolated: boolean;
}

export interface CompetitorMatchedResult {
  position: number;
  url: string;
  hostname: string;
  title: string | null;
}

export interface CompetitorObservationDetail {
  project_id: string;
  keyword_id: string;
  keyword: string;
  rank_check_id: string;
  checked_at: string;
  search_engine: string;
  country_code: string;
  language_code: string;
  device: string;
  location: string | null;
  checked_depth: number;
  snapshot_complete: boolean;
  coverage_quality: CoverageQuality;
  sites: (CompetitorSiteObservation & {
    matched_results: CompetitorMatchedResult[];
  })[];
}
