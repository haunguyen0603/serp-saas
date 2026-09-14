import { Alert, Button, Select, Skeleton, Table } from "@/design-system/ui";
import type { RankCheck } from "./types";

export function RankCheckHistory({
  keyword,
  keywordId,
  keywordOptions,
  checks,
  loading,
  error,
  page,
  hasNextPage,
  onKeywordChange,
  onPreviousPage,
  onNextPage,
  onOpen,
}: {
  keyword: string | null;
  keywordId: string | null;
  keywordOptions: { id: string; keyword: string }[];
  checks: RankCheck[];
  loading: boolean;
  error: boolean;
  page: number;
  hasNextPage: boolean;
  onKeywordChange: (keywordId: string) => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
  onOpen: (check: RankCheck) => void;
}) {
  return (
    <section
      aria-label="Ranking history"
      className="mt-8 rounded-xl border border-border p-5"
    >
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h3 className="text-xl font-semibold">
          Ranking history{keyword ? ` · ${keyword}` : ""}
        </h3>
        {keywordOptions.length > 1 && keywordId && (
          <label className="min-w-52 text-sm">
            Keyword
            <Select
              aria-label="Ranking history keyword"
              value={keywordId}
              onChange={(event) => onKeywordChange(event.target.value)}
            >
              {keywordOptions.map((option) => (
                <option value={option.id} key={option.id}>
                  {option.keyword}
                </option>
              ))}
            </Select>
          </label>
        )}
      </div>
      {loading && <Skeleton label="Loading ranking history…" />}
      {error && (
        <Alert className="mt-4">Ranking history could not be loaded.</Alert>
      )}
      {!loading && !error && !keyword && (
        <p className="mt-4 text-secondary">
          Add a keyword to start building ranking history.
        </p>
      )}
      {!loading && !error && keyword && checks.length === 0 && (
        <p className="mt-4 text-secondary">No Rank Checks yet.</p>
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
                              `${ranking.tracked_site_name} #${ranking.position}`,
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
    </section>
  );
}
