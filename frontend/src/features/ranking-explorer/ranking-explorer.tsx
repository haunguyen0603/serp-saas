"use client";

import {
  Badge,
  Button,
  Card,
  Dialog,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Select,
  Skeleton,
  Table,
} from "@/design-system/ui";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Fragment, useEffect, useMemo, useState } from "react";
import {
  getKeywordRankingHistory,
  projectAnalytics,
} from "@/features/analytics/api";
import type { AnalyticsRange } from "@/features/analytics/types";
import {
  getProject,
  listKeywordGroups,
  listKeywordTags,
  projectKeys,
} from "@/features/projects/api";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import {
  getRankCheck,
  listRankChecks,
  rankingKeys,
} from "@/features/rankings/api";
import { RankCheckDetail } from "@/features/rankings/rank-check-detail";
import { RankCheckHistory } from "@/features/rankings/rank-check-history";
import type { RankCheck } from "@/features/rankings/types";
import {
  listTrackedSites,
  trackedSiteKeys,
} from "@/features/tracked-sites/api";
import { ApiError } from "@/lib/api/client";
import { getRankingExplorer, rankingExplorerKeys } from "./api";
import type {
  ExplorerItem,
  ExplorerMovement,
  ExplorerOrder,
  ExplorerParams,
  ExplorerSort,
  ExplorerStatus,
} from "./types";

const movements: { value: ExplorerMovement | ""; label: string }[] = [
  { value: "", label: "All movements" },
  { value: "improved", label: "Improved" },
  { value: "declined", label: "Declined" },
  { value: "unchanged", label: "Unchanged" },
  { value: "entered_checked_depth", label: "Entered checked depth" },
  { value: "left_checked_depth", label: "Left checked depth" },
  { value: "no_previous_data", label: "No previous data" },
  { value: "never_checked", label: "Never checked" },
];

const utcDate = (daysAgo = 0) => {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() - daysAgo);
  return value.toISOString().slice(0, 10);
};

const movementLabel = (type: ExplorerMovement, depth: number) =>
  ({
    improved: "Improved",
    declined: "Declined",
    unchanged: "Unchanged",
    entered_checked_depth: `Entered Top ${depth}`,
    left_checked_depth: `Left Top ${depth}`,
    no_previous_data: "No previous data",
    never_checked: "Never checked",
  })[type];

const positionLabel = (observation: ExplorerItem["current"]) => {
  if (!observation) return "Never checked";
  return observation.position === null
    ? `Not found in Top ${observation.depth}`
    : `#${observation.position}`;
};

const bucketLabel = (bucket: string, depth: number) => {
  const labels: Record<string, string> = {
    top_3: "Top 3",
    positions_4_10: "4–10",
    positions_11_20: "11–20",
    positions_21_50: "21–50",
    positions_51_100: "51–100",
    not_found_in_depth: `Not found in Top ${depth}`,
  };
  return labels[bucket] ?? bucket;
};

export function RankingExplorer({ projectId }: { projectId: string }) {
  const auth = useProtectedAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const serialized = searchParams.toString();
  const params = useMemo<ExplorerParams>(() => {
    const value = new URLSearchParams(serialized);
    const custom = value.get("range") === "custom";
    return {
      q: value.get("q") || undefined,
      range: custom
        ? undefined
        : ((value.get("range") || "30d") as AnalyticsRange),
      compare_from: custom ? value.get("compare_from") || undefined : undefined,
      compare_to: custom ? value.get("compare_to") || undefined : undefined,
      movement: (value.get("movement") || undefined) as
        | ExplorerMovement
        | undefined,
      position_bucket: value.get("position_bucket") || undefined,
      tracked_site_id: value.get("tracked_site_id") || undefined,
      status: (value.get("status") || undefined) as ExplorerStatus | undefined,
      sort: (value.get("sort") || "keyword") as ExplorerSort,
      order: (value.get("order") || "asc") as ExplorerOrder,
      limit: Number(value.get("limit") || 50) as 25 | 50 | 100,
      cursor: value.get("cursor") || undefined,
      group_id: value.get("group_id") || undefined,
      tag_ids: value.get("tag_ids") || undefined,
      tag_match: (value.get("tag_match") || "any") as "any" | "all",
    };
  }, [serialized]);
  const [search, setSearch] = useState(params.q ?? "");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [expanded, setExpanded] = useState<ExplorerItem | null>(null);
  const [historyRange, setHistoryRange] = useState<AnalyticsRange>("30d");
  const [detailCheck, setDetailCheck] = useState<RankCheck | null>(null);
  const [historyCursors, setHistoryCursors] = useState<string[]>([]);
  const project = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => getProject(auth.request, projectId),
    enabled: auth.isAuthenticated,
    retry: false,
  });
  const sites = useQuery({
    queryKey: trackedSiteKeys.list({ status: "active", limit: 200 }),
    queryFn: () =>
      listTrackedSites(auth.request, { status: "active", limit: 200 }),
    enabled: auth.isAuthenticated,
  });
  const groups = useQuery({
    queryKey: projectKeys.groups(projectId),
    queryFn: () => listKeywordGroups(auth.request, projectId),
    enabled: auth.isAuthenticated,
  });
  const tags = useQuery({
    queryKey: projectKeys.tags(projectId),
    queryFn: () => listKeywordTags(auth.request, projectId),
    enabled: auth.isAuthenticated,
  });
  const explorer = useQuery({
    queryKey: rankingExplorerKeys.list(projectId, params),
    queryFn: () => getRankingExplorer(auth.request, projectId, params),
    enabled: auth.isAuthenticated,
    placeholderData: keepPreviousData,
    retry: false,
  });
  const historyCursor = historyCursors.at(-1) ?? null;
  const rankChecks = useQuery({
    queryKey: [
      ...rankingKeys.history(projectId, expanded?.keyword_id ?? ""),
      historyCursor ?? "first",
      10,
    ],
    queryFn: () =>
      listRankChecks(auth.request, projectId, expanded?.keyword_id ?? "", {
        limit: 10,
        cursor: historyCursor,
      }),
    enabled: auth.isAuthenticated && expanded !== null,
  });
  const chart = useQuery({
    queryKey: projectAnalytics.history(
      projectId,
      expanded?.keyword_id ?? "",
      expanded?.tracked_site.id ?? "",
      project.data?.device ?? "desktop",
      historyRange,
    ),
    queryFn: () =>
      getKeywordRankingHistory(
        auth.request,
        projectId,
        expanded?.keyword_id ?? "",
        expanded?.tracked_site.id ?? "",
        project.data?.device ?? "desktop",
        historyRange,
      ),
    enabled: auth.isAuthenticated && expanded !== null && !!project.data,
  });
  const detail = useQuery({
    queryKey: rankingKeys.detail(
      projectId,
      expanded?.keyword_id ?? "",
      detailCheck?.id ?? "",
    ),
    queryFn: () =>
      getRankCheck(
        auth.request,
        projectId,
        expanded?.keyword_id ?? "",
        detailCheck?.id ?? "",
      ),
    enabled: expanded !== null && detailCheck !== null,
  });

  const updateUrl = (
    updates: Record<string, string | null>,
    resetCursor = true,
  ) => {
    const next = new URLSearchParams(serialized);
    for (const [key, value] of Object.entries(updates)) {
      if (!value) next.delete(key);
      else next.set(key, value);
    }
    if (resetCursor && !("cursor" in updates)) next.delete("cursor");
    const query = next.toString();
    router.push(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(params.q ?? ""), 0);
    return () => window.clearTimeout(timer);
  }, [params.q]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = search.trim();
      if (next !== (params.q ?? "")) updateUrl({ q: next || null });
    }, 300);
    return () => window.clearTimeout(timer);
    // updateUrl reads the latest URL; params.q is the debounce key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, params.q]);

  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  if (project.isPending) return <Skeleton label="Loading Ranking Explorer…" />;
  if (project.isError)
    return (
      <ErrorState onRetry={() => void project.refetch()}>
        Project could not be loaded.
      </ErrorState>
    );

  const data = explorer.data;
  const depth = data?.effective_depth ?? 10;
  const custom = searchParams.get("range") === "custom";
  const activeFilters: { key: string; label: string }[] = [];
  if (params.q) activeFilters.push({ key: "q", label: `“${params.q}”` });
  if (params.movement)
    activeFilters.push({
      key: "movement",
      label: movementLabel(params.movement, depth),
    });
  if (params.position_bucket)
    activeFilters.push({
      key: "position_bucket",
      label: bucketLabel(params.position_bucket, depth),
    });
  if (params.tracked_site_id)
    activeFilters.push({
      key: "tracked_site_id",
      label:
        sites.data?.items.find((site) => site.id === params.tracked_site_id)
          ?.name ?? "Tracked Site",
    });
  if (params.status)
    activeFilters.push({
      key: "status",
      label: params.status.replaceAll("_", " "),
    });
  if (params.group_id)
    activeFilters.push({
      key: "group_id",
      label:
        params.group_id === "none"
          ? "No Group"
          : (groups.data?.items.find((group) => group.id === params.group_id)
              ?.name ?? "Group"),
    });
  if (params.tag_ids) {
    const selectedTagIds = params.tag_ids.split(",");
    activeFilters.push({
      key: "tag_ids",
      label: `${params.tag_match === "all" ? "All" : "Any"}: ${selectedTagIds
        .map(
          (id) => tags.data?.items.find((tag) => tag.id === id)?.name ?? "Tag",
        )
        .join(", ")}`,
    });
  }

  const selectRange = (value: string) => {
    if (value === "custom")
      updateUrl({
        range: "custom",
        compare_from: utcDate(30),
        compare_to: utcDate(),
      });
    else
      updateUrl({
        range: value === "30d" ? null : value,
        compare_from: null,
        compare_to: null,
      });
  };
  const toggleHistory = (item: ExplorerItem) => {
    setExpanded((current) =>
      current?.keyword_id === item.keyword_id &&
      current.tracked_site.id === item.tracked_site.id
        ? null
        : item,
    );
    setHistoryCursors([]);
    setDetailCheck(null);
  };

  return (
    <main>
      <Link className="ui-text-link" href={`/app/projects/${projectId}`}>
        ← {project.data.name}
      </Link>
      <PageHeader
        eyebrow={`${project.data.device} · ${project.data.country_code}`}
        title="Ranking Explorer"
        description="Filter and compare persisted ranking observations without running new checks."
      />
      <Card className="explorer-filters">
        <div className="explorer-search-row">
          <label>
            Search Keywords
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search keyword…"
            />
          </label>
          <Button
            className="explorer-mobile-filter-toggle"
            aria-expanded={filtersOpen}
            aria-controls="explorer-filter-panel"
            onClick={() => setFiltersOpen((value) => !value)}
          >
            Filters
          </Button>
        </div>
        <div
          id="explorer-filter-panel"
          className={`explorer-filter-panel ${filtersOpen ? "is-open" : ""}`}
        >
          <label>
            Date comparison
            <Select
              value={custom ? "custom" : (params.range ?? "30d")}
              onChange={(event) => selectRange(event.target.value)}
            >
              <option value="7d">Current vs 7 days ago</option>
              <option value="30d">Current vs 30 days ago</option>
              <option value="90d">Current vs 90 days ago</option>
              <option value="custom">Custom dates</option>
            </Select>
          </label>
          <label>
            Movement
            <Select
              value={params.movement ?? ""}
              onChange={(event) =>
                updateUrl({ movement: event.target.value || null })
              }
            >
              {movements.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Current position
            <Select
              value={params.position_bucket ?? ""}
              onChange={(event) =>
                updateUrl({ position_bucket: event.target.value || null })
              }
            >
              <option value="">All positions</option>
              {(
                data?.supported_position_buckets ?? [
                  "top_3",
                  "positions_4_10",
                  "not_found_in_depth",
                ]
              ).map((bucket) => (
                <option key={bucket} value={bucket}>
                  {bucketLabel(bucket, depth)}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Tracked Site
            <Select
              value={params.tracked_site_id ?? ""}
              onChange={(event) =>
                updateUrl({ tracked_site_id: event.target.value || null })
              }
            >
              <option value="">All Sites</option>
              {sites.data?.items.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Current status
            <Select
              value={params.status ?? ""}
              onChange={(event) =>
                updateUrl({ status: event.target.value || null })
              }
            >
              <option value="">All statuses</option>
              <option value="ranked">Ranked</option>
              <option value="not_found_in_depth">
                Not found in checked depth
              </option>
              <option value="never_checked">Never checked</option>
            </Select>
          </label>
          <label>
            Keyword Group
            <Select
              value={params.group_id ?? ""}
              onChange={(event) =>
                updateUrl({ group_id: event.target.value || null })
              }
            >
              <option value="">All Groups</option>
              <option value="none">No Group</option>
              {groups.data?.items.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Keyword Tags
            <Select
              multiple
              aria-label="Keyword Tags"
              value={params.tag_ids?.split(",") ?? []}
              onChange={(event) => {
                const values = Array.from(
                  event.target.selectedOptions,
                  (option) => option.value,
                );
                updateUrl({
                  tag_ids: values.length ? values.join(",") : null,
                  tag_match: values.length ? (params.tag_match ?? "any") : null,
                });
              }}
            >
              {tags.data?.items.map((tag) => (
                <option key={tag.id} value={tag.id}>
                  {tag.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Tag matching
            <Select
              value={params.tag_match ?? "any"}
              disabled={!params.tag_ids}
              onChange={(event) =>
                updateUrl({
                  tag_match:
                    event.target.value === "any" ? null : event.target.value,
                })
              }
            >
              <option value="any">Any selected Tag</option>
              <option value="all">All selected Tags</option>
            </Select>
          </label>
          <label>
            Sort by
            <Select
              value={params.sort ?? "keyword"}
              onChange={(event) =>
                updateUrl({
                  sort:
                    event.target.value === "keyword"
                      ? null
                      : event.target.value,
                })
              }
            >
              <option value="keyword">Keyword</option>
              <option value="comparison_position">Previous position</option>
              <option value="current_position">Current position</option>
              <option value="change">Change</option>
            </Select>
          </label>
          <label>
            Sort order
            <Select
              value={params.order ?? "asc"}
              onChange={(event) =>
                updateUrl({
                  order: event.target.value === "asc" ? null : "desc",
                })
              }
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </Select>
          </label>
        </div>
        {custom && (
          <div className="explorer-custom-dates">
            <label>
              From date (UTC)
              <Input
                type="date"
                value={params.compare_from ?? ""}
                onChange={(event) =>
                  updateUrl({ compare_from: event.target.value || null })
                }
              />
            </label>
            <label>
              To date (UTC)
              <Input
                type="date"
                value={params.compare_to ?? ""}
                min={params.compare_from}
                onChange={(event) =>
                  updateUrl({ compare_to: event.target.value || null })
                }
              />
            </label>
          </div>
        )}
        {!!activeFilters.length && (
          <div className="explorer-filter-chips" aria-label="Active filters">
            {activeFilters.map((filter) => (
              <Badge key={filter.key} tone="info">
                <button
                  type="button"
                  aria-label={`Remove ${filter.label} filter`}
                  onClick={() => updateUrl({ [filter.key]: null })}
                >
                  {filter.label} ×
                </button>
              </Badge>
            ))}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setSearch("");
                router.push(pathname, { scroll: false });
              }}
            >
              Clear all
            </Button>
          </div>
        )}
      </Card>
      {explorer.isPending && <Skeleton label="Loading ranking results…" />}
      {explorer.isFetching && !explorer.isPending && (
        <p role="status" className="text-sm text-secondary">
          Updating ranking results…
        </p>
      )}
      {explorer.isError && (
        <ErrorState onRetry={() => void explorer.refetch()}>
          {explorer.error instanceof ApiError
            ? explorer.error.message
            : "Unable to load ranking results."}
        </ErrorState>
      )}
      {data && (
        <>
          <Card
            className="explorer-summary"
            aria-label="Filtered results summary"
          >
            <strong>{data.summary.total} results</strong>
            <span>{data.summary.improved} improved</span>
            <span>{data.summary.declined} declined</span>
            <span>{data.summary.unchanged} unchanged</span>
            <span>
              {data.summary.entered_checked_depth} entered Top {depth}
            </span>
            <span>
              {data.summary.left_checked_depth} left Top {depth}
            </span>
          </Card>
          {!data.items.length && (
            <EmptyState
              title={
                activeFilters.length
                  ? "No Keywords match these filters"
                  : "No ranking data yet"
              }
            >
              {activeFilters.length ? (
                <Button onClick={() => router.push(pathname)}>
                  Clear filters
                </Button>
              ) : (
                "Run a rank check to start building ranking history."
              )}
            </EmptyState>
          )}
          {!!data.items.length && (
            <Table aria-label="Ranking comparison" className="w-full">
              <thead>
                <tr>
                  {[
                    ["keyword", "Keyword"],
                    [null, "Tracked Site"],
                    ["comparison_position", "Previous"],
                    ["current_position", "Current"],
                    ["change", "Change"],
                    [null, "Status"],
                    [null, "History"],
                  ].map(([field, label]) => (
                    <th
                      key={label}
                      aria-sort={
                        field && params.sort === field
                          ? params.order === "desc"
                            ? "descending"
                            : "ascending"
                          : undefined
                      }
                    >
                      {field ? (
                        <button
                          type="button"
                          className="explorer-sort"
                          onClick={() =>
                            updateUrl({
                              sort: field,
                              order:
                                params.sort === field && params.order === "asc"
                                  ? "desc"
                                  : "asc",
                            })
                          }
                        >
                          {label}
                        </button>
                      ) : (
                        label
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => {
                  const rowKey = `${item.keyword_id}:${item.tracked_site.id}`;
                  const open =
                    expanded?.keyword_id === item.keyword_id &&
                    expanded.tracked_site.id === item.tracked_site.id;
                  return (
                    <Fragment key={rowKey}>
                      <tr>
                        <td>
                          <button
                            type="button"
                            className="ui-text-link keyword-history-trigger"
                            aria-expanded={open}
                            aria-controls={`explorer-history-${rowKey}`}
                            onClick={() => toggleHistory(item)}
                          >
                            {item.keyword}
                          </button>
                        </td>
                        <td>{item.tracked_site.name}</td>
                        <td>{positionLabel(item.comparison)}</td>
                        <td>{positionLabel(item.current)}</td>
                        <td>
                          {item.movement.change === null
                            ? "—"
                            : item.movement.change > 0
                              ? `+${item.movement.change}`
                              : item.movement.change}
                        </td>
                        <td>{movementLabel(item.movement.type, depth)}</td>
                        <td>{open ? "Expanded" : "Select Keyword"}</td>
                      </tr>
                      {open && (
                        <tr className="keyword-history-row">
                          <td className="keyword-history-cell" colSpan={7}>
                            <RankCheckHistory
                              id={`explorer-history-${rowKey}`}
                              keyword={item.keyword}
                              checks={rankChecks.data?.items ?? []}
                              loading={rankChecks.isPending}
                              error={rankChecks.isError}
                              page={historyCursors.length}
                              hasNextPage={rankChecks.data?.has_more ?? false}
                              onPreviousPage={() =>
                                setHistoryCursors((value) => value.slice(0, -1))
                              }
                              onNextPage={() => {
                                const cursor = rankChecks.data?.next_cursor;
                                if (cursor)
                                  setHistoryCursors((value) => [
                                    ...value,
                                    cursor,
                                  ]);
                              }}
                              onOpen={setDetailCheck}
                              onRetry={() => void rankChecks.refetch()}
                              chart={chart.data}
                              chartLoading={chart.isPending}
                              chartError={chart.isError}
                              chartRange={historyRange}
                              trackedSites={[item.tracked_site]}
                              trackedSiteId={item.tracked_site.id}
                              onChartRangeChange={setHistoryRange}
                              onTrackedSiteChange={() => {}}
                              onChartRetry={() => void chart.refetch()}
                            />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </Table>
          )}
          <nav className="explorer-pagination" aria-label="Explorer pagination">
            <label>
              Page size
              <Select
                value={params.limit ?? 50}
                onChange={(event) =>
                  updateUrl({
                    limit:
                      event.target.value === "50" ? null : event.target.value,
                  })
                }
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </Select>
            </label>
            <Button
              disabled={!params.cursor}
              onClick={() => updateUrl({ cursor: null }, false)}
            >
              First page
            </Button>
            <Button
              disabled={!data.page.next_cursor}
              onClick={() =>
                updateUrl({ cursor: data.page.next_cursor }, false)
              }
            >
              Next page
            </Button>
          </nav>
        </>
      )}
      <Dialog
        open={detailCheck !== null}
        onClose={() => setDetailCheck(null)}
        title="Rank Check detail"
      >
        {detail.isPending && <Skeleton label="Loading Rank Check detail…" />}
        {detail.isError && (
          <ErrorState>Rank Check detail could not be loaded.</ErrorState>
        )}
        {detail.data && <RankCheckDetail check={detail.data} />}
      </Dialog>
    </main>
  );
}
