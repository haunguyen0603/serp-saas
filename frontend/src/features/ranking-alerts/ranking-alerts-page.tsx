"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { Alert, Badge, Button, Select, Skeleton } from "@/design-system/ui";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import { listProjects } from "@/features/projects/api";
import {
  alertKeys,
  alertLabels,
  listAlerts,
  rankLabel,
  readAlert,
  readAllAlerts,
} from "./api";

export function RankingAlertsPage() {
  const auth = useProtectedAuth();
  const client = useQueryClient();
  const readStatus = useRef<HTMLParagraphElement>(null);
  const [project, setProject] = useState("");
  const [unread, setUnread] = useState(false);
  const [cursors, setCursors] = useState<string[]>([]);
  const enabled = auth.isAuthenticated && !auth.requiresEmailVerification;
  const cursor = cursors.at(-1);
  const projects = useInfiniteQuery({
    queryKey: [...alertKeys(auth.user?.id), "project-options"],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      listProjects(auth.request, {
        status: "all",
        limit: 200,
        cursor: pageParam,
      }),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled,
    retry: false,
  });
  const query = useQuery({
    queryKey: [...alertKeys(auth.user?.id), "inbox", project, unread, cursor],
    queryFn: () =>
      listAlerts(auth.request, {
        project_id: project,
        unread_only: unread,
        cursor,
      }),
    enabled,
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: async (id: string | null) => {
      if (id) await readAlert(auth.request, id);
      else await readAllAlerts(auth.request, project);
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: alertKeys(auth.user?.id) });
    },
  });
  useEffect(() => {
    if (mutation.isSuccess) readStatus.current?.focus({ preventScroll: true });
  }, [mutation.isSuccess]);
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
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Ranking Alerts</h1>
          <p className="mt-2 text-secondary">
            Get notified when tracked Google rankings change significantly after
            a completed check.
          </p>
        </div>
        <Button
          disabled={mutation.isPending || !query.data?.items.length}
          onClick={() => mutation.mutate(null)}
        >
          Mark all read
        </Button>
      </div>
      <div className="my-6 flex flex-wrap items-end gap-4">
        <label htmlFor="alert-status-filter">
          Show
          <Select
            id="alert-status-filter"
            aria-label="Show"
            value={unread ? "unread" : "all"}
            onChange={(event) => {
              setUnread(event.target.value === "unread");
              setCursors([]);
            }}
          >
            <option value="all">All alerts</option>
            <option value="unread">Unread</option>
          </Select>
        </label>
        <label htmlFor="alert-project-filter" className="min-w-0 max-w-full">
          Project
          <Select
            id="alert-project-filter"
            aria-label="Project"
            className="max-w-full"
            value={project}
            onChange={(event) => {
              setProject(event.target.value);
              setCursors([]);
            }}
          >
            <option value="">All projects</option>
            {projects.data?.pages
              .flatMap((page) => page.items)
              .map((item) => (
                <option value={item.id} key={item.id}>
                  {item.name} ({item.device})
                </option>
              ))}
          </Select>
        </label>
        {projects.hasNextPage && (
          <Button
            disabled={projects.isFetchingNextPage}
            onClick={() => void projects.fetchNextPage()}
          >
            Load more projects
          </Button>
        )}
        {projects.isError && (
          <Alert>
            Project filters unavailable.{" "}
            <Button onClick={() => void projects.refetch()}>
              Retry projects
            </Button>
          </Alert>
        )}
      </div>
      {project && (
        <Link
          className="text-brand underline"
          href={`/app/projects/${project}#ranking-alert-preferences`}
        >
          Manage project alert preferences
        </Link>
      )}
      {mutation.isError && (
        <Alert className="my-4">
          The read status could not be updated. Please try again.
        </Alert>
      )}
      {mutation.isSuccess && (
        <p
          role="status"
          ref={readStatus}
          tabIndex={-1}
          className="my-3 text-sm"
        >
          Read status updated.
        </p>
      )}
      {query.isPending ? (
        <Skeleton label="Loading ranking alerts…" />
      ) : query.isError ? (
        <Alert>
          Ranking alerts could not be loaded.{" "}
          <Button onClick={() => void query.refetch()}>Retry</Button>
        </Alert>
      ) : (
        <>
          <p role="status" className="my-4 text-sm text-secondary">
            {query.data.items.length} alerts on this page
          </p>
          {query.data.items.length === 0 ? (
            <section className="rounded-xl border border-border p-6">
              <h2 className="text-xl font-semibold">
                {unread ? "No unread ranking alerts" : "No ranking alerts yet"}
              </h2>
              <p className="mt-2 text-secondary">
                Alerts need two eligible completed checks. Review alert
                preferences in your project settings.
              </p>
              <Link
                className="mt-4 inline-block text-brand underline"
                href="/app/projects"
              >
                Go to Projects
              </Link>
            </section>
          ) : (
            <ul className="grid gap-4" aria-label="Ranking alerts">
              {query.data.items.map((item) => (
                <li
                  key={item.id}
                  className="min-w-0 rounded-xl border border-border bg-surface p-5"
                >
                  <article className="flex min-w-0 flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1 basis-64 break-words [overflow-wrap:anywhere]">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Badge>{alertLabels[item.alert_type]}</Badge>
                        <span className="text-sm text-secondary">
                          {item.read_at ? "Read" : "Unread"}
                        </span>
                      </div>
                      <h2 className="text-lg font-semibold">{item.keyword}</h2>
                      <p className="mt-2">
                        {rankLabel(item.previous_rank)} →{" "}
                        {rankLabel(item.current_rank)}
                        {item.rank_delta !== null &&
                          ` (${item.rank_delta > 0 ? "+" : ""}${item.rank_delta} positions)`}
                      </p>
                      <p className="mt-2 text-sm text-secondary">
                        {item.project_name} · {item.device} · {item.site_name}
                        {!item.tracked_site_id && " (deleted site)"}
                      </p>
                      <p className="mt-1 text-sm text-secondary">
                        Observed{" "}
                        <time dateTime={item.observed_at}>
                          {new Date(item.observed_at).toLocaleString()}
                        </time>{" "}
                        ({Intl.DateTimeFormat().resolvedOptions().timeZone})
                      </p>
                      <Link
                        className="mt-3 inline-block text-brand underline"
                        href={
                          item.tracked_site_id
                            ? `/app/projects/${item.project_id}/rankings?tracked_site_id=${item.tracked_site_id}&q=${encodeURIComponent(item.keyword)}`
                            : `/app/projects/${item.project_id}`
                        }
                      >
                        {item.tracked_site_id
                          ? "View ranking history"
                          : "View project"}
                      </Link>
                    </div>
                    {!item.read_at && (
                      <Button
                        aria-label={`Mark read: ${item.keyword}`}
                        disabled={mutation.isPending}
                        onClick={() => mutation.mutate(item.id)}
                      >
                        Mark read
                      </Button>
                    )}
                  </article>
                </li>
              ))}
            </ul>
          )}
          <nav aria-label="Alert pages" className="mt-6 flex flex-wrap gap-3">
            <Button
              disabled={!cursors.length}
              onClick={() => setCursors((values) => values.slice(0, -1))}
            >
              Previous
            </Button>
            <Button
              disabled={!query.data.next_cursor}
              onClick={() => {
                if (query.data.next_cursor)
                  setCursors((values) => [...values, query.data.next_cursor!]);
              }}
            >
              Next
            </Button>
          </nav>
        </>
      )}
    </main>
  );
}
