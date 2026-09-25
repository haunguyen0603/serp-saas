import type { AnalyticsRange } from "@/features/analytics/types";

export type ExplorerMovement =
  | "improved"
  | "declined"
  | "unchanged"
  | "entered_checked_depth"
  | "left_checked_depth"
  | "no_previous_data"
  | "never_checked";
export type ExplorerStatus = "ranked" | "not_found_in_depth" | "never_checked";
export type ExplorerSort =
  | "keyword"
  | "current_position"
  | "comparison_position"
  | "change";
export type ExplorerOrder = "asc" | "desc";

export interface ExplorerObservation {
  checked_at: string;
  position: number | null;
  status: "ranked" | "not_found_in_depth";
  depth: number;
  rank_check_id: string;
}

export interface ExplorerItem {
  keyword_id: string;
  keyword: string;
  keyword_status: "active" | "paused";
  tracked_site: { id: string; name: string };
  device: "desktop" | "mobile";
  comparison: ExplorerObservation | null;
  current: ExplorerObservation | null;
  movement: { type: ExplorerMovement; change: number | null };
}

export interface RankingExplorerResponse {
  project_id: string;
  device: "desktop" | "mobile";
  range: AnalyticsRange | "custom";
  compare_from: string | null;
  compare_to: string | null;
  comparison_basis:
    | "range_boundary"
    | "earliest_in_range"
    | "custom_dates"
    | "none";
  effective_depth: number;
  supported_position_buckets: string[];
  summary: {
    total: number;
    improved: number;
    declined: number;
    unchanged: number;
    entered_checked_depth: number;
    left_checked_depth: number;
    no_previous_data: number;
    never_checked: number;
  };
  page: { limit: number; next_cursor: string | null };
  items: ExplorerItem[];
}

export interface ExplorerParams {
  q?: string;
  range?: AnalyticsRange;
  compare_from?: string;
  compare_to?: string;
  movement?: ExplorerMovement;
  position_bucket?: string;
  tracked_site_id?: string;
  status?: ExplorerStatus;
  sort?: ExplorerSort;
  order?: ExplorerOrder;
  limit?: 25 | 50 | 100;
  cursor?: string;
  group_id?: string;
  tag_ids?: string;
  tag_match?: "any" | "all";
}
