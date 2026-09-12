"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { listProjects, projectKeys } from "./api";
import { ProtectedStatus, useProtectedAuth } from "./protected";
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
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-widest text-teal-400">
            SERP SaaS
          </p>
          <h1 className="mt-2 text-4xl font-semibold">Projects</h1>
        </div>
        <Link
          href="/app/projects/new"
          className="rounded-lg bg-teal-400 px-5 py-3 font-semibold text-slate-950"
        >
          Create Project
        </Link>
      </div>
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <label>
          Search projects
          <input
            className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Project name"
          />
        </label>
        <label>
          Project status
          <select
            className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3"
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as ProjectStatus | "all")
            }
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </select>
        </label>
      </div>
      {projects.isPending && <p role="status">Loading projects…</p>}
      {projects.isError && (
        <div role="alert" className="rounded-lg border border-red-400/30 p-5">
          <p>Projects could not be loaded.</p>
          <button
            className="mt-3 text-teal-300 underline"
            onClick={() => void projects.refetch()}
          >
            Retry
          </button>
        </div>
      )}
      {!projects.isPending && !projects.isError && items.length === 0 && (
        <div className="rounded-xl border border-slate-700 p-8 text-center">
          <h2 className="text-2xl">No projects yet.</h2>
          <p className="my-4 text-slate-400">
            Create your first project to start organizing keywords.
          </p>
          <Link className="text-teal-300 underline" href="/app/projects/new">
            Create Project
          </Link>
        </div>
      )}
      <div className="space-y-4">
        {items.map((project) => (
          <article
            key={project.id}
            className="rounded-xl border border-slate-700 bg-slate-900/50 p-5"
          >
            <div className="flex flex-wrap justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">
                  <Link
                    className="hover:text-teal-300"
                    href={`/app/projects/${project.id}`}
                  >
                    {project.name}
                  </Link>
                </h2>
                <p className="mt-1 text-slate-400">
                  {project.search_engine === "google"
                    ? "Google"
                    : project.search_engine}{" "}
                  · {project.country_code} · {project.language_code} ·{" "}
                  <span className="capitalize">{project.device}</span>
                </p>
              </div>
              <span
                className={
                  project.status === "active"
                    ? "text-teal-300"
                    : "text-amber-300"
                }
              >
                {project.status === "active" ? "Active" : "Archived"}
              </span>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-slate-500">Country</dt>
                <dd>{project.country_code}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Language</dt>
                <dd>{project.language_code}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Device</dt>
                <dd className="capitalize">{project.device}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Keywords</dt>
                <dd>{project.keyword_count}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
      {projects.hasNextPage && (
        <button
          className="mt-6 rounded-lg border border-slate-600 px-5 py-3"
          disabled={projects.isFetchingNextPage}
          onClick={() => void projects.fetchNextPage()}
        >
          {projects.isFetchingNextPage ? "Loading…" : "Load more projects"}
        </button>
      )}
    </main>
  );
}
