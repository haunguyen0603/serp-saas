"use client";
import { Alert, Button, Input, Select, Textarea } from "@/design-system/ui";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api/client";
import { createProject, projectKeys } from "./api";
import { ProtectedStatus, useProtectedAuth } from "./protected";
import type { Device, ProjectCreate } from "./types";
import { CountrySelect, LanguageSelect } from "./locale-select";

const field = "";

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
    const country = String(values.get("country") ?? "");
    const language = String(values.get("language") ?? "");
    if (!country || !language) {
      setError("Select a country and language before creating a project.");
      return;
    }
    const keywords = String(values.get("keywords") ?? "").split(/\r?\n/);
    if (keywords.length > 1000) {
      setError("A Project may contain at most 1000 keyword lines.");
      return;
    }
    const input: ProjectCreate = {
      name: String(values.get("name") ?? ""),
      search_engine: "google",
      country_code: country,
      language_code: language,
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
      <Link className="text-brand underline" href="/app/projects">
        ← Projects
      </Link>
      <h1 className="my-8 text-4xl font-semibold">Create Project</h1>
      <form onSubmit={submit} className="space-y-5" aria-label="Create project">
        <label className="block">
          Project name
          <Input name="name" required maxLength={200} className={field} />
        </label>
        <label className="block">
          Search engine
          <Select name="searchEngine" className={field} defaultValue="google">
            <option value="google">Google</option>
          </Select>
        </label>
        <div className="grid gap-5 sm:grid-cols-2">
          <CountrySelect name="country" required className={field} />
          <LanguageSelect name="language" required className={field} />
          <label>
            Device
            <Select name="device" defaultValue="desktop" className={field}>
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
            </Select>
          </label>
          <label>
            Location (optional)
            <Input name="location" className={field} />
          </label>
        </div>
        <label className="block">
          Keywords, one per line
          <Textarea
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
        <p className="text-sm text-secondary">
          {keywordCount} {keywordCount === 1 ? "keyword" : "keywords"}. Empty
          and duplicate lines are cleaned automatically.
        </p>
        {error && <Alert className="text-danger">{error}</Alert>}
        <Button disabled={mutation.isPending} variant="primary">
          {mutation.isPending ? "Creating…" : "Create Project"}
        </Button>
      </form>
    </main>
  );
}
