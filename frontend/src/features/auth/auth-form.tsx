"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "./auth-provider";
import { ApiError } from "@/lib/api/client";

const inputStyle =
  "mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3 text-slate-100 focus:outline-2 focus:outline-teal-400";

export function AuthForm({ mode }: { mode: "signup" | "login" }) {
  const signup = mode === "signup";
  const auth = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (auth.isAuthenticated) router.replace("/app");
  }, [auth.isAuthenticated, router]);

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
      if (signup) await auth.register({ email, password, accept_terms: true });
      else await auth.login({ email, password });
      router.replace("/app");
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
      <p className="mb-3 text-sm uppercase tracking-widest text-teal-400">
        SERP SaaS
      </p>
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
                className="mt-1 accent-teal-400"
              />
              I accept the Terms of Service
            </label>
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
        <button
          type="submit"
          disabled={submitting || auth.isLoading || auth.isAuthenticated}
          className="w-full rounded-lg bg-teal-400 px-4 py-3 font-semibold text-slate-950 hover:bg-teal-300 disabled:opacity-50"
        >
          {submitting ? "Please wait…" : signup ? "Create Account" : "Log in"}
        </button>
        {auth.isLoading && (
          <p role="status" className="text-sm text-slate-400">
            Checking your session…
          </p>
        )}
      </form>
      <p className="mt-6 text-slate-400">
        {signup ? "Already have an account?" : "Don't have an account?"}{" "}
        <Link
          className="text-teal-300 underline"
          href={signup ? "/login" : "/signup"}
        >
          {signup ? "Log in" : "Create account"}
        </Link>
      </p>
    </main>
  );
}
