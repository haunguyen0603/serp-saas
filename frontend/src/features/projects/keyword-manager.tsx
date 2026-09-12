"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import {
  checkKeyword,
  checkProject,
  getLatestRankings,
  getRankCheck,
  listRankChecks,
  rankingKeys,
} from "@/features/rankings/api";
import { RankCheckDetail } from "@/features/rankings/rank-check-detail";
import { RankCheckHistory } from "@/features/rankings/rank-check-history";
import { BatchPanel, SchedulePanel } from "@/features/rankings/batch-panel";
import { batchKey } from "@/features/rankings/batches";
import type { RankCheck } from "@/features/rankings/types";
import { ApiError } from "@/lib/api/client";
import {
  bulkCreateKeywords,
  createKeyword,
  deleteKeyword,
  listKeywords,
  projectKeys,
  updateKeyword,
} from "./api";
import { useProtectedAuth } from "./protected";
import type {
  Keyword,
  KeywordBulkResult,
  KeywordUpdate,
  Project,
} from "./types";

const field =
  "mt-2 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2";
const message = (error: unknown, fallback: string) =>
  error instanceof ApiError ? error.message : fallback;

export function KeywordManager({ project }: { project: Project }) {
  const auth = useProtectedAuth();
  const queryClient = useQueryClient();
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState<"true" | "false" | "all">("true");
  const [panel, setPanel] = useState<"single" | "bulk" | null>(null);
  const [editing, setEditing] = useState<Keyword | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyKeyword, setHistoryKeyword] = useState<Keyword | null>(null);
  const [detailCheck, setDetailCheck] = useState<RankCheck | null>(null);
  const filters = { search, active, limit: 50 } as const;
  const keywords = useInfiniteQuery({
    queryKey: projectKeys.keywordList(project.id, filters),
    queryFn: ({ pageParam }) =>
      listKeywords(auth.request, project.id, { ...filters, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: auth.isAuthenticated,
  });
  const latest = useQuery({
    queryKey: rankingKeys.latest(project.id),
    queryFn: () => getLatestRankings(auth.request, project.id),
    enabled: auth.isAuthenticated,
  });
  const history = useQuery({
    queryKey: rankingKeys.history(project.id, historyKeyword?.id ?? ""),
    queryFn: () =>
      listRankChecks(auth.request, project.id, historyKeyword?.id ?? "", {
        limit: 50,
      }),
    enabled: auth.isAuthenticated && historyKeyword !== null,
  });
  const detail = useQuery({
    queryKey: rankingKeys.detail(
      project.id,
      historyKeyword?.id ?? "",
      detailCheck?.id ?? "",
    ),
    queryFn: () =>
      getRankCheck(
        auth.request,
        project.id,
        historyKeyword?.id ?? "",
        detailCheck?.id ?? "",
      ),
    enabled:
      auth.isAuthenticated && historyKeyword !== null && detailCheck !== null,
  });
  const invalidate = async () => {
    await queryClient.invalidateQueries({
      queryKey: projectKeys.keywords(project.id),
    });
    await queryClient.invalidateQueries({
      queryKey: projectKeys.detail(project.id),
    });
  };
  const single = useMutation({
    mutationFn: (keyword: string) =>
      createKeyword(auth.request, project.id, { keyword }),
    onSuccess: async () => {
      setPanel(null);
      setNotice("Keyword added.");
      await invalidate();
    },
  });
  const bulk = useMutation({
    mutationFn: (lines: string[]) =>
      bulkCreateKeywords(auth.request, project.id, { keywords: lines }),
    onSuccess: async (result: KeywordBulkResult) => {
      setNotice(
        `${result.created} keywords added. ${result.skipped_duplicates} duplicates and ${result.skipped_empty} empty lines skipped.`,
      );
      await invalidate();
    },
  });
  const update = useMutation({
    mutationFn: ({ id, input }: { id: string; input: KeywordUpdate }) =>
      updateKeyword(auth.request, project.id, id, input),
    onSuccess: async () => {
      setEditing(null);
      await invalidate();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteKeyword(auth.request, project.id, id),
    onSuccess: invalidate,
    onError: (failure) =>
      setError(message(failure, "Keyword could not be deleted.")),
  });
  const projectCheck = useMutation({
    mutationFn: () => checkProject(auth.request, project.id),
    onSuccess: async (result) => {
      setNotice("Ranking checks queued.");
      setSelectedBatch(result.batch_id);
      await queryClient.invalidateQueries({ queryKey: batchKey(project.id) });
    },
    onError: (failure) =>
      setError(message(failure, "Project rankings could not be checked.")),
  });
  const keywordCheck = useMutation({
    mutationFn: (keywordId: string) =>
      checkKeyword(auth.request, project.id, keywordId),
    onSuccess: async (result) => {
      setNotice("Keyword check queued.");
      setSelectedBatch(result.batch_id);
      await queryClient.invalidateQueries({ queryKey: batchKey(project.id) });
    },
    onError: (failure) =>
      setError(message(failure, "Keyword ranking could not be checked.")),
  });
  const items = keywords.data?.pages.flatMap((page) => page.items) ?? [];
  const latestByKeyword = new Map(
    latest.data?.items.map((item) => [item.keyword_id, item.latest_check]) ??
      [],
  );
  function submitSingle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    single.mutate(String(new FormData(form).get("keyword") ?? ""), {
      onError: (failure) =>
        setError(message(failure, "Keyword could not be added.")),
    });
  }
  function submitBulk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const lines = String(
      new FormData(event.currentTarget).get("keywords") ?? "",
    ).split(/\r?\n/);
    if (lines.length > 1000) {
      setError("A bulk request may contain at most 1000 keywords.");
      return;
    }
    bulk.mutate(lines, {
      onError: (failure) =>
        setError(message(failure, "Keywords could not be added.")),
    });
  }
  return (
    <section id="keywords">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold">
          Keywords{" "}
          <span className="text-base text-slate-400">
            ({project.keyword_count})
          </span>
        </h2>
        <div className="flex flex-wrap gap-3">
          <button
            className="rounded-lg bg-teal-400 px-4 py-2 font-semibold text-slate-950"
            disabled={project.status !== "active" || projectCheck.isPending}
            onClick={() => {
              setError(null);
              projectCheck.mutate();
            }}
          >
            {projectCheck.isPending ? "Queueing…" : "Check Rankings"}
          </button>
          <button
            className="rounded-lg bg-teal-400 px-4 py-2 font-semibold text-slate-950"
            onClick={() => setPanel(panel === "single" ? null : "single")}
          >
            Add Keyword
          </button>
          <button
            className="rounded-lg border border-slate-600 px-4 py-2"
            onClick={() => setPanel(panel === "bulk" ? null : "bulk")}
          >
            Bulk Add
          </button>
        </div>
      </div>
      <BatchPanel
        projectId={project.id}
        selectedBatch={selectedBatch}
        onSelect={setSelectedBatch}
      />
      <SchedulePanel
        projectId={project.id}
        archived={project.status !== "active"}
      />
      {panel === "single" && (
        <form
          aria-label="Add keyword"
          onSubmit={submitSingle}
          className="mt-5 rounded-xl border border-slate-700 p-5"
        >
          <label>
            Keyword
            <input className={field} name="keyword" required maxLength={512} />
          </label>
          <button
            disabled={single.isPending}
            className="mt-4 rounded-lg bg-teal-400 px-5 py-2 font-semibold text-slate-950"
          >
            {single.isPending ? "Adding…" : "Add keyword"}
          </button>
        </form>
      )}
      {panel === "bulk" && (
        <form
          aria-label="Bulk add keywords"
          onSubmit={submitBulk}
          className="mt-5 rounded-xl border border-slate-700 p-5"
        >
          <label>
            Keywords, one per line
            <textarea
              className={`${field} min-h-40`}
              name="keywords"
              required
            />
          </label>
          <p className="mt-2 text-sm text-slate-400">
            Maximum 1000 lines. Empty and duplicate lines are cleaned.
          </p>
          <button
            disabled={bulk.isPending}
            className="mt-4 rounded-lg bg-teal-400 px-5 py-2 font-semibold text-slate-950"
          >
            {bulk.isPending ? "Adding…" : "Add keywords"}
          </button>
        </form>
      )}
      {error && (
        <p role="alert" className="mt-4 text-red-300">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="mt-4 rounded-lg bg-teal-950/60 p-4">
          {notice}
        </p>
      )}
      <div className="my-6 grid gap-3 sm:grid-cols-2">
        <label>
          Search keywords
          <input
            className={field}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label>
          Keyword state
          <select
            className={field}
            value={active}
            onChange={(event) => setActive(event.target.value as typeof active)}
          >
            <option value="true">Active</option>
            <option value="false">Paused</option>
            <option value="all">All</option>
          </select>
        </label>
      </div>
      {keywords.isPending && <p role="status">Loading keywords…</p>}
      {keywords.isError && <p role="alert">Keywords could not be loaded.</p>}
      {editing && (
        <form
          aria-label="Edit keyword"
          className="mb-5 rounded-xl border border-teal-500/50 p-5"
          onSubmit={(event) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            update.mutate({
              id: editing.id,
              input: {
                keyword: String(values.get("keyword") ?? ""),
                active: values.get("active") === "on",
              },
            });
          }}
        >
          <label>
            Edit keyword
            <input
              className={field}
              name="keyword"
              defaultValue={editing.keyword}
              required
            />
          </label>
          <label className="mt-4 flex gap-3">
            <input
              name="active"
              type="checkbox"
              defaultChecked={editing.active}
            />
            Active
          </label>
          <button className="mt-4 rounded-lg bg-teal-400 px-4 py-2 text-slate-950">
            Save Keyword
          </button>
          <button
            type="button"
            className="ml-3 px-4 py-2"
            onClick={() => setEditing(null)}
          >
            Cancel
          </button>
        </form>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="p-3">Keyword</th>
              <th className="p-3">Status</th>
              <th className="p-3">Last checked</th>
              <th className="p-3">Tracked rankings</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-slate-800">
                <td className="p-3">{item.keyword}</td>
                <td className="p-3">{item.active ? "Active" : "Paused"}</td>
                <td className="p-3">
                  {(() => {
                    const check = latestByKeyword.get(item.id);
                    if (!check) return "Never checked";
                    return new Date(check.requested_at).toLocaleString();
                  })()}
                </td>
                <td className="p-3">
                  {(() => {
                    const check = latestByKeyword.get(item.id);
                    if (!check) return "—";
                    if (check.status === "failed") return "Check failed";
                    if (
                      check.status === "pending" ||
                      check.status === "running"
                    )
                      return "Running";
                    if (!check.rankings.length)
                      return `Not found in Top ${check.result_limit}`;
                    return check.rankings
                      .map(
                        (ranking) =>
                          `${ranking.tracked_site_name} #${ranking.position}`,
                      )
                      .join(", ");
                  })()}
                </td>
                <td className="p-3">
                  <button
                    className="mr-3 text-teal-300"
                    disabled={
                      !item.active ||
                      (keywordCheck.isPending &&
                        keywordCheck.variables === item.id)
                    }
                    onClick={() => {
                      setError(null);
                      keywordCheck.mutate(item.id);
                    }}
                  >
                    {keywordCheck.isPending &&
                    keywordCheck.variables === item.id
                      ? "Queueing…"
                      : "Check now"}
                  </button>
                  <button
                    className="mr-3 text-teal-300"
                    onClick={() => {
                      setHistoryKeyword(item);
                      setDetailCheck(null);
                    }}
                  >
                    History
                  </button>
                  <button
                    className="mr-3 text-teal-300"
                    onClick={() => setEditing(item)}
                  >
                    Edit
                  </button>
                  <button
                    className="text-red-300"
                    onClick={() => remove.mutate(item.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {keywords.hasNextPage && (
        <button
          className="mt-5 rounded-lg border border-slate-600 px-4 py-2"
          onClick={() => void keywords.fetchNextPage()}
        >
          Load more keywords
        </button>
      )}
      {historyKeyword && (
        <>
          {history.isPending && <p role="status">Loading ranking history…</p>}
          {history.isError && (
            <p role="alert">Ranking history could not be loaded.</p>
          )}
          {history.data && (
            <RankCheckHistory
              keyword={historyKeyword.keyword}
              checks={history.data.items}
              onOpen={setDetailCheck}
            />
          )}
          {detail.isPending && detailCheck && (
            <p role="status">Loading Rank Check detail…</p>
          )}
          {detail.isError && (
            <p role="alert">Rank Check detail could not be loaded.</p>
          )}
          {detail.data && <RankCheckDetail check={detail.data} />}
        </>
      )}
    </section>
  );
}
