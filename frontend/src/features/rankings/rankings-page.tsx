"use client";
import Link from "next/link";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  useProtectedAuth,
  ProtectedStatus,
} from "@/features/projects/protected";
import { listProjects, projectKeys } from "@/features/projects/api";
import { getLatestRankings, rankingKeys } from "./api";
import {
  Card,
  CursorPagination,
  EmptyState,
  ErrorState,
  PageHeader,
  Select,
  Skeleton,
  StatusBadge,
  Table,
  Tabs,
} from "@/design-system/ui";
export function RankingsPage() {
  const auth = useProtectedAuth();
  const [selected, setSelected] = useState("");
  const [view, setView] = useState("all");
  const projects = useInfiniteQuery({
    queryKey: projectKeys.list({ status: "active", limit: 50 }),
    queryFn: ({ pageParam }) =>
      listProjects(auth.request, {
        status: "active",
        limit: 50,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_cursor ?? undefined,
    enabled: auth.isAuthenticated,
  });
  const items = projects.data?.pages.flatMap((p) => p.items) ?? [];
  const projectId = selected || items[0]?.id || "";
  const rankings = useQuery({
    queryKey: rankingKeys.latest(projectId),
    queryFn: () => getLatestRankings(auth.request, projectId),
    enabled: auth.isAuthenticated && !!projectId,
  });
  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  return (
    <main>
      <PageHeader
        title="Rankings"
        description="Your latest keyword positions, matched to your Tracked Sites."
        actions={
          projectId && (
            <Link
              href={`/app/projects/${projectId}#keywords`}
              className="ui-link-button"
            >
              Check Rankings
            </Link>
          )
        }
      />
      {projects.isError && (
        <ErrorState onRetry={() => void projects.refetch()}>
          Projects could not be loaded.
        </ErrorState>
      )}
      {projects.isPending && <Skeleton label="Loading projects…" />}
      {!projects.isPending && !projects.isError && !items.length && (
        <EmptyState
          title="No rankings yet"
          action={
            <Link href="/app/projects/new" className="ui-link-button">
              Create Project
            </Link>
          }
        >
          Create a project and add keywords to start tracking positions.
        </EmptyState>
      )}
      {!!items.length && (
        <>
          <Card className="mb-6">
            <label>
              Project
              <Select
                value={projectId}
                onChange={(e) => setSelected(e.target.value)}
              >
                {items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} · {p.device} · {p.country_code}
                  </option>
                ))}
              </Select>
            </label>
            <CursorPagination
              hasMore={!!projects.hasNextPage}
              loading={projects.isFetchingNextPage}
              onNext={() => void projects.fetchNextPage()}
              label="Load more projects"
            />
          </Card>
          {rankings.isPending && <Skeleton label="Loading rankings…" />}
          {rankings.isError && (
            <ErrorState onRetry={() => void rankings.refetch()}>
              Rankings could not be loaded.
            </ErrorState>
          )}
          <Tabs
            label="Ranking view"
            value={view}
            onChange={setView}
            items={[
              { value: "all", label: "All keywords" },
              { value: "ranked", label: "Ranked" },
              { value: "attention", label: "Needs attention" },
            ]}
          />
          {rankings.data && (
            <Table aria-label="Latest rankings">
              <thead>
                <tr>
                  <th>Keyword</th>
                  <th>Tracked Site</th>
                  <th>Position</th>
                  <th>Checked at</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rankings.data.items
                  .filter(
                    (item) =>
                      view === "all" ||
                      (view === "ranked"
                        ? !!item.latest_check?.rankings.length
                        : !item.latest_check?.rankings.length),
                  )
                  .map((item) => {
                    const check = item.latest_check;
                    return (
                      <tr key={item.keyword_id}>
                        <td>
                          <Link
                            href={`/app/projects/${projectId}#keywords`}
                            className="text-brand font-semibold"
                          >
                            {item.keyword}
                          </Link>
                        </td>
                        <td>
                          {check?.rankings.map((r) => (
                            <div key={r.tracked_site_id ?? r.tracked_site_name}>
                              {r.matched_domain}
                            </div>
                          )) || "—"}
                          {check && !check.rankings.length && "—"}
                        </td>
                        <td>
                          {check?.rankings.length
                            ? check.rankings.map((r) => (
                                <div
                                  key={r.tracked_site_id ?? r.tracked_site_name}
                                >
                                  #{r.position}
                                </div>
                              ))
                            : check?.status === "succeeded"
                              ? `Not found in Top ${check.result_limit}`
                              : "—"}
                        </td>
                        <td>
                          {check
                            ? new Date(check.requested_at).toLocaleString()
                            : "—"}
                        </td>
                        <td>
                          <StatusBadge
                            status={
                              !check
                                ? "Never checked"
                                : check.status === "succeeded"
                                  ? check.rankings.length
                                    ? "Ranked"
                                    : "Not found"
                                  : check.status
                            }
                          />
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </Table>
          )}
        </>
      )}
    </main>
  );
}
