"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api/client";
import { deleteProject, getProject, projectKeys, updateProject } from "./api";
import { KeywordManager } from "./keyword-manager";
import { ProtectedStatus, useProtectedAuth } from "./protected";
import type { Device, Project, ProjectUpdate } from "./types";

const field =
  "mt-2 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2";

function ProjectSettings({ project }: { project: Project }) {
  const auth = useProtectedAuth();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (input: ProjectUpdate) =>
      updateProject(auth.request, project.id, input),
    onSuccess: async (updated) => {
      queryClient.setQueryData(projectKeys.detail(project.id), updated);
      await queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      setMessage("Project settings saved.");
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    const values = new FormData(event.currentTarget);
    mutation.mutate({
      name: String(values.get("name") ?? ""),
      search_engine: "google",
      country_code: String(values.get("country") ?? ""),
      language_code: String(values.get("language") ?? ""),
      device: String(values.get("device") ?? "desktop") as Device,
      location: String(values.get("location") ?? "") || null,
    });
  }

  return (
    <section id="settings" className="mt-12 border-t border-slate-700 pt-10">
      <h2 className="text-2xl font-semibold">Project Settings</h2>
      <p className="mt-2 text-sm text-slate-400">
        These settings apply to every keyword in this project.
      </p>
      <form
        className="mt-6 grid gap-4 sm:grid-cols-2"
        onSubmit={submit}
        aria-label="Project settings"
      >
        <label>
          Project name
          <input
            className={field}
            name="name"
            defaultValue={project.name}
            maxLength={200}
            required
          />
        </label>
        <label>
          Country
          <input
            className={field}
            name="country"
            defaultValue={project.country_code}
            required
          />
        </label>
        <label>
          Language
          <input
            className={field}
            name="language"
            defaultValue={project.language_code}
            required
          />
        </label>
        <label>
          Device
          <select className={field} name="device" defaultValue={project.device}>
            <option value="desktop">Desktop</option>
            <option value="mobile">Mobile</option>
          </select>
        </label>
        <label>
          Location
          <input
            className={field}
            name="location"
            defaultValue={project.location ?? ""}
          />
        </label>
        <div className="sm:col-span-2">
          {mutation.isError && (
            <p role="alert" className="mb-3 text-red-300">
              {mutation.error instanceof ApiError
                ? mutation.error.message
                : "Project settings could not be saved."}
            </p>
          )}
          {message && (
            <p role="status" className="mb-3 text-teal-300">
              {message}
            </p>
          )}
          <button
            disabled={mutation.isPending}
            className="rounded-lg border border-teal-500 px-5 py-3 text-teal-200"
          >
            {mutation.isPending ? "Saving…" : "Save Project Settings"}
          </button>
        </div>
      </form>
    </section>
  );
}

export function ProjectDetail({ projectId }: { projectId: string }) {
  const auth = useProtectedAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const project = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => getProject(auth.request, projectId),
    enabled: auth.isAuthenticated,
    retry: false,
  });
  const statusMutation = useMutation({
    mutationFn: (status: "active" | "archived") =>
      updateProject(auth.request, projectId, { status }),
    onSuccess: async (updated) => {
      queryClient.setQueryData(projectKeys.detail(projectId), updated);
      await queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteProject(auth.request, projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: projectKeys.detail(projectId),
        refetchType: "none",
      });
      await queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      router.replace("/app/projects");
    },
  });

  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  if (project.isPending) return <p role="status">Loading project…</p>;
  if (project.isError)
    return (
      <main>
        <h1 className="text-3xl">Project unavailable</h1>
        <p role="alert" className="my-5 text-red-300">
          {project.error instanceof ApiError
            ? project.error.message
            : "Project could not be loaded."}
        </p>
        <button
          className="text-teal-300 underline"
          onClick={() => void project.refetch()}
        >
          Retry
        </button>
      </main>
    );

  const value = project.data;
  return (
    <main>
      <Link className="text-teal-300 underline" href="/app/projects">
        ← Projects
      </Link>
      <div className="my-8 flex flex-wrap items-start justify-between gap-5">
        <div>
          <h1 className="text-4xl font-semibold">{value.name}</h1>
          <p className="mt-2 text-slate-400">
            Google · {value.country_code} · {value.language_code} ·{" "}
            <span className="capitalize">{value.device}</span>
            {value.location ? ` · ${value.location}` : ""}
          </p>
          <p className="mt-2">
            Status:{" "}
            <span className="capitalize text-teal-300">{value.status}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            className="rounded-lg border border-slate-600 px-4 py-2"
            disabled={statusMutation.isPending}
            onClick={() =>
              statusMutation.mutate(
                value.status === "active" ? "archived" : "active",
              )
            }
          >
            {value.status === "active"
              ? "Archive Project"
              : "Reactivate Project"}
          </button>
          <button
            className="rounded-lg border border-red-500/70 px-4 py-2 text-red-300"
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (
                window.confirm(
                  "Deleting this project will also delete its keywords. Continue?",
                )
              )
                deleteMutation.mutate();
            }}
          >
            Delete Project
          </button>
        </div>
      </div>
      {(statusMutation.isError || deleteMutation.isError) && (
        <p role="alert" className="mb-5 text-red-300">
          The project action could not be completed.
        </p>
      )}
      <nav className="mb-8 flex gap-5 border-b border-slate-700 pb-4">
        <a className="text-teal-300" href="#keywords">
          Keywords
        </a>
        <a className="text-teal-300" href="#settings">
          Project Settings
        </a>
      </nav>
      <KeywordManager project={value} />
      <ProjectSettings project={value} />
    </main>
  );
}
