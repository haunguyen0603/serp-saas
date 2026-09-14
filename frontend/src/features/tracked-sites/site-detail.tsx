"use client";
import {
  Alert,
  Badge,
  Button,
  ErrorState,
  Input,
  Skeleton,
  StatusBadge,
} from "@/design-system/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api/client";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import {
  addTrackedDomain,
  deleteTrackedDomain,
  getTrackedSite,
  trackedSiteKeys,
  updateTrackedDomain,
  updateTrackedSite,
} from "./api";
const field = "";
export function TrackedSiteDetail({ siteId }: { siteId: string }) {
  const auth = useProtectedAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const site = useQuery({
    queryKey: trackedSiteKeys.detail(siteId),
    queryFn: () => getTrackedSite(auth.request, siteId),
    enabled: auth.isAuthenticated,
    retry: false,
  });
  const refresh = async () => {
    await queryClient.invalidateQueries({
      queryKey: trackedSiteKeys.detail(siteId),
    });
    await queryClient.invalidateQueries({ queryKey: trackedSiteKeys.lists() });
  };
  const add = useMutation({
    mutationFn: (input: { domain: string; make_primary: boolean }) =>
      addTrackedDomain(auth.request, siteId, input),
    onSuccess: refresh,
  });
  const updateDomain = useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: { active?: boolean; is_primary?: boolean };
    }) => updateTrackedDomain(auth.request, siteId, id, input),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteTrackedDomain(auth.request, siteId, id),
    onSuccess: refresh,
  });
  const status = useMutation({
    mutationFn: (value: "active" | "archived") =>
      updateTrackedSite(auth.request, siteId, { status: value }),
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
  if (site.isPending) return <Skeleton label="Loading Tracked Site…" />;
  if (site.isError)
    return (
      <ErrorState onRetry={() => void site.refetch()}>
        {site.error instanceof ApiError
          ? site.error.message
          : "Tracked Site could not be loaded."}
      </ErrorState>
    );
  const value = site.data;
  function addDomain(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);
    add.mutate(
      {
        domain: String(data.get("domain") ?? ""),
        make_primary: data.get("makePrimary") === "on",
      },
      {
        onSuccess: () => form.reset(),
        onError: (failure) =>
          setError(
            failure instanceof ApiError
              ? failure.message
              : "Domain could not be added.",
          ),
      },
    );
  }
  return (
    <main>
      <Link className="text-brand underline" href="/app/tracked-sites">
        ← Tracked Sites
      </Link>
      <div className="my-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-semibold">{value.name}</h1>
          <p className="mt-3">
            Primary: <strong>{value.primary_domain ?? "None"}</strong>
          </p>
          <div className="mt-2 flex items-center gap-2">
            <span>Status:</span> <StatusBadge status={value.status} />
          </div>
        </div>
        <Button
          onClick={() =>
            status.mutate(value.status === "active" ? "archived" : "active")
          }
        >
          {value.status === "active" ? "Archive Site" : "Reactivate Site"}
        </Button>
      </div>
      {(updateDomain.isError || remove.isError || status.isError) && (
        <Alert>
          {(updateDomain.error ?? remove.error ?? status.error) instanceof
          ApiError
            ? (updateDomain.error ?? remove.error ?? status.error)?.message
            : "The site action could not be completed. Please try again."}
        </Alert>
      )}
      <section>
        <h2 className="text-2xl font-semibold">Domain aliases</h2>
        <p className="text-secondary mt-2">
          Moved your site with a 301 redirect? Keep the old domain as an alias
          so ranking matches remain connected to this site.
        </p>
        <div className="mt-5 space-y-3">
          {value.domains.map((domain) => (
            <article
              key={domain.id}
              className="rounded-lg border border-border p-4"
            >
              <div className="flex flex-wrap justify-between gap-4">
                <div>
                  <strong>{domain.domain}</strong>
                  <p className="mt-1 text-sm">
                    {domain.is_primary && (
                      <Badge tone="info" className="mr-2">
                        PRIMARY
                      </Badge>
                    )}
                    {!domain.is_primary && (
                      <Badge className="mr-2">Alias</Badge>
                    )}
                    <Badge tone={domain.active ? "success" : "neutral"}>
                      {domain.active ? "ACTIVE" : "INACTIVE"}
                    </Badge>
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  {!domain.is_primary && (
                    <Button
                      onClick={() =>
                        updateDomain.mutate({
                          id: domain.id,
                          input: { is_primary: true },
                        })
                      }
                    >
                      Make primary
                    </Button>
                  )}
                  <Button
                    disabled={domain.is_primary || updateDomain.isPending}
                    confirmation={
                      domain.active
                        ? "Deactivate this alias? Future checks will no longer match it until you activate it again."
                        : undefined
                    }
                    onClick={() =>
                      updateDomain.mutate({
                        id: domain.id,
                        input: { active: !domain.active },
                      })
                    }
                  >
                    {domain.active ? "Deactivate" : "Activate"}
                  </Button>
                  <Button
                    variant="danger"
                    confirmation="Remove this domain alias? Future checks will no longer match it to this site."
                    onClick={() => remove.mutate(domain.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </article>
          ))}
        </div>
        <form
          aria-label="Add domain"
          onSubmit={addDomain}
          className="mt-8 rounded-xl border border-border p-5"
        >
          <h3 className="text-xl">Add Domain</h3>
          <label className="mt-4 block">
            Domain
            <Input
              name="domain"
              required
              className={field}
              placeholder="new-domain.com"
            />
          </label>
          <label className="mt-4 flex gap-3">
            <Input name="makePrimary" type="checkbox" />
            Make primary
          </label>
          {error && <Alert className="mt-3 text-danger">{error}</Alert>}
          <Button disabled={add.isPending} className="mt-4" variant="primary">
            {add.isPending ? "Adding…" : "Add Domain"}
          </Button>
        </form>
      </section>
    </main>
  );
}
