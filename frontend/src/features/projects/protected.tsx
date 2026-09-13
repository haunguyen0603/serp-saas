"use client";
import { Alert, Button } from "@/design-system/ui";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/features/auth/auth-provider";

export function useProtectedAuth() {
  const auth = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (auth.status === "anonymous") router.replace("/login");
  }, [auth.status, router]);
  return auth;
}

export function ProtectedStatus({
  status,
  error,
  retry,
}: {
  status: "loading" | "anonymous" | "error";
  error: string | null;
  retry: () => void;
}) {
  if (status === "error")
    return (
      <main>
        <h1 className="text-3xl">Session unavailable</h1>
        <Alert className="my-5 text-danger">{error}</Alert>
        <Button onClick={retry}>Retry</Button>
      </main>
    );
  return (
    <main>
      <p role="status">
        {status === "loading" ? "Restoring session…" : "Redirecting to login…"}
      </p>
    </main>
  );
}
