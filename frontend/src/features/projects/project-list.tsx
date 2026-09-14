"use client";
import {
  Button,
  Input,
  Select,
  Skeleton,
  Card,
  StatusBadge,
  EmptyState,
  ErrorState,
  PageHeader,
} from "@/design-system/ui";

import { useInfiniteQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { listProjects, projectKeys } from "./api";
import { ProtectedStatus, useProtectedAuth } from "./protected";
import { ProjectActivity } from "./project-activity";
import type { ProjectStatus } from "./types";

export function ProjectList() {
  const auth = useProtectedAuth();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<ProjectStatus | "all">("active");
  const filters = { search, status, limit: 20 } as const;
  const projects = useInfiniteQuery({
    queryKey: projectKeys.list(filters),
    queryFn: ({ pageParam }) =>
      listProjects(auth.request, { ...filters, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: auth.isAuthenticated,
  });

  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );

  const items = projects.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <main>
      <PageHeader
        eyebrow="SERP SaaS"
        title="Projects"
        actions={
          <Link href="/app/projects/new" className="ui-link-button">
            Create Project
          </Link>
        }
      />
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <label>
          Search projects
          <Input
            className="mt-2 w-full"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Project name"
          />
        </label>
        <label>
          Project status
          <Select
            className="mt-2 w-full"
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as ProjectStatus | "all")
            }
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </Select>
        </label>
      </div>
      {projects.isPending && <Skeleton label="Loading projects…" />}
      {projects.isError && (
        <ErrorState onRetry={() => void projects.refetch()}>
          Projects could not be loaded.
        </ErrorState>
      )}
      {!projects.isPending && !projects.isError && items.length === 0 && (
        <EmptyState
          title={
            search || status !== "active"
              ? "No matching projects"
              : "No projects yet."
          }
          action={
            <Link className="ui-link-button" href="/app/projects/new">
              Create Project
            </Link>
          }
        >
          Create your first project to start organizing keywords, or change your
          filters.
        </EmptyState>
      )}
      <div className="space-y-4">
        {items.map((project) => (
          <Card key={project.id}>
            <div className="flex flex-wrap justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">
                  <Link
                    className="hover:text-brand"
                    href={`/app/projects/${project.id}`}
                  >
                    {project.name}
                  </Link>
                </h2>
                <p className="mt-1 text-secondary">
                  {project.search_engine === "google"
                    ? "Google"
                    : project.search_engine}{" "}
                  · {project.country_code} · {project.language_code} ·{" "}
                  <span className="capitalize">{project.device}</span>
                </p>
              </div>
              <StatusBadge status={project.status} />
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-secondary">Country</dt>
                <dd>{project.country_code}</dd>
              </div>
              <div>
                <dt className="text-secondary">Language / Location</dt>
                <dd>
                  {project.language_code} · {project.location || "Country-wide"}
                </dd>
              </div>
              <div>
                <dt className="text-secondary">Device</dt>
                <dd className="capitalize">{project.device}</dd>
              </div>
              <div>
                <dt className="text-secondary">Keywords</dt>
                <dd>{project.keyword_count}</dd>
              </div>
            </dl>
            <ProjectActivity projectId={project.id} />
          </Card>
        ))}
      </div>
      {projects.hasNextPage && (
        <Button
          className="mt-6"
          disabled={projects.isFetchingNextPage}
          onClick={() => void projects.fetchNextPage()}
        >
          {projects.isFetchingNextPage ? "Loading…" : "Load more projects"}
        </Button>
      )}
    </main>
  );
}
