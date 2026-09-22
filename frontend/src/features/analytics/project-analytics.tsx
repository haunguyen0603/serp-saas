"use client";

import {
  Card,
  EmptyState,
  ErrorState,
  Skeleton,
  StatCard,
  Table,
} from "@/design-system/ui";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { Project } from "@/features/projects/types";
import { useAuth } from "@/features/auth/auth-provider";
import { getProjectAnalytics, getProjectMovers, projectAnalytics } from "./api";
import { AnalyticsRangeSelector } from "./range-selector";
import type { AnalyticsRange, RankingMover } from "./types";

const bucketLabel = (key: string, depth: number) => {
  const labels: Record<string, string> = {
    top_3: "Top 3",
    positions_4_10: "4–10",
    positions_11_20: "11–20",
    positions_21_50: "21–50",
    positions_51_100: "51–100",
    not_found_in_depth: `Not found in Top ${depth}`,
  };
  return labels[key] ?? key;
};

function Movers({ title, items }: { title: string; items: RankingMover[] }) {
  return (
    <Card className="analytics-movers">
      <h3 className="text-xl font-semibold">{title}</h3>
      {!items.length ? (
        <p className="mt-4 text-secondary">
          No numeric movement in this range.
        </p>
      ) : (
        <Table className="mt-4 w-full" aria-label={title}>
          <thead>
            <tr>
              <th>Keyword</th>
              <th>Site</th>
              <th>Previous</th>
              <th>Current</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={`${item.keyword_id}:${item.tracked_site_id}`}>
                <td>
                  <a
                    className="ui-text-link"
                    href={`#keyword-${item.keyword_id}`}
                  >
                    {item.keyword}
                  </a>
                </td>
                <td>{item.tracked_site_name}</td>
                <td>#{item.previous_position}</td>
                <td>#{item.current_position}</td>
                <td
                  className={item.change > 0 ? "text-success" : "text-danger"}
                >
                  {item.change > 0
                    ? `Improved ${item.change}`
                    : `Declined ${Math.abs(item.change)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

export function ProjectAnalytics({ project }: { project: Project }) {
  const auth = useAuth();
  const [range, setRange] = useState<AnalyticsRange>("30d");
  const summary = useQuery({
    queryKey: projectAnalytics.summary(project.id, project.device, range),
    queryFn: () =>
      getProjectAnalytics(auth.request, project.id, project.device, range),
  });
  const movers = useQuery({
    queryKey: projectAnalytics.movers(project.id, project.device, range),
    queryFn: () =>
      getProjectMovers(auth.request, project.id, project.device, range),
  });
  const value = summary.data;
  return (
    <section id="analytics" aria-labelledby="analytics-title" className="mb-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="analytics-title" className="text-2xl font-semibold">
            Ranking analytics
          </h2>
          <p className="mt-1 text-secondary">
            Persisted {project.device} observations. Viewing analytics never
            runs a rank check.
          </p>
        </div>
        <AnalyticsRangeSelector value={range} onChange={setRange} />
      </div>
      {summary.isPending && <Skeleton label="Loading ranking analytics…" />}
      {summary.isError && (
        <ErrorState onRetry={() => void summary.refetch()}>
          Ranking analytics could not be loaded.
        </ErrorState>
      )}
      {value && value.observed_keywords === 0 && (
        <EmptyState title="No ranking data yet">
          Run a rank check to start building ranking history.
        </EmptyState>
      )}
      {value && value.observed_keywords > 0 && (
        <>
          <div className="analytics-kpis">
            <StatCard label="Tracked Keywords" value={value.total_keywords} />
            <StatCard label="Top 3" value={value.top_3} />
            <StatCard label="Top 10" value={value.top_10} />
            <StatCard
              label="Improved"
              value={value.improved}
              detail="Numeric movement"
            />
            <StatCard
              label="Declined"
              value={value.declined}
              detail="Numeric movement"
            />
            <StatCard
              label={`Not found in Top ${value.distribution.effective_depth}`}
              value={value.not_found_in_depth}
            />
          </div>
          <Card className="mt-6">
            <h3 className="text-xl font-semibold">Ranking distribution</h3>
            <div
              className="analytics-distribution"
              role="list"
              aria-label="Ranking distribution"
            >
              {Object.entries(value.distribution.buckets).map(
                ([key, count]) => {
                  const maximum = Math.max(
                    ...Object.values(value.distribution.buckets),
                    1,
                  );
                  return (
                    <div
                      className="analytics-distribution-row"
                      role="listitem"
                      key={key}
                    >
                      <span>
                        {bucketLabel(key, value.distribution.effective_depth)}
                      </span>
                      <div
                        className="analytics-distribution-track"
                        aria-hidden="true"
                      >
                        <span
                          style={{ width: `${(count / maximum) * 100}%` }}
                        />
                      </div>
                      <strong>{count}</strong>
                    </div>
                  );
                },
              )}
            </div>
          </Card>
        </>
      )}
      {movers.isPending && value?.observed_keywords ? (
        <Skeleton label="Loading ranking movers…" />
      ) : null}
      {movers.isError && (
        <ErrorState onRetry={() => void movers.refetch()}>
          Ranking movers could not be loaded.
        </ErrorState>
      )}
      {movers.data && value?.observed_keywords ? (
        <div className="analytics-movers-grid">
          <Movers title="Biggest Winners" items={movers.data.winners} />
          <Movers title="Biggest Losers" items={movers.data.losers} />
        </div>
      ) : null}
    </section>
  );
}
