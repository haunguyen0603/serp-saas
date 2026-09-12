"use client";
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
const field =
  "mt-2 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2";
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
  if (site.isPending) return <p role="status">Loading Tracked Site…</p>;
  if (site.isError)
    return (
      <p role="alert">
        {site.error instanceof ApiError
          ? site.error.message
          : "Tracked Site could not be loaded."}
      </p>
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
      <Link className="text-teal-300 underline" href="/app/tracked-sites">
        ← Tracked Sites
      </Link>
      <div className="my-8 flex justify-between gap-4">
        <div>
          <h1 className="text-4xl font-semibold">{value.name}</h1>
          <p className="mt-3">
            Primary: <strong>{value.primary_domain ?? "None"}</strong>
          </p>
          <p className="mt-2 capitalize">Status: {value.status}</p>
        </div>
        <button
          onClick={() =>
            status.mutate(value.status === "active" ? "archived" : "active")
          }
        >
          {value.status === "active" ? "Archive Site" : "Reactivate Site"}
        </button>
      </div>
      <section>
        <h2 className="text-2xl font-semibold">Domain aliases</h2>
        <div className="mt-5 space-y-3">
          {value.domains.map((domain) => (
            <article
              key={domain.id}
              className="rounded-lg border border-slate-700 p-4"
            >
              <div className="flex flex-wrap justify-between gap-4">
                <div>
                  <strong>{domain.domain}</strong>
                  <p className="mt-1 text-sm">
                    {domain.is_primary && (
                      <span className="mr-3 text-teal-300">PRIMARY</span>
                    )}
                    <span>{domain.active ? "ACTIVE" : "INACTIVE"}</span>
                  </p>
                </div>
                <div className="flex gap-3">
                  {!domain.is_primary && (
                    <button
                      onClick={() =>
                        updateDomain.mutate({
                          id: domain.id,
                          input: { is_primary: true },
                        })
                      }
                    >
                      Make primary
                    </button>
                  )}
                  <button
                    disabled={domain.is_primary}
                    onClick={() =>
                      updateDomain.mutate({
                        id: domain.id,
                        input: { active: !domain.active },
                      })
                    }
                  >
                    {domain.active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    className="text-red-300"
                    onClick={() => remove.mutate(domain.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
        <form
          aria-label="Add domain"
          onSubmit={addDomain}
          className="mt-8 rounded-xl border border-slate-700 p-5"
        >
          <h3 className="text-xl">Add Domain</h3>
          <label className="mt-4 block">
            Domain
            <input
              name="domain"
              required
              className={field}
              placeholder="new-domain.com"
            />
          </label>
          <label className="mt-4 flex gap-3">
            <input name="makePrimary" type="checkbox" />
            Make primary
          </label>
          {error && (
            <p role="alert" className="mt-3 text-red-300">
              {error}
            </p>
          )}
          <button
            disabled={add.isPending}
            className="mt-4 rounded-lg bg-teal-400 px-5 py-2 font-semibold text-slate-950"
          >
            {add.isPending ? "Adding…" : "Add Domain"}
          </button>
        </form>
      </section>
    </main>
  );
}
