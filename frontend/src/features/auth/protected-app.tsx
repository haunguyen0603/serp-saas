"use client";

import { Button, Card, StatusBadge, Skeleton } from "@/design-system/ui";
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
        <Button
          onClick={() => {
            void auth.refresh().catch(() => {});
          }}
          className="text-brand underline"
        >
          Retry
        </Button>
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
        <Skeleton label="Loading your account…" />
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
        <Button
          onClick={() => {
            void me.refetch();
          }}
          className="mr-6 text-brand underline"
        >
          Retry
        </Button>
        <Button
          onClick={() => {
            void logout();
          }}
          disabled={loggingOut}
        >
          Logout
        </Button>
        {logoutError && <p role="alert">{logoutError}</p>}
      </main>
    );
  return (
    <main>
      <h1 className="mb-8">Account settings</h1>
      <Card>
        <dl className="space-y-6">
          <div>
            <dt className="text-secondary">Signed in as:</dt>
            <dd className="mt-2 text-xl">{me.data.email}</dd>
          </div>
          <div>
            <dt className="text-secondary">Account status:</dt>
            <dd className="mt-2 text-brand">
              <StatusBadge status={me.data.status} />
            </dd>
          </div>
        </dl>
      </Card>
      <Link
        href="/app/projects"
        className="mt-8 mr-4 inline-block rounded-lg bg-brand px-5 py-3 font-semibold text-white"
      >
        Projects
      </Link>
      <Link
        href="/app/tracked-sites"
        className="mt-8 mr-4 inline-block rounded-lg border border-brand px-5 py-3 text-brand"
      >
        Tracked Sites
      </Link>
      <Link
        href="/settings/billing"
        className="mt-8 mr-4 inline-block text-brand underline"
      >
        Billing &amp; Usage
      </Link>
      {me.data.is_platform_admin && (
        <Link
          href="/admin/customers"
          className="mt-8 mr-4 inline-block text-brand underline"
        >
          Customers
        </Link>
      )}
      <Button
        onClick={() => {
          void logout();
        }}
        disabled={loggingOut}
        className="mt-8 rounded-lg border border-border px-5 py-3 hover:bg-surface-muted disabled:opacity-50"
      >
        {loggingOut ? "Logging out…" : "Logout"}
      </Button>
      {logoutError && (
        <p role="alert" className="mt-4 text-danger">
          {logoutError}
        </p>
      )}
    </main>
  );
}
