"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/design-system/ui";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "./auth-provider";
import { verifyEmail } from "./api";
import type { VerificationStatus } from "./types";

function message(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "The service is unavailable. Please try again.";
}

export function EmailVerification() {
  const auth = useAuth();
  const refresh = auth.refresh;
  const [token, setToken] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [confirmedUserId, setConfirmedUserId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deadline, setDeadline] = useState(0);
  const [now, setNow] = useState(0);
  const state = useQuery({
    queryKey: ["email-verification", auth.user?.id],
    queryFn: () =>
      auth.request<VerificationStatus>("/api/v1/auth/email-verification"),
    enabled: auth.isAuthenticated && !auth.user?.email_verified,
    retry: false,
    refetchInterval: (query) => (query.state.data?.verified ? false : 5000),
  });

  useEffect(() => {
    const readFragment = () => {
      const raw = new URLSearchParams(window.location.hash.slice(1)).get(
        "token",
      );
      if (raw) {
        setToken(raw);
        // Fragments never reach the web server; remove it from the current URL too.
        window.history.replaceState(
          window.history.state,
          "",
          window.location.pathname,
        );
      }
    };
    const timer = window.setTimeout(readFragment, 0);
    window.addEventListener("hashchange", readFragment);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("hashchange", readFragment);
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (state.data?.verified && !auth.user?.email_verified)
      void refresh().catch(() =>
        setError("Email verified. Refresh your session to continue."),
      );
  }, [state.data?.verified, auth.user?.email_verified, refresh]);

  const retryDeadline = state.data
    ? state.dataUpdatedAt + state.data.retry_after_seconds * 1000
    : 0;
  const wait = Math.max(
    0,
    Math.ceil(
      (Math.max(deadline, retryDeadline) - (now || state.dataUpdatedAt)) / 1000,
    ),
  );

  async function confirm() {
    if (!token || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await verifyEmail(token);
      setConfirmedUserId(result.user_id);
      setToken(null);
      setConfirmed(true);
      if (auth.isAuthenticated) {
        // Verification does not create a login session or switch another account.
        try {
          await auth.refresh();
        } catch {
          setError(
            "Email verified. Log in again if your session could not be restored.",
          );
        }
      }
    } catch (failure) {
      setError(message(failure));
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    if (busy || wait > 0) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await auth.request<VerificationStatus>(
        "/api/v1/auth/email-verification/resend",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        },
      );
      setDeadline(Date.now() + result.retry_after_seconds * 1000);
      setNow(Date.now());
      setNotice(
        "Email requested. Check your inbox and spam folder, and use the latest link.",
      );
      await state.refetch();
    } catch (failure) {
      setError(message(failure));
      void state.refetch();
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    setError(null);
    try {
      await auth.logout();
    } catch (failure) {
      setError(message(failure));
    } finally {
      setBusy(false);
    }
  }

  const verified = confirmed || (!token && auth.user?.email_verified);
  const ownVerified =
    auth.user?.email_verified &&
    (!confirmedUserId || confirmedUserId === auth.user.id);
  return (
    <main className="public-main py-12 sm:py-16">
      <article className="mx-auto max-w-md space-y-6">
        <h1 className="text-3xl font-semibold">
          {verified
            ? "Email verified"
            : token
              ? "Confirm your email address"
              : "Verify your email"}
        </h1>
        {verified ? (
          <>
            <p role="status">Your email address has been verified.</p>
            {auth.isAuthenticated && ownVerified ? (
              <Link href="/app" className="ui-link-button">
                Continue to workspace
              </Link>
            ) : auth.isAuthenticated ? (
              <>
                <p>
                  Sign out, then log in with the account whose email you just
                  verified.
                </p>
                <Button onClick={() => void signOut()} disabled={busy}>
                  Sign out
                </Button>
              </>
            ) : (
              <Link href="/login" className="ui-link-button">
                Log in to continue
              </Link>
            )}
          </>
        ) : token ? (
          <>
            <p>
              Select Verify email to confirm the address used for your SERP SaaS
              account. This link can be used once.
            </p>
            <Button onClick={() => void confirm()} disabled={busy}>
              {busy ? "Verifying…" : "Verify email"}
            </Button>
            {error && (
              <p>
                For a new link,{" "}
                <Link
                  className="ui-text-link"
                  href="/verify-email"
                  onClick={() => {
                    setToken(null);
                    setError(null);
                  }}
                >
                  open email verification
                </Link>{" "}
                after logging in to your account.
              </p>
            )}
          </>
        ) : auth.isLoading ? (
          <p role="status">Restoring your session…</p>
        ) : auth.isAuthenticated ? (
          <>
            <p>
              {state.data?.delivery_status === "not_requested"
                ? "Request a verification email for "
                : "Check your inbox for the verification email for "}
              <strong className="break-all">{auth.user?.email}</strong>. Open
              the latest link and select Verify email.
            </p>
            {auth.requiresEmailVerification && (
              <p>Please verify your email before entering the workspace.</p>
            )}
            {state.data?.delivery_status === "failed" && (
              <p role="alert">
                The email could not be delivered. Please request another email
                when the button is available.
              </p>
            )}
            {state.data?.delivery_status === "pending" && (
              <p role="status">
                Email delivery is in progress. If it does not arrive, request
                another email below.
              </p>
            )}
            {state.data?.expires_at &&
              Date.parse(state.data.expires_at) <= now && (
                <p>Your link has expired. Request a new email.</p>
              )}
            {state.isError && <p role="alert">{message(state.error)}</p>}
            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={() => void resend()}
                disabled={busy || wait > 0 || state.isPending}
              >
                {wait > 0
                  ? `Resend email in ${wait}s`
                  : busy
                    ? "Requesting…"
                    : "Resend verification email"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  void auth
                    .refresh()
                    .catch((failure) => setError(message(failure)));
                }}
                disabled={busy}
              >
                I’ve verified my email
              </Button>
            </div>
            <Button
              variant="ghost"
              onClick={() => void signOut()}
              disabled={busy}
            >
              Sign out / use another account
            </Button>
          </>
        ) : auth.status === "error" ? (
          <>
            <p role="alert">{auth.error}</p>
            <Button
              onClick={() => {
                void auth.refresh().catch(() => {});
              }}
            >
              Retry
            </Button>
          </>
        ) : (
          <>
            <p>
              Open the link from your latest verification email, or log in to
              request a new email.
            </p>
            <Link href="/login" className="ui-link-button">
              Log in
            </Link>
          </>
        )}
        {notice && <p role="status">{notice}</p>}
        {error && <p role="alert">{error}</p>}
      </article>
    </main>
  );
}
