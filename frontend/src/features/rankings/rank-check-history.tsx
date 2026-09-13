import { Button, Table } from "@/design-system/ui";
import type { RankCheck } from "./types";

export function RankCheckHistory({
  keyword,
  checks,
  onOpen,
}: {
  keyword: string;
  checks: RankCheck[];
  onOpen: (check: RankCheck) => void;
}) {
  return (
    <section
      aria-label="Ranking history"
      className="mt-8 rounded-xl border border-border p-5"
    >
      <h3 className="text-xl font-semibold">Ranking history · {keyword}</h3>
      {checks.length === 0 ? (
        <p className="mt-4 text-secondary">No Rank Checks yet.</p>
      ) : (
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
    </section>
  );
}
