"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "./auth-provider";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/design-system/ui";
import { siteHref } from "@/lib/site";

const inputStyle = "ui-input auth-input";

export function AuthForm({ mode }: { mode: "signup" | "login" }) {
  const signup = mode === "signup";
  const auth = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (auth.isAuthenticated)
      router.replace(auth.requiresEmailVerification ? "/verify-email" : "/app");
  }, [auth.isAuthenticated, auth.requiresEmailVerification, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setError(null);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "")
      .trim()
      .toLowerCase();
    const password = String(form.get("password") ?? "");
    if (password.length < 10 || password.length > 128) {
      setError("Password must contain 10 to 128 characters.");
      return;
    }
    if (signup && password !== form.get("confirmPassword")) {
      setError("Passwords do not match.");
      return;
    }
    if (signup && form.get("acceptTerms") !== "on") {
      setError("You must accept the Terms of Service.");
      return;
    }
    setSubmitting(true);
    try {
      const response = signup
        ? await auth.register({ email, password, accept_terms: true })
        : await auth.login({ email, password });
      router.replace(
        response.email_verification_required && !response.user.email_verified
          ? "/verify-email"
          : "/app",
      );
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? failure.message
          : "The service is unavailable. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-md">
      <h1 className="mb-8 text-3xl font-semibold">
        {signup ? "Create your account" : "Log in"}
      </h1>
      <form
        onSubmit={(event) => {
          void submit(event);
        }}
        className="space-y-5"
        aria-label={signup ? "Sign up" : "Log in"}
      >
        <label className="block">
          Email
          <input
            name="email"
            type="email"
            autoComplete="email"
            maxLength={320}
            required
            className={inputStyle}
          />
        </label>
        <label className="block">
          Password
          <input
            name="password"
            type="password"
            autoComplete={signup ? "new-password" : "current-password"}
            minLength={10}
            maxLength={128}
            required
            className={inputStyle}
          />
        </label>
        {signup && (
          <>
            <p className="text-sm text-slate-400">Use 10 to 128 characters.</p>
            <label className="block">
              Confirm Password
              <input
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                minLength={10}
                maxLength={128}
                required
                className={inputStyle}
              />
            </label>
            <label className="flex items-start gap-3">
              <input
                name="acceptTerms"
                type="checkbox"
                required
                className="ui-checkbox"
              />
              <span>
                I accept the{" "}
                <Link
                  href={siteHref("/terms")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ui-text-link"
                >
                  Terms of Service
                  <span className="sr-only"> (opens in a new tab)</span>
                </Link>
              </span>
            </label>
            <p className="text-sm text-secondary">
              Learn how we handle your information in our{" "}
              <Link
                href={siteHref("/privacy")}
                target="_blank"
                rel="noopener noreferrer"
                className="ui-text-link"
              >
                Privacy Policy
                <span className="sr-only"> (opens in a new tab)</span>
              </Link>
              .
            </p>
          </>
        )}
        {error && (
          <p
            role="alert"
            className="rounded-lg border border-red-400/30 p-3 text-red-300"
          >
            {error}
          </p>
        )}
        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={submitting || auth.isLoading || auth.isAuthenticated}
          className="w-full"
        >
          {submitting ? "Please wait…" : signup ? "Create Account" : "Log in"}
        </Button>
        {auth.isLoading && (
          <p role="status" className="text-sm text-slate-400">
            Checking your session…
          </p>
        )}
      </form>
      <p className="mt-6 text-sm text-secondary">
        {signup ? "Already have an account?" : "Don't have an account?"}{" "}
        <Link className="ui-text-link" href={signup ? "/login" : "/signup"}>
          {signup ? "Log in" : "Create account"}
        </Link>
      </p>
    </main>
  );
}
