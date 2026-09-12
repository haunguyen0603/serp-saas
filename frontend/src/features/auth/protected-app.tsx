"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "./auth-provider";
import { ApiError } from "@/lib/api/client";

export function ProtectedApp() {
  const auth = useAuth();
  const router = useRouter();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const me = useQuery({
    queryKey: ["current-user", auth.user?.id],
    queryFn: auth.getCurrentUser,
    enabled: auth.isAuthenticated,
    retry: false,
    staleTime: 0,
  });
  useEffect(() => {
    if (auth.status === "anonymous") router.replace("/login");
  }, [auth.status, router]);

  async function logout() {
    setLoggingOut(true);
    setLogoutError(null);
    try {
      await auth.logout();
      router.replace("/login");
    } catch {
      setLogoutError("Logout could not be completed. Please try again.");
    } finally {
      setLoggingOut(false);
    }
  }

  if (auth.status === "error")
    return (
      <main>
        <h1 className="text-3xl">Session unavailable</h1>
        <p role="alert" className="my-6">
          {auth.error}
        </p>
        <button
          onClick={() => {
            void auth.refresh().catch(() => {});
          }}
          className="text-teal-300 underline"
        >
          Retry
        </button>
      </main>
    );
  if (!auth.isAuthenticated)
    return (
      <main>
        <p role="status">
          {auth.isLoading ? "Restoring session…" : "Redirecting to login…"}
        </p>
      </main>
    );
  if (me.isPending)
    return (
      <main>
        <p role="status">Loading your account…</p>
      </main>
    );
  if (me.isError)
    return (
      <main>
        <h1 className="text-3xl">Account unavailable</h1>
        <p role="alert" className="my-6">
          {me.error instanceof ApiError
            ? me.error.message
            : "The service is unavailable."}
        </p>
        <button
          onClick={() => {
            void me.refetch();
          }}
          className="mr-6 text-teal-300 underline"
        >
          Retry
        </button>
        <button
          onClick={() => {
            void logout();
          }}
          disabled={loggingOut}
        >
          Logout
        </button>
        {logoutError && <p role="alert">{logoutError}</p>}
      </main>
    );
  return (
    <main>
      <h1 className="mb-8 text-4xl font-semibold">SERP SaaS</h1>
      <dl className="space-y-6 rounded-xl border border-slate-700 bg-slate-900/50 p-6">
        <div>
          <dt className="text-slate-400">Signed in as:</dt>
          <dd className="mt-2 text-xl">{me.data.email}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Account status:</dt>
          <dd className="mt-2 text-teal-300">
            {me.data.status === "active" ? "Active" : "Disabled"}
          </dd>
        </div>
      </dl>
      <Link
        href="/app/projects"
        className="mt-8 mr-4 inline-block rounded-lg bg-teal-400 px-5 py-3 font-semibold text-slate-950"
      >
        Projects
      </Link>
      <Link
        href="/app/tracked-sites"
        className="mt-8 mr-4 inline-block rounded-lg border border-teal-500 px-5 py-3 text-teal-200"
      >
        Tracked Sites
      </Link>
      <button
        onClick={() => {
          void logout();
        }}
        disabled={loggingOut}
        className="mt-8 rounded-lg border border-slate-500 px-5 py-3 hover:bg-slate-800 disabled:opacity-50"
      >
        {loggingOut ? "Logging out…" : "Logout"}
      </button>
      {logoutError && (
        <p role="alert" className="mt-4 text-red-300">
          {logoutError}
        </p>
      )}
    </main>
  );
}
