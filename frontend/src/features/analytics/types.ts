export type AnalyticsRange = "7d" | "30d" | "90d";

export interface RankingDistribution {
  effective_depth: number;
  buckets: Record<string, number>;
}

export interface ProjectAnalyticsSummary {
  project_id: string;
  device: "desktop" | "mobile";
  range: AnalyticsRange;
  as_of: string;
  comparison_basis: "range_boundary" | "earliest_in_range" | "none";
  total_keywords: number;
  observed_keywords: number;
  never_checked: number;
  ranked_keywords: number;
  not_found_in_depth: number;
  top_3: number;
  top_10: number;
  improved: number;
  declined: number;
  unchanged: number;
  newly_ranked: number;
  lost_ranking: number;
  entered_checked_depth: number;
  left_checked_depth: number;
  no_previous_data: number;
  distribution: RankingDistribution;
}

export interface RankingMover {
  keyword_id: string;
  keyword: string;
  tracked_site_id: string;
  tracked_site_name: string;
  previous_position: number;
  current_position: number;
  change: number;
}

export interface RankingMovers {
  winners: RankingMover[];
  losers: RankingMover[];
}

export interface RankingHistoryPoint {
  checked_at: string;
  position: number | null;
  status: "ranked" | "not_found_in_depth";
  checked_depth: number;
  rank_check_id: string;
}

export interface KeywordRankingHistory {
  keyword_id: string;
  keyword: string;
  tracked_site: { id: string; name: string };
  device: "desktop" | "mobile";
  range: AnalyticsRange;
  points: RankingHistoryPoint[];
}
