"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api/client";
import { createProject, projectKeys } from "./api";
import { ProtectedStatus, useProtectedAuth } from "./protected";
import type { Device, ProjectCreate } from "./types";

const field =
  "mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3";

export function ProjectForm() {
  const auth = useProtectedAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [keywordCount, setKeywordCount] = useState(0);
  const mutation = useMutation({
    mutationFn: (input: ProjectCreate) => createProject(auth.request, input),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      router.replace(`/app/projects/${result.project.id}`);
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

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const values = new FormData(event.currentTarget);
    const keywords = String(values.get("keywords") ?? "").split(/\r?\n/);
    if (keywords.length > 1000) {
      setError("A Project may contain at most 1000 keyword lines.");
      return;
    }
    const input: ProjectCreate = {
      name: String(values.get("name") ?? ""),
      search_engine: "google",
      country_code: String(values.get("country") ?? "VN"),
      language_code: String(values.get("language") ?? "vi"),
      device: String(values.get("device") ?? "desktop") as Device,
      location: String(values.get("location") ?? "") || null,
      keywords,
    };
    mutation.mutate(input, {
      onError: (failure) =>
        setError(
          failure instanceof ApiError
            ? failure.message
            : "Project could not be created.",
        ),
    });
  }
  return (
    <main className="max-w-xl">
      <Link className="text-teal-300 underline" href="/app/projects">
        ← Projects
      </Link>
      <h1 className="my-8 text-4xl font-semibold">Create Project</h1>
      <form onSubmit={submit} className="space-y-5" aria-label="Create project">
        <label className="block">
          Project name
          <input name="name" required maxLength={200} className={field} />
        </label>
        <label className="block">
          Search engine
          <select name="searchEngine" className={field} defaultValue="google">
            <option value="google">Google</option>
          </select>
        </label>
        <div className="grid gap-5 sm:grid-cols-2">
          <label>
            Country
            <input
              name="country"
              required
              defaultValue="VN"
              className={field}
            />
          </label>
          <label>
            Language
            <input
              name="language"
              required
              defaultValue="vi"
              className={field}
            />
          </label>
          <label>
            Device
            <select name="device" defaultValue="desktop" className={field}>
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
            </select>
          </label>
          <label>
            Location (optional)
            <input name="location" className={field} />
          </label>
        </div>
        <label className="block">
          Keywords, one per line
          <textarea
            name="keywords"
            required
            className={`${field} min-h-44`}
            placeholder={"keyword 1\nkeyword 2\nkeyword 3"}
            onChange={(event) =>
              setKeywordCount(
                event.target.value.split(/\r?\n/).filter((line) => line.trim())
                  .length,
              )
            }
          />
        </label>
        <p className="text-sm text-slate-400">
          {keywordCount} {keywordCount === 1 ? "keyword" : "keywords"}. Empty
          and duplicate lines are cleaned automatically.
        </p>
        {error && (
          <p role="alert" className="text-red-300">
            {error}
          </p>
        )}
        <button
          disabled={mutation.isPending}
          className="rounded-lg bg-teal-400 px-6 py-3 font-semibold text-slate-950 disabled:opacity-50"
        >
          {mutation.isPending ? "Creating…" : "Create Project"}
        </button>
      </form>
    </main>
  );
}
