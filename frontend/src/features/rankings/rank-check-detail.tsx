import { Card, Badge, StatusBadge } from "@/design-system/ui";
import type { RankCheckDetail as RankCheckDetailData } from "./types";

export function RankCheckDetail({ check }: { check: RankCheckDetailData }) {
  const matched = new Map(
    check.rankings.map((ranking) => [
      `${ranking.position}:${ranking.result_url}`,
      ranking.tracked_site_name,
    ]),
  );
  return (
    <Card
      aria-label="Rank Check detail"
      className="mt-6 rounded-xl border border-border p-5"
    >
      <h3 className="text-xl font-semibold">Rank Check detail</h3>
      <p className="mt-2 text-sm text-secondary">
        {/* Data source: {providerName(check.provider)} ·{" "} */}
        {check.search_engine_snapshot} · {check.country_code_snapshot} ·{" "}
        {check.language_code_snapshot} · {check.device_snapshot}
        {check.location_snapshot ? ` · ${check.location_snapshot}` : ""} · Top{" "}
        {check.result_limit}
      </p>
      <p className="mt-3">
        <StatusBadge status={check.status} /> ·{" "}
        {new Date(check.requested_at).toLocaleString()}
        {check.completed_at &&
          ` · Completed ${new Date(check.completed_at).toLocaleString()}`}
      </p>
      <h4 className="mt-6 font-semibold">
        Top {check.result_limit} Organic Results
      </h4>
      {check.organic_results.length === 0 ? (
        <p className="mt-3 text-secondary">No organic results were returned.</p>
      ) : (
        <ol className="mt-3 space-y-3">
          {check.organic_results.map((result) => {
            const site = matched.get(`${result.position}:${result.url}`);
            return (
              <li
                key={`${result.position}:${result.url}`}
                className="rounded-lg bg-surface p-3"
              >
                <span className="font-semibold">#{result.position}</span>{" "}
                <span>{result.hostname}</span>
                {site && <Badge tone="success">Tracked · {site}</Badge>}
                <p className="mt-1 text-sm">
                  {result.title || "Untitled result"}
                </p>
                <a
                  className="break-all text-sm text-brand underline"
                  href={result.url}
                >
                  {result.url}
                </a>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
