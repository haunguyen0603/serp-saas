import type { RankCheckDetail as RankCheckDetailData } from "./types";

export function RankCheckDetail({ check }: { check: RankCheckDetailData }) {
  const matched = new Map(
    check.rankings.map((ranking) => [
      `${ranking.position}:${ranking.result_url}`,
      ranking.tracked_site_name,
    ]),
  );
  return (
    <section
      aria-label="Rank Check detail"
      className="mt-6 rounded-xl border border-slate-700 p-5"
    >
      <h3 className="text-xl font-semibold">Rank Check detail</h3>
      <p className="mt-2 text-sm text-slate-400">
        {/* Data source: {providerName(check.provider)} ·{" "} */}
        {check.search_engine_snapshot} · {check.country_code_snapshot} ·{" "}
        {check.language_code_snapshot} · {check.device_snapshot}
        {check.location_snapshot ? ` · ${check.location_snapshot}` : ""} · Top{" "}
        {check.result_limit}
      </p>
      {check.provider_attempts.length > 1 && (
        <p className="mt-2 text-sm text-slate-400">
          {check.provider_attempts.length} provider attempts
        </p>
      )}
      <h4 className="mt-6 font-semibold">
        Top {check.result_limit} Organic Results
      </h4>
      {check.organic_results.length === 0 ? (
        <p className="mt-3 text-slate-400">No organic results were returned.</p>
      ) : (
        <ol className="mt-3 space-y-3">
          {check.organic_results.map((result) => {
            const site = matched.get(`${result.position}:${result.url}`);
            return (
              <li
                key={`${result.position}:${result.url}`}
                className="rounded-lg bg-slate-900 p-3"
              >
                <span className="font-semibold">#{result.position}</span>{" "}
                <span>{result.hostname}</span>
                {site && (
                  <span className="ml-3 rounded bg-teal-900 px-2 py-1 text-xs text-teal-200">
                    Tracked · {site}
                  </span>
                )}
                <p className="mt-1 text-sm">
                  {result.title || "Untitled result"}
                </p>
                <a
                  className="break-all text-sm text-teal-300 underline"
                  href={result.url}
                >
                  {result.url}
                </a>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
