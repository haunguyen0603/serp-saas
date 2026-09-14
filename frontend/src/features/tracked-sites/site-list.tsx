"use client";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Select,
  Skeleton,
  StatusBadge,
} from "@/design-system/ui";
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
const field = "";
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
      <PageHeader
        title="Tracked Sites"
        actions={
          <Link href="/app/tracked-sites/new" className="ui-link-button">
            Add Tracked Site
          </Link>
        }
      />
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <label>
          Search tracked sites
          <Input
            className={field}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label>
          Site status
          <Select
            className={field}
            value={status}
            onChange={(event) => setStatus(event.target.value as typeof status)}
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </Select>
        </label>
      </div>
      {sites.isPending && <Skeleton label="Loading tracked sites…" />}
      {sites.isError && (
        <ErrorState onRetry={() => void sites.refetch()}>
          Tracked Sites could not be loaded.
        </ErrorState>
      )}
      {!sites.isPending && !sites.isError && items.length === 0 && (
        <EmptyState
          title={
            search || status !== "active"
              ? "No matching sites"
              : "No tracked sites yet."
          }
        >
          Add a site to connect current and previous domains with ranking
          results, or change your filters.
        </EmptyState>
      )}
      <div className="space-y-4">
        {items.map((site) => (
          <Card key={site.id}>
            <h2 className="text-xl font-semibold">
              <Link href={`/app/tracked-sites/${site.id}`}>{site.name}</Link>
            </h2>
            <dl className="mt-3 grid grid-cols-3 gap-3">
              <div>
                <dt className="text-secondary">Primary Domain</dt>
                <dd>{site.primary_domain ?? "None"}</dd>
              </div>
              <div>
                <dt className="text-secondary">Aliases</dt>
                <dd>{site.domain_alias_count}</dd>
              </div>
              <div>
                <dt className="text-secondary">Status</dt>
                <dd>
                  <StatusBadge status={site.status} />
                </dd>
              </div>
            </dl>
            <div className="mt-4 flex gap-4">
              <Link
                className="ui-link-button"
                href={`/app/tracked-sites/${site.id}`}
              >
                Open
              </Link>
              <Button
                onClick={() =>
                  statusMutation.mutate({
                    id: site.id,
                    status: site.status === "active" ? "archived" : "active",
                  })
                }
              >
                {site.status === "active" ? "Archive" : "Reactivate"}
              </Button>
              <Button
                variant="danger"
                confirmation="Delete this Tracked Site and all its aliases? Ranking history remains unchanged."
                onClick={() => remove.mutate(site.id)}
              >
                Delete
              </Button>
            </div>
          </Card>
        ))}
      </div>
      {sites.hasNextPage && (
        <Button className="mt-6" onClick={() => void sites.fetchNextPage()}>
          Load more tracked sites
        </Button>
      )}
    </main>
  );
}
