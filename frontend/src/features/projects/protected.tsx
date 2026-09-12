"use client";

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
        <p role="alert" className="my-5 text-red-300">
          {error}
        </p>
        <button className="text-teal-300 underline" onClick={retry}>
          Retry
        </button>
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
