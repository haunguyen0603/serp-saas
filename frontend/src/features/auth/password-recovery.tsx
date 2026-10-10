"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/design-system/ui";
import { ApiError } from "@/lib/api/client";
import { forgotPassword, resetPassword } from "./api";
import { PasswordForm } from "./password-form";
import { useAuth } from "./auth-provider";

export function ForgotPassword() {
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const email = String(new FormData(event.currentTarget).get("email") ?? "")
      .trim()
      .toLowerCase();
    setBusy(true);
    setSent(false);
    setError(null);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? failure.message
          : "The service is unavailable. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-main space-y-6">
      <h1 className="text-3xl font-semibold">Forgot password?</h1>
      <p>Enter your account email to request a password reset link.</p>
      <form
        aria-label="Request password reset"
        onSubmit={(event) => void submit(event)}
        className="space-y-5"
      >
        <label className="block">
          Email
          <input
            name="email"
            type="email"
            autoComplete="email"
            maxLength={320}
            required
            className="ui-input auth-input"
          />
        </label>
        {error && (
          <p role="alert" className="text-danger">
            {error}
          </p>
        )}
        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={busy}
          className="w-full"
        >
          {busy ? "Sending…" : "Send reset link"}
        </Button>
      </form>
      {sent && (
        <p role="status">
          If an active account exists for this email, you’ll receive a reset
          link. Check your inbox and spam folder. Use the latest link; wait a
          minute before requesting another.
        </p>
      )}
      <p>
        <Link href="/login" className="ui-text-link">
          Back to log in
        </Link>
      </p>
    </main>
  );
}

export function ResetPassword() {
  const auth = useAuth();
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [done, setDone] = useState(false);
  useEffect(() => {
    const read = () => {
      const raw = new URLSearchParams(window.location.hash.slice(1)).get(
        "token",
      );
      if (raw) {
        setToken(raw);
        setDone(false);
        window.history.replaceState(
          window.history.state,
          "",
          window.location.pathname,
        );
      }
      setReady(true);
    };
    const timer = window.setTimeout(read, 0);
    window.addEventListener("hashchange", read);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("hashchange", read);
    };
  }, []);
  return (
    <main className="auth-main space-y-6">
      <h1 className="text-3xl font-semibold">
        {done ? "Password reset" : "Reset password"}
      </h1>
      {!ready ? (
        <p role="status">Loading reset link…</p>
      ) : done ? (
        <>
          <p role="status">
            Your password has been reset. Log in with your new password.
            Previous sessions have been signed out.
          </p>
          <Link href="/login" className="ui-link-button">
            Log in
          </Link>
        </>
      ) : token ? (
        <>
          <p>Choose a new password for your account.</p>
          <PasswordForm
            submitLabel="Reset password"
            onSubmit={async (password) => {
              await resetPassword(token, password);
              auth.clearSession();
              setToken(null);
              setDone(true);
            }}
          />
        </>
      ) : (
        <p>Open the link from your latest password reset email.</p>
      )}
      {!done && (
        <p>
          <Link href="/forgot-password" className="ui-text-link">
            Request a new reset link
          </Link>
        </p>
      )}
    </main>
  );
}
