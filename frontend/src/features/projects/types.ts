export type SearchEngine = "google";
export type Device = "desktop" | "mobile";
export type ProjectStatus = "active" | "archived";

export interface Project {
  id: string;
  name: string;
  search_engine: SearchEngine;
  country_code: string;
  language_code: string;
  device: Device;
  location: string | null;
  status: ProjectStatus;
  keyword_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  search_engine: SearchEngine;
  country_code: string;
  language_code: string;
  device: Device;
  location: string | null;
  keywords: string[];
}

export type ProjectUpdate = Partial<Omit<ProjectCreate, "keywords">> & {
  status?: ProjectStatus;
};
export interface InitialKeywordResult {
  submitted: number;
  normalized_unique: number;
  created: number;
  skipped_duplicates: number;
  skipped_empty: number;
}
export interface ProjectCreateResult {
  project: Project;
  keywords: InitialKeywordResult;
}
export interface ProjectListResponse {
  items: Project[];
  next_cursor: string | null;
  has_more: boolean;
}
export interface ProjectFilters {
  status?: ProjectStatus | "all";
  search?: string;
  limit?: number;
  cursor?: string | null;
}

export interface Keyword {
  id: string;
  keyword: string;
  active: boolean;
  group: KeywordOrganizationRef | null;
  tags: KeywordOrganizationRef[];
  created_at: string;
  updated_at: string;
}
export interface KeywordCreate {
  keyword: string;
  group_id?: string | null;
  tag_ids?: string[];
}
export interface KeywordBulkCreate {
  keywords: string[];
}
export interface KeywordBulkResult extends InitialKeywordResult {
  items: Keyword[];
}
export interface KeywordUpdate {
  keyword?: string;
  active?: boolean;
  group_id?: string | null;
  tag_ids?: string[];
}
export interface KeywordListResponse {
  items: Keyword[];
  next_cursor: string | null;
  has_more: boolean;
}
export interface KeywordFilters {
  search?: string;
  active?: "true" | "false" | "all";
  limit?: number;
  cursor?: string | null;
  group_id?: string;
  tag_ids?: string;
  tag_match?: "any" | "all";
}

export interface KeywordOrganizationRef {
  id: string;
  name: string;
}

export interface KeywordOrganization extends KeywordOrganizationRef {
  active_keyword_count: number;
  created_at: string;
  updated_at: string;
}

export interface KeywordOrganizationList {
  items: KeywordOrganization[];
}

export type KeywordBulkOperation =
  | "assign_group"
  | "add_tags"
  | "remove_tags"
  | "replace_tags"
  | "archive"
  | "restore";

export interface KeywordBulkOrganization {
  keyword_ids: string[];
  operation: KeywordBulkOperation;
  group_id?: string | null;
  tag_ids?: string[];
}

export interface KeywordBulkOrganizationResult {
  operation: KeywordBulkOperation;
  selected_count: number;
  affected_keyword_count: number;
  assignment_count: number | null;
}
