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
      className="mt-8 rounded-xl border border-slate-700 p-5"
    >
      <h3 className="text-xl font-semibold">Ranking history · {keyword}</h3>
      {checks.length === 0 ? (
        <p className="mt-4 text-slate-400">No Rank Checks yet.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-700">
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
                <tr key={check.id} className="border-b border-slate-800">
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
                    <button
                      className="text-teal-300 underline"
                      onClick={() => onOpen(check)}
                    >
                      View results
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
