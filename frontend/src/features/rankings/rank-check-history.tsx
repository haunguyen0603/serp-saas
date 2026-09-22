import {
  Button,
  Card,
  ErrorState,
  Select,
  Skeleton,
  Table,
} from "@/design-system/ui";
import { AnalyticsRangeSelector } from "@/features/analytics/range-selector";
import { RankingChart } from "@/features/analytics/ranking-chart";
import type {
  AnalyticsRange,
  KeywordRankingHistory,
} from "@/features/analytics/types";
import type { RankCheck } from "./types";

export function RankCheckHistory({
  id,
  keyword,
  checks,
  loading,
  error,
  page,
  hasNextPage,
  onPreviousPage,
  onNextPage,
  onOpen,
  onRetry,
  chart,
  chartLoading = false,
  chartError = false,
  chartRange = "30d",
  trackedSites = [],
  trackedSiteId = "",
  onChartRangeChange,
  onTrackedSiteChange,
  onChartRetry,
}: {
  id: string;
  keyword: string;
  checks: RankCheck[];
  loading: boolean;
  error: boolean;
  page: number;
  hasNextPage: boolean;
  onPreviousPage: () => void;
  onNextPage: () => void;
  onOpen: (check: RankCheck) => void;
  onRetry: () => void;
  chart?: KeywordRankingHistory;
  chartLoading?: boolean;
  chartError?: boolean;
  chartRange?: AnalyticsRange;
  trackedSites?: { id: string; name: string }[];
  trackedSiteId?: string;
  onChartRangeChange?: (value: AnalyticsRange) => void;
  onTrackedSiteChange?: (value: string) => void;
  onChartRetry?: () => void;
}) {
  return (
    <Card
      id={id}
      aria-label="Ranking history"
      className="keyword-history-panel"
    >
      <h3 className="text-xl font-semibold">Ranking history · {keyword}</h3>
      {!!trackedSites.length && onChartRangeChange && onTrackedSiteChange && (
        <div className="mt-4">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <label>
              Tracked site
              <Select
                value={trackedSiteId}
                onChange={(event) => onTrackedSiteChange(event.target.value)}
              >
                {trackedSites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.name}
                  </option>
                ))}
              </Select>
            </label>
            <AnalyticsRangeSelector
              value={chartRange}
              onChange={onChartRangeChange}
              label="Ranking history range"
            />
          </div>
          {chartLoading && <Skeleton label="Loading ranking chart…" />}
          {chartError && (
            <ErrorState onRetry={onChartRetry ?? (() => {})}>
              Ranking chart could not be loaded.
            </ErrorState>
          )}
          {chart && <RankingChart history={chart} />}
        </div>
      )}
      {loading && (
        <div className="mt-4">
          <Skeleton label="Loading ranking history…" />
        </div>
      )}
      {error && (
        <div className="mt-4">
          <ErrorState onRetry={onRetry}>
            Ranking history could not be loaded.
          </ErrorState>
        </div>
      )}
      {!loading && !error && checks.length === 0 && (
        <p className="mt-4 text-secondary">No ranking history yet.</p>
      )}
      {!loading && !error && checks.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <Table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="p-2">Check time</th>
                <th className="p-2">Environment snapshot</th>
                <th className="p-2">Depth</th>
                <th className="p-2">Matched Sites</th>
                <th className="p-2">Status</th>
                <th className="p-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((check) => (
                <tr key={check.id} className="border-b border-border">
                  <td className="p-2">
                    {new Date(check.requested_at).toLocaleString()}
                  </td>
                  <td className="p-2">
                    {check.country_code_snapshot} ·{" "}
                    {check.language_code_snapshot}
                    {" · "}
                    {check.device_snapshot}
                    {check.location_snapshot
                      ? ` · ${check.location_snapshot}`
                      : ""}
                  </td>
                  <td className="p-2">Top {check.result_limit}</td>
                  <td className="p-2">
                    {check.rankings.length ? (
                      <div className="flex flex-wrap gap-2">
                        {check.rankings.map((ranking) => (
                          <a
                            key={`${ranking.tracked_site_id}:${ranking.matched_domain}:${ranking.position}`}
                            className="ui-text-link"
                            href={`https://www.google.com/search?${new URLSearchParams({ q: check.query_snapshot })}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={`Search Google for “${check.query_snapshot}” (opens in a new tab)`}
                          >
                            {ranking.matched_domain} #{ranking.position}
                          </a>
                        ))}
                      </div>
                    ) : check.status === "succeeded" ? (
                      `Not found in Top ${check.result_limit}`
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="p-2 capitalize">{check.status}</td>
                  <td className="p-2">
                    <Button onClick={() => onOpen(check)}>View results</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
      {!loading && !error && (page > 0 || hasNextPage) && (
        <nav
          className="mt-4 flex items-center justify-end gap-3"
          aria-label="Ranking history pagination"
        >
          <Button disabled={page === 0} onClick={onPreviousPage}>
            Previous page
          </Button>
          <span className="text-sm text-secondary" aria-live="polite">
            Page {page + 1}
          </span>
          <Button disabled={!hasNextPage} onClick={onNextPage}>
            Next page
          </Button>
        </nav>
      )}
    </Card>
  );
}
