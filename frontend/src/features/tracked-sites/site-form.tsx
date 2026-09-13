"use client";
import { Alert, Button, Input, Textarea } from "@/design-system/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api/client";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import { createTrackedSite, trackedSiteKeys } from "./api";
import type { TrackedSiteCreate } from "./types";
const field = "";
export function TrackedSiteForm() {
  const auth = useProtectedAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (input: TrackedSiteCreate) =>
      createTrackedSite(auth.request, input),
    onSuccess: async (site) => {
      await queryClient.invalidateQueries({
        queryKey: trackedSiteKeys.lists(),
      });
      router.replace(`/app/tracked-sites/${site.id}`);
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
    const values = new FormData(event.currentTarget);
    mutation.mutate(
      {
        name: String(values.get("name") ?? ""),
        primary_domain: String(values.get("primaryDomain") ?? ""),
        aliases: String(values.get("aliases") ?? "")
          .split(/\r?\n/)
          .filter((value) => value.trim()),
      },
      {
        onError: (failure) =>
          setError(
            failure instanceof ApiError
              ? failure.message
              : "Tracked Site could not be created.",
          ),
      },
    );
  }
  return (
    <main className="max-w-xl">
      <Link className="text-brand underline" href="/app/tracked-sites">
        ← Tracked Sites
      </Link>
      <h1 className="my-8 text-4xl font-semibold">Add Tracked Site</h1>
      <form
        aria-label="Add tracked site"
        className="space-y-5"
        onSubmit={submit}
      >
        <label className="block">
          Site Name
          <Input name="name" className={field} required maxLength={200} />
        </label>
        <label className="block">
          Primary Domain
          <Input
            name="primaryDomain"
            className={field}
            required
            placeholder="new-domain.com"
          />
        </label>
        <label className="block">
          Previous / Alias Domains
          <Textarea
            name="aliases"
            className={`${field} min-h-36`}
            placeholder={"old-domain.com\nsecond-domain.com"}
          />
        </label>
        {error && <Alert className="text-danger">{error}</Alert>}
        <Button disabled={mutation.isPending} variant="primary">
          {mutation.isPending ? "Creating…" : "Create Site"}
        </Button>
      </form>
    </main>
  );
}
