"use client";
import {
  Alert,
  Button,
  Input,
  Select,
  Skeleton,
  Toast,
} from "@/design-system/ui";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api/client";
import { deleteProject, getProject, projectKeys, updateProject } from "./api";
import { KeywordManager } from "./keyword-manager";
import { ProtectedStatus, useProtectedAuth } from "./protected";
import type { Device, Project, ProjectUpdate } from "./types";
import { ProjectAnalytics } from "@/features/analytics/project-analytics";
import { CountrySelect, LanguageSelect } from "./locale-select";

import { RankingAlertPreferences } from "@/features/ranking-alerts/alert-preferences";
const field = "";

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
    <section id="settings" className="mt-12 border-t border-border pt-10">
      <h2 className="text-2xl font-semibold">Project Settings</h2>
      <p className="mt-2 text-sm text-secondary">
        These settings apply to every keyword in this project.
      </p>
      <form
        className="mt-6 grid gap-4 sm:grid-cols-2"
        onSubmit={submit}
        aria-label="Project settings"
      >
        <label>
          Project name
          <Input
            className={field}
            name="name"
            defaultValue={project.name}
            maxLength={200}
            required
          />
        </label>
        <CountrySelect
          className={field}
          name="country"
          defaultValue={project.country_code}
          required
        />
        <LanguageSelect
          className={field}
          name="language"
          defaultValue={project.language_code}
          required
        />
        <label>
          Device
          <Select className={field} name="device" defaultValue={project.device}>
            <option value="desktop">Desktop</option>
            <option value="mobile">Mobile</option>
          </Select>
        </label>
        <label>
          Location
          <Input
            className={field}
            name="location"
            defaultValue={project.location ?? ""}
          />
        </label>
        <div className="sm:col-span-2">
          {mutation.isError && (
            <Alert className="mb-3 text-danger">
              {mutation.error instanceof ApiError
                ? mutation.error.message
                : "Project settings could not be saved."}
            </Alert>
          )}
          {message && <Toast key={message}>{message}</Toast>}
          <Button variant="primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Save Project Settings"}
          </Button>
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
      deleteMutation.reset();
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
  if (project.isPending) return <Skeleton label="Loading project…" />;
  if (project.isError)
    return (
      <main>
        <h1 className="text-3xl">Project unavailable</h1>
        <Alert className="my-5 text-danger">
          {project.error instanceof ApiError
            ? project.error.message
            : "Project could not be loaded."}
        </Alert>
        <Button onClick={() => void project.refetch()}>Retry</Button>
      </main>
    );

  const value = project.data;
  const deletionBlockedByHistory =
    deleteMutation.error instanceof ApiError &&
    deleteMutation.error.code === "HISTORY_EXISTS";
  return (
    <main>
      <Link className="text-brand underline" href="/app/projects">
        ← Projects
      </Link>
      <div className="my-8 flex flex-wrap items-start justify-between gap-5">
        <div>
          <h1 className="text-4xl font-semibold">{value.name}</h1>
          <p className="mt-2 text-secondary">
            Google · {value.country_code} · {value.language_code} ·{" "}
            <span className="capitalize">{value.device}</span>
            {value.location ? ` · ${value.location}` : ""}
          </p>
          <p className="mt-2">
            Status:{" "}
            <span className="capitalize text-brand">{value.status}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button
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
          </Button>
          <Button
            variant="danger"
            disabled={deleteMutation.isPending}
            confirmation="Delete this Project and its Keywords? Projects with ranking checks or batches, including failed checks, cannot be permanently deleted. Use Archive Project to stop new checks and keep your history."
            onClick={() => deleteMutation.mutate()}
          >
            Delete Project
          </Button>
        </div>
      </div>
      {deletionBlockedByHistory && (
        <Alert className="mb-5 text-danger">
          <p className="font-semibold">This Project could not be deleted.</p>
          <p className="mt-2">
            This Project has ranking history or a check schedule. Projects with
            ranking checks or batches cannot be permanently deleted, even if the
            checks failed.
          </p>
          <p className="mt-2">
            {value.status === "active"
              ? "Choose Archive Project above to stop new ranking checks while keeping your Keywords and ranking history. Then return to Projects and select the Active filter to hide archived Projects. You can find and reactivate this Project later using the Archived filter."
              : "This Project is already archived. Your Keywords and ranking history are preserved. You can find it using the Archived filter on Projects. Archiving does not allow permanent deletion."}
          </p>
          <p className="mt-2">
            If this Project only has a check schedule and has never been
            checked, delete the schedule in{" "}
            <a className="underline" href="#schedule">
              Schedule
            </a>{" "}
            and try deleting the Project again.
          </p>
        </Alert>
      )}
      {(statusMutation.isError ||
        (deleteMutation.isError && !deletionBlockedByHistory)) && (
        <Alert className="mb-5 text-danger">
          The project action could not be completed.
        </Alert>
      )}
      <nav aria-label="Project sections" className="ui-section-nav">
        <a href="#analytics">Analytics</a>
        <Link href={`/app/projects/${projectId}/rankings`}>
          Ranking Explorer
        </Link>
        <Link href={`/app/projects/${projectId}/competitors`}>Competitors</Link>
        <Link href={`/app/projects/${projectId}/reports`}>Reports</Link>
        <a className="text-brand" href="#keywords">
          Keywords
        </a>
        <a href="#rankings">Rankings</a>
        <a href="#batches">Batch History</a>
        <a href="#schedule">Schedule</a>
        <a href="#ranking-alert-preferences">Alert Preferences</a>
        <a className="text-brand" href="#settings">
          Project Settings
        </a>
      </nav>
      <ProjectAnalytics project={value} />
      <KeywordManager project={value} />
      <ProjectSettings project={value} />
      <RankingAlertPreferences projectId={projectId} />
    </main>
  );
}
