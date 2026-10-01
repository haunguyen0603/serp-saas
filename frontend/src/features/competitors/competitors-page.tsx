"use client";

import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Select,
  Skeleton,
  StatCard,
  Table,
} from "@/design-system/ui";
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
  listTrackedSites,
  trackedSiteKeys,
} from "@/features/tracked-sites/api";
import { ApiError } from "@/lib/api/client";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Fragment, useEffect, useMemo, useState } from "react";
import {
  competitorKeys,
  getCompetitorKeywords,
  getCompetitorObservation,
  getCompetitorOverview,
  getCompetitorSelection,
  getCompetitorTrends,
  replaceCompetitorSelection,
} from "./api";
import type {
  CompetitorFilters,
  CompetitorRange,
  CompetitorSiteObservation,
  CompetitorTrends,
} from "./types";

const chartColors = [
  "#315efb",
  "#0f8a6a",
  "#a45d08",
  "#8b5cf6",
  "#d9467a",
  "#475569",
];

const formatDate = (value: string | null) =>
  value
    ? `${new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      }).format(new Date(value))} UTC`
    : "No successful observation";

function message(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Competitor analytics could not be loaded.";
}

function statusLabel(value: CompetitorSiteObservation) {
  if (value.position !== null) return `#${value.position}`;
  if (value.status === "not_found_in_checked_depth")
    return `Not found in Top ${value.checked_depth}`;
  if (value.status === "ambiguous_match") return "Ambiguous match";
  return "No comparable observation";
}

function CoverageChart({ data }: { data: CompetitorTrends }) {
  if (!data.points.length) return null;
  const sites = data.points[0]?.sites ?? [];
  const width = 720;
  const height = 220;
  const x = (index: number) =>
    data.points.length === 1
      ? width / 2
      : (index / (data.points.length - 1)) * width;
  const y = (value: number) => height - (value / 100) * height;
  return (
    <Card className="mt-6">
      <h2 className="text-xl font-semibold">
        Observed Top-{data.top_n} coverage trend
      </h2>
      <p className="mt-1 text-sm text-secondary">
        Missing UTC days are gaps, not interpolated observations. Each point
        shows its own denominator.
      </p>
      <div className="mt-5 overflow-hidden">
        <svg
          viewBox={`-12 -12 ${width + 24} ${height + 24}`}
          role="img"
          aria-labelledby="competitor-chart-title competitor-chart-description"
          className="h-auto w-full"
        >
          <title id="competitor-chart-title">
            Observed Top-{data.top_n} coverage by site
          </title>
          <desc id="competitor-chart-description">
            Coverage percentage by real UTC observation date. Missing dates are
            not connected.
          </desc>
          {[0, 25, 50, 75, 100].map((tick) => (
            <line
              key={tick}
              x1="0"
              x2={width}
              y1={y(tick)}
              y2={y(tick)}
              stroke="currentColor"
              opacity="0.12"
            />
          ))}
          {sites.map((site, siteIndex) =>
            data.points.slice(1).map((point, index) => {
              const previous = data.points[index];
              const days =
                (new Date(`${point.date}T00:00:00Z`).getTime() -
                  new Date(`${previous.date}T00:00:00Z`).getTime()) /
                86400000;
              const from = previous.sites.find(
                (value) => value.tracked_site_id === site.tracked_site_id,
              );
              const to = point.sites.find(
                (value) => value.tracked_site_id === site.tracked_site_id,
              );
              return days === 1 && from && to ? (
                <line
                  key={`${site.tracked_site_id}-${point.date}`}
                  x1={x(index)}
                  x2={x(index + 1)}
                  y1={y(from.observed_top_n_coverage_pct)}
                  y2={y(to.observed_top_n_coverage_pct)}
                  stroke={chartColors[siteIndex % chartColors.length]}
                  strokeWidth="3"
                />
              ) : null;
            }),
          )}
          {sites.flatMap((site, siteIndex) =>
            data.points.map((point, index) => {
              const value = point.sites.find(
                (item) => item.tracked_site_id === site.tracked_site_id,
              );
              return value ? (
                <circle
                  key={`${site.tracked_site_id}-${point.date}-point`}
                  cx={x(index)}
                  cy={y(value.observed_top_n_coverage_pct)}
                  r="4"
                  fill={chartColors[siteIndex % chartColors.length]}
                />
              ) : null;
            }),
          )}
        </svg>
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-sm">
        {sites.map((site, index) => (
          <span key={site.tracked_site_id} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{
                backgroundColor: chartColors[index % chartColors.length],
              }}
            />
            {site.name}
          </span>
        ))}
      </div>
      <details className="mt-5">
        <summary className="cursor-pointer font-medium">
          Accessible trend table
        </summary>
        <Table className="mt-3">
          <thead>
            <tr>
              <th>Date (UTC)</th>
              <th>Coverage quality</th>
              {sites.map((site) => (
                <th key={site.tracked_site_id}>{site.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.points.map((point) => (
              <tr key={point.date}>
                <td>{point.date}</td>
                <td>{point.coverage_quality.replaceAll("_", " ")}</td>
                {sites.map((site) => {
                  const value = point.sites.find(
                    (item) => item.tracked_site_id === site.tracked_site_id,
                  );
                  return (
                    <td key={site.tracked_site_id}>
                      {value
                        ? `${value.observed_top_n_coverage_pct}% (${value.top_n_appearances}/${value.comparable_keywords})`
                        : "No observation"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </Table>
      </details>
    </Card>
  );
}

export function CompetitorsPage({ projectId }: { projectId: string }) {
  const auth = useProtectedAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const serialized = searchParams.toString();
  const queryClient = useQueryClient();
  const filters = useMemo<CompetitorFilters>(() => {
    const values = new URLSearchParams(serialized);
    return {
      range: (values.get("range") || "30d") as CompetitorRange,
      q: values.get("q") || undefined,
      group_id: values.get("group_id") || undefined,
      tag_ids: values.get("tag_ids") || undefined,
      tag_match: (values.get("tag_match") || "any") as "any" | "all",
      comparison_state: values.get("comparison_state") || "all",
      opportunity: values.get("opportunity") === "true",
      opponent_site_id: values.get("opponent_site_id") || undefined,
      sort: values.get("sort") || "keyword",
      order: (values.get("order") || "asc") as "asc" | "desc",
      limit: Number(values.get("limit") || 50) as 25 | 50 | 100,
      cursor: values.get("cursor") || undefined,
    };
  }, [serialized]);
  const [search, setSearch] = useState(filters.q ?? "");
  const [primaryId, setPrimaryId] = useState("");
  const [competitorIds, setCompetitorIds] = useState<string[]>([]);
  const [expandedKeywordId, setExpandedKeywordId] = useState<string | null>(
    null,
  );

  const project = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => getProject(auth.request, projectId),
    enabled: auth.isAuthenticated,
    retry: false,
  });
  const sites = useQuery({
    queryKey: trackedSiteKeys.list({ status: "active", limit: 100 }),
    queryFn: () =>
      listTrackedSites(auth.request, { status: "active", limit: 100 }),
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
  const selection = useQuery({
    queryKey: competitorKeys.selection(projectId),
    queryFn: () => getCompetitorSelection(auth.request, projectId),
    enabled: auth.isAuthenticated,
    retry: false,
  });
  const analyticsEnabled =
    auth.isAuthenticated && !!selection.data?.primary_site;
  const overview = useQuery({
    queryKey: competitorKeys.overview(projectId, filters),
    queryFn: () => getCompetitorOverview(auth.request, projectId, filters),
    enabled: analyticsEnabled,
    placeholderData: keepPreviousData,
    retry: false,
  });
  const keywords = useQuery({
    queryKey: competitorKeys.keywords(projectId, filters),
    queryFn: () => getCompetitorKeywords(auth.request, projectId, filters),
    enabled: analyticsEnabled,
    placeholderData: keepPreviousData,
    retry: false,
  });
  const trends = useQuery({
    queryKey: competitorKeys.trends(projectId, filters),
    queryFn: () => getCompetitorTrends(auth.request, projectId, filters),
    enabled: analyticsEnabled,
    retry: false,
  });
  const detail = useQuery({
    queryKey: competitorKeys.observation(
      projectId,
      expandedKeywordId ?? "",
      filters.range,
    ),
    queryFn: () =>
      getCompetitorObservation(
        auth.request,
        projectId,
        expandedKeywordId ?? "",
        filters.range,
      ),
    enabled: analyticsEnabled && expandedKeywordId !== null,
    retry: false,
  });
  const saveSelection = useMutation({
    mutationFn: () =>
      replaceCompetitorSelection(
        auth.request,
        projectId,
        primaryId,
        competitorIds,
      ),
    onSuccess: async (value) => {
      queryClient.setQueryData(competitorKeys.selection(projectId), value);
      await queryClient.invalidateQueries({
        queryKey: competitorKeys.all(projectId),
      });
    },
  });

  const updateUrl = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(serialized);
    for (const [key, value] of Object.entries(updates)) {
      if (!value) next.delete(key);
      else next.set(key, value);
    }
    if (!("cursor" in updates)) next.delete("cursor");
    const value = next.toString();
    router.push(value ? `${pathname}?${value}` : pathname, { scroll: false });
  };

  useEffect(() => {
    if (!selection.data) return;
    const timer = window.setTimeout(() => {
      setPrimaryId(selection.data?.primary_site?.tracked_site_id ?? "");
      setCompetitorIds(
        selection.data?.competitor_sites.map((site) => site.tracked_site_id) ??
          [],
      );
    }, 0);
    return () => window.clearTimeout(timer);
  }, [selection.data]);
  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(filters.q ?? ""), 0);
    return () => window.clearTimeout(timer);
  }, [filters.q]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const value = search.trim();
      if (value !== (filters.q ?? "")) updateUrl({ q: value || null });
    }, 300);
    return () => window.clearTimeout(timer);
    // updateUrl intentionally uses the latest serialized URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, filters.q]);

  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  if (project.isPending || selection.isPending || sites.isPending)
    return <Skeleton label="Loading Competitors…" rows={6} />;
  if (project.isError || selection.isError || sites.isError)
    return (
      <ErrorState
        onRetry={() =>
          void Promise.all([
            project.refetch(),
            selection.refetch(),
            sites.refetch(),
          ])
        }
      >
        {message(project.error || selection.error || sites.error)}
      </ErrorState>
    );

  const selectedOpponent =
    filters.opponent_site_id ||
    selection.data.competitor_sites[0]?.tracked_site_id;
  const opponent = selection.data.competitor_sites.find(
    (site) => site.tracked_site_id === selectedOpponent,
  );
  const overviewError = overview.error || keywords.error || trends.error;

  return (
    <main>
      <Link className="ui-text-link" href={`/app/projects/${projectId}`}>
        ← {project.data.name}
      </Link>
      <PageHeader
        eyebrow="Persisted SERP observations"
        title="Competitors"
        description="Compare your site with selected tracked sites using the same successful Top-10 snapshots. This view never runs a new rank check."
      />

      <Card className="mb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Comparison sites</h2>
            <p className="mt-1 text-sm text-secondary">
              Select one primary site and up to five competitors. Historical
              snapshots are matched using current active aliases.
            </p>
          </div>
          <Button
            variant="primary"
            disabled={!primaryId || saveSelection.isPending}
            loading={saveSelection.isPending}
            onClick={() => saveSelection.mutate()}
          >
            Save selection
          </Button>
        </div>
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <label>
            Primary site
            <Select
              className="mt-2"
              value={primaryId}
              onChange={(event) => {
                setPrimaryId(event.target.value);
                setCompetitorIds((current) =>
                  current.filter((id) => id !== event.target.value),
                );
              }}
            >
              <option value="">Select your site</option>
              {sites.data.items.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name} · {site.primary_domain ?? "No primary domain"}
                </option>
              ))}
            </Select>
          </label>
          <fieldset>
            <legend>Compare with ({competitorIds.length}/5)</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {sites.data.items
                .filter((site) => site.id !== primaryId)
                .map((site) => (
                  <label
                    key={site.id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <Checkbox
                      checked={competitorIds.includes(site.id)}
                      disabled={
                        !competitorIds.includes(site.id) &&
                        competitorIds.length >= 5
                      }
                      onChange={(event) =>
                        setCompetitorIds((current) =>
                          event.target.checked
                            ? [...current, site.id].slice(0, 5)
                            : current.filter((id) => id !== site.id),
                        )
                      }
                    />
                    {site.name}
                  </label>
                ))}
            </div>
          </fieldset>
        </div>
        {saveSelection.isError && (
          <Alert className="mt-4 text-danger">
            {message(saveSelection.error)}
          </Alert>
        )}
      </Card>

      {!selection.data.primary_site ? (
        <EmptyState title="Select a primary site">
          Configure the comparison lens above. Existing sites, aliases,
          rankings, and quota remain unchanged.
        </EmptyState>
      ) : (
        <>
          {!selection.data.competitor_sites.length && (
            <Alert className="mb-6">
              No competitor is selected yet. Primary-site coverage remains
              available, but head-to-head metrics need at least one competitor.
            </Alert>
          )}
          <Card className="mb-6">
            <h2 className="text-lg font-semibold">Filters</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <label>
                Range
                <Select
                  value={filters.range}
                  onChange={(event) =>
                    updateUrl({
                      range:
                        event.target.value === "30d"
                          ? null
                          : event.target.value,
                    })
                  }
                >
                  <option value="7d">7 days</option>
                  <option value="30d">30 days</option>
                  <option value="90d">90 days</option>
                </Select>
              </label>
              <label>
                Keyword search
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search keywords"
                />
              </label>
              <label>
                Group
                <Select
                  value={filters.group_id ?? ""}
                  onChange={(event) =>
                    updateUrl({ group_id: event.target.value || null })
                  }
                >
                  <option value="">All groups</option>
                  <option value="none">No group</option>
                  {groups.data?.items.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </Select>
              </label>
              <label>
                Opponent
                <Select
                  value={selectedOpponent ?? ""}
                  onChange={(event) =>
                    updateUrl({ opponent_site_id: event.target.value || null })
                  }
                >
                  {!selection.data.competitor_sites.length && (
                    <option value="">No competitor</option>
                  )}
                  {selection.data.competitor_sites.map((site) => (
                    <option
                      key={site.tracked_site_id}
                      value={site.tracked_site_id}
                    >
                      {site.name}
                    </option>
                  ))}
                </Select>
              </label>
              <label>
                Tags
                <Select
                  multiple
                  value={(filters.tag_ids ?? "").split(",").filter(Boolean)}
                  onChange={(event) =>
                    updateUrl({
                      tag_ids:
                        Array.from(event.target.selectedOptions)
                          .map((option) => option.value)
                          .join(",") || null,
                    })
                  }
                  aria-label="Keyword tags"
                >
                  {tags.data?.items.map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.name}
                    </option>
                  ))}
                </Select>
              </label>
              <label>
                Tag match
                <Select
                  value={filters.tag_match}
                  onChange={(event) =>
                    updateUrl({
                      tag_match:
                        event.target.value === "any"
                          ? null
                          : event.target.value,
                    })
                  }
                >
                  <option value="any">Any selected tag</option>
                  <option value="all">All selected tags</option>
                </Select>
              </label>
              <label>
                Comparison state
                <Select
                  value={filters.comparison_state}
                  onChange={(event) =>
                    updateUrl({
                      comparison_state:
                        event.target.value === "all"
                          ? null
                          : event.target.value,
                    })
                  }
                >
                  <option value="all">All states</option>
                  <option value="both_ranked">Both ranked</option>
                  <option value="my_site_ahead">My site ahead</option>
                  <option value="competitor_ahead">Competitor ahead</option>
                  <option value="tied">Tied</option>
                </Select>
              </label>
              <label className="flex items-end gap-2 pb-2">
                <Checkbox
                  checked={filters.opportunity ?? false}
                  onChange={(event) =>
                    updateUrl({
                      opportunity: event.target.checked ? "true" : null,
                    })
                  }
                />
                Opportunities only
              </label>
              <label>
                Sort by
                <Select
                  value={filters.sort}
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
                  <option value="primary_position">Primary position</option>
                  <option value="competitor_position">
                    Competitor position
                  </option>
                  <option value="position_gap">Position gap</option>
                  <option value="checked_at">Observation time</option>
                </Select>
              </label>
              <label>
                Sort order
                <Select
                  value={filters.order}
                  onChange={(event) =>
                    updateUrl({
                      order:
                        event.target.value === "asc"
                          ? null
                          : event.target.value,
                    })
                  }
                >
                  <option value="asc">Ascending</option>
                  <option value="desc">Descending</option>
                </Select>
              </label>
            </div>
          </Card>

          {overviewError && (
            <ErrorState
              onRetry={() =>
                void Promise.all([
                  overview.refetch(),
                  keywords.refetch(),
                  trends.refetch(),
                ])
              }
            >
              {message(overviewError)}
            </ErrorState>
          )}
          {(overview.isPending || keywords.isPending || trends.isPending) && (
            <Skeleton label="Loading competitor analytics…" rows={5} />
          )}
          {overview.data && (
            <>
              <Alert className="mb-6">
                {overview.data.coverage_quality === "insufficient_data"
                  ? "No successful observations exist in this range for the current Project environment. Run a regular authorized rank check to collect evidence."
                  : overview.data.coverage_quality === "complete"
                    ? `Complete persisted snapshots at effective Top ${overview.data.top_n}.`
                    : `Partial coverage: ${overview.data.partial_or_unobserved_keywords} keyword snapshots include missing or incomplete evidence.`}{" "}
                As of {formatDate(overview.data.latest_successful_check_at)}.
                Missing evidence is never treated as a ranking loss.
              </Alert>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard
                  label="Keyword cohort"
                  value={overview.data.keyword_cohort}
                  detail={`${overview.data.qualifying_keywords} with a successful observation`}
                />
                <StatCard
                  label={`Observed Top-${overview.data.top_n}`}
                  value={overview.data.sites[0]?.top_n ?? 0}
                  detail={overview.data.primary_site.name}
                />
                <StatCard
                  label="Partial / unobserved"
                  value={overview.data.partial_or_unobserved_keywords}
                  detail="Excluded where direct evidence is required"
                />
                <StatCard
                  label="Checked depth"
                  value={`Top ${overview.data.effective_depth}`}
                  detail={`${overview.data.device} · current Project environment`}
                />
              </div>

              <Card className="mt-6">
                <h2 className="text-xl font-semibold">Site coverage</h2>
                <Table className="mt-4">
                  <thead>
                    <tr>
                      <th>Site</th>
                      <th>Top 3</th>
                      <th>Top {overview.data.top_n}</th>
                      <th>Comparable denominator</th>
                      <th>Observed coverage</th>
                      <th>Not observed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.data.sites.map((site) => (
                      <tr key={site.tracked_site_id}>
                        <td>{site.name}</td>
                        <td>{site.top_3}</td>
                        <td>{site.top_n}</td>
                        <td>{site.comparable_keywords}</td>
                        <td>{site.observed_top_n_coverage_pct}%</td>
                        <td>{site.not_observed + site.ambiguous_match}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card>

              {!!overview.data.comparisons.length && (
                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                  {overview.data.comparisons.map((comparison) => (
                    <Card key={comparison.opponent_site_id}>
                      <h2 className="text-lg font-semibold">
                        vs {comparison.opponent_name}
                      </h2>
                      <p className="mt-1 text-sm text-secondary">
                        {comparison.both_numeric_ranked} paired numeric keywords
                        · {comparison.excluded_unpaired} excluded
                      </p>
                      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div>
                          <strong>{comparison.primary_ahead}</strong>
                          <span className="block text-xs text-secondary">
                            Primary ahead
                          </span>
                        </div>
                        <div>
                          <strong>{comparison.tied}</strong>
                          <span className="block text-xs text-secondary">
                            Tied
                          </span>
                        </div>
                        <div>
                          <strong>{comparison.competitor_ahead}</strong>
                          <span className="block text-xs text-secondary">
                            Competitor ahead
                          </span>
                        </div>
                        <div>
                          <strong>{comparison.opportunities}</strong>
                          <span className="block text-xs text-secondary">
                            Opportunities
                          </span>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </>
          )}

          {trends.data && <CoverageChart data={trends.data} />}

          {keywords.data && (
            <Card className="mt-6">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold">Keyword comparison</h2>
                  <p className="mt-1 text-sm text-secondary">
                    {keywords.data.total} same-check keyword snapshots. Position
                    gap is competitor minus primary; positive means your site is
                    ahead.
                  </p>
                </div>
                <label>
                  Rows
                  <Select
                    value={filters.limit}
                    onChange={(event) =>
                      updateUrl({
                        limit:
                          event.target.value === "50"
                            ? null
                            : event.target.value,
                      })
                    }
                  >
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                  </Select>
                </label>
              </div>
              {!keywords.data.items.length ? (
                <EmptyState title="No matching keyword observations">
                  Adjust the current filters or wait for an authorized regular
                  rank check.
                </EmptyState>
              ) : (
                <Table className="mt-4">
                  <thead>
                    <tr>
                      <th>Keyword</th>
                      <th>{selection.data.primary_site.name}</th>
                      <th>{opponent?.name ?? "Competitor"}</th>
                      <th>Gap</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {keywords.data.items.map((row) => {
                      const mine = row.sites.find(
                        (site) =>
                          site.tracked_site_id ===
                          selection.data.primary_site?.tracked_site_id,
                      );
                      const theirs = row.sites.find(
                        (site) => site.tracked_site_id === selectedOpponent,
                      );
                      const open = expandedKeywordId === row.keyword_id;
                      return (
                        <Fragment key={row.keyword_id}>
                          <tr>
                            <td>
                              <button
                                type="button"
                                className="ui-text-link text-left"
                                aria-expanded={open}
                                onClick={() =>
                                  setExpandedKeywordId(
                                    open ? null : row.keyword_id,
                                  )
                                }
                              >
                                {row.keyword}
                              </button>
                            </td>
                            <td>
                              {mine ? statusLabel(mine) : "No observation"}
                            </td>
                            <td>
                              {theirs
                                ? statusLabel(theirs)
                                : "No competitor selected"}
                            </td>
                            <td>
                              {row.position_gap === null
                                ? "—"
                                : row.position_gap > 0
                                  ? `+${row.position_gap}`
                                  : row.position_gap}
                            </td>
                            <td>
                              <Badge
                                tone={
                                  row.opportunity
                                    ? "warning"
                                    : row.comparison_state === "my_site_ahead"
                                      ? "success"
                                      : "neutral"
                                }
                              >
                                {row.opportunity
                                  ? "Opportunity"
                                  : row.comparison_state.replaceAll("_", " ")}
                              </Badge>
                            </td>
                          </tr>
                          {open && (
                            <tr>
                              <td colSpan={5}>
                                {detail.isPending && (
                                  <Skeleton
                                    label="Loading observation…"
                                    rows={2}
                                  />
                                )}
                                {detail.isError && (
                                  <Alert className="text-danger">
                                    {message(detail.error)}
                                  </Alert>
                                )}
                                {detail.data && (
                                  <div className="grid gap-4 p-2">
                                    <p className="text-sm text-secondary">
                                      {formatDate(detail.data.checked_at)} ·{" "}
                                      {detail.data.device} ·{" "}
                                      {detail.data.country_code}/
                                      {detail.data.language_code} · checked Top{" "}
                                      {detail.data.checked_depth} ·{" "}
                                      {detail.data.snapshot_complete
                                        ? "complete snapshot"
                                        : "partial snapshot"}
                                    </p>
                                    <div className="grid gap-3 md:grid-cols-2">
                                      {detail.data.sites.map((site) => (
                                        <div key={site.tracked_site_id}>
                                          <strong>
                                            {site.name}: {statusLabel(site)}
                                          </strong>
                                          {site.matched_results.map(
                                            (result) => (
                                              <p
                                                key={`${result.position}-${result.url}`}
                                                className="mt-1 text-sm"
                                              >
                                                <a
                                                  className="ui-text-link break-all"
                                                  href={result.url}
                                                  target="_blank"
                                                  rel="noreferrer"
                                                >
                                                  #{result.position} ·{" "}
                                                  {result.hostname}
                                                </a>
                                                {result.title
                                                  ? ` — ${result.title}`
                                                  : ""}
                                              </p>
                                            ),
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                    <Link
                                      className="ui-text-link text-sm"
                                      href={`/app/projects/${projectId}/rankings?q=${encodeURIComponent(row.keyword)}`}
                                    >
                                      Open ranking history →
                                    </Link>
                                  </div>
                                )}
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
                  </tbody>
                </Table>
              )}
              <div className="mt-4 flex flex-wrap justify-between gap-3">
                <Button
                  disabled={!filters.cursor}
                  onClick={() => updateUrl({ cursor: null })}
                >
                  First page
                </Button>
                <Button
                  disabled={!keywords.data.has_more}
                  onClick={() =>
                    updateUrl({ cursor: keywords.data.next_cursor })
                  }
                >
                  Next page
                </Button>
              </div>
            </Card>
          )}
        </>
      )}
    </main>
  );
}
