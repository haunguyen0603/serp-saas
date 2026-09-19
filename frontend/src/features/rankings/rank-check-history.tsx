import { Button, Card, ErrorState, Skeleton, Table } from "@/design-system/ui";
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
}) {
  return (
    <Card
      id={id}
      aria-label="Ranking history"
      className="keyword-history-panel"
    >
      <h3 className="text-xl font-semibold">Ranking history · {keyword}</h3>
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
                    {check.rankings.length
                      ? check.rankings
                          .map(
                            (ranking) =>
                              `${ranking.matched_domain} #${ranking.position}`,
                          )
                          .join(", ")
                      : check.status === "succeeded"
                        ? `Not found in Top ${check.result_limit}`
                        : "—"}
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
