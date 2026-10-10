"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/design-system/ui";
import { ApiError } from "@/lib/api/client";

export function PasswordForm({
  currentPassword = false,
  onSubmit,
  submitLabel,
}: {
  currentPassword?: boolean;
  onSubmit: (password: string, current: string) => Promise<void>;
  submitLabel: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const element = event.currentTarget;
    const form = new FormData(element);
    const password = String(form.get("newPassword") ?? "");
    setError(null);
    if (password.length < 10 || password.length > 128) {
      setError("Password must contain 10 to 128 characters.");
      return;
    }
    if (password !== form.get("confirmPassword")) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await onSubmit(password, String(form.get("currentPassword") ?? ""));
      element.reset();
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
    <form
      aria-label={submitLabel}
      onSubmit={(event) => void submit(event)}
      className="space-y-5"
    >
      {currentPassword && (
        <label className="block">
          Current Password
          <input
            name="currentPassword"
            type="password"
            autoComplete="current-password"
            maxLength={128}
            required
            className="ui-input auth-input"
          />
        </label>
      )}
      <label className="block">
        New Password
        <input
          name="newPassword"
          type="password"
          autoComplete="new-password"
          minLength={10}
          maxLength={128}
          required
          className="ui-input auth-input"
          aria-describedby="password-help"
        />
      </label>
      <p id="password-help" className="text-sm text-secondary">
        Use 10 to 128 characters.
      </p>
      <label className="block">
        Confirm New Password
        <input
          name="confirmPassword"
          type="password"
          autoComplete="new-password"
          minLength={10}
          maxLength={128}
          required
          className="ui-input auth-input"
        />
      </label>
      {error && (
        <p role="alert" className="text-danger">
          {error}
        </p>
      )}
      <Button type="submit" variant="primary" size="lg" disabled={busy}>
        {busy ? "Saving…" : submitLabel}
      </Button>
    </form>
  );
}
