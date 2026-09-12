"use client";
import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import {
  deleteTrackedSite,
  listTrackedSites,
  trackedSiteKeys,
  updateTrackedSite,
} from "./api";
import type { TrackedSiteStatus } from "./types";
const field =
  "mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3";
export function TrackedSiteList() {
  const auth = useProtectedAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<TrackedSiteStatus | "all">("active");
  const filters = { search, status, limit: 20 } as const;
  const sites = useInfiniteQuery({
    queryKey: trackedSiteKeys.list(filters),
    queryFn: ({ pageParam }) =>
      listTrackedSites(auth.request, { ...filters, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: auth.isAuthenticated,
  });
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: trackedSiteKeys.all });
  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TrackedSiteStatus }) =>
      updateTrackedSite(auth.request, id, { status }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteTrackedSite(auth.request, id),
    onSuccess: refresh,
  });
  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  const items = sites.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <main>
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-4xl font-semibold">Tracked Sites</h1>
        <Link
          href="/app/tracked-sites/new"
          className="rounded-lg bg-teal-400 px-5 py-3 font-semibold text-slate-950"
        >
          Add Tracked Site
        </Link>
      </div>
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <label>
          Search tracked sites
          <input
            className={field}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label>
          Site status
          <select
            className={field}
            value={status}
            onChange={(event) => setStatus(event.target.value as typeof status)}
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </select>
        </label>
      </div>
      {sites.isPending && <p role="status">Loading tracked sites…</p>}
      {sites.isError && <p role="alert">Tracked Sites could not be loaded.</p>}
      {!sites.isPending && items.length === 0 && <p>No tracked sites yet.</p>}
      <div className="space-y-4">
        {items.map((site) => (
          <article
            key={site.id}
            className="rounded-xl border border-slate-700 p-5"
          >
            <h2 className="text-xl font-semibold">
              <Link href={`/app/tracked-sites/${site.id}`}>{site.name}</Link>
            </h2>
            <dl className="mt-3 grid grid-cols-3 gap-3">
              <div>
                <dt className="text-slate-500">Primary Domain</dt>
                <dd>{site.primary_domain ?? "None"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Aliases</dt>
                <dd>{site.domain_alias_count}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Status</dt>
                <dd className="capitalize">{site.status}</dd>
              </div>
            </dl>
            <div className="mt-4 flex gap-4">
              <Link
                className="text-teal-300"
                href={`/app/tracked-sites/${site.id}`}
              >
                Open
              </Link>
              <button
                onClick={() =>
                  statusMutation.mutate({
                    id: site.id,
                    status: site.status === "active" ? "archived" : "active",
                  })
                }
              >
                {site.status === "active" ? "Archive" : "Reactivate"}
              </button>
              <button
                className="text-red-300"
                onClick={() => {
                  if (
                    window.confirm(
                      "Delete this Tracked Site and all its domains?",
                    )
                  )
                    remove.mutate(site.id);
                }}
              >
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>
      {sites.hasNextPage && (
        <button
          className="mt-6 rounded-lg border border-slate-600 px-5 py-3"
          onClick={() => void sites.fetchNextPage()}
        >
          Load more tracked sites
        </button>
      )}
    </main>
  );
}
