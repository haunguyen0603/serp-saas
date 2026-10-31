"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Alert, Button, Input, Skeleton } from "@/design-system/ui";
import { useAuth } from "@/features/auth/auth-provider";
import {
  alertKeys,
  getPreferences,
  savePreferences,
  type AlertPreferences,
} from "./api";

const toggles = [
  ["enabled", "Enable ranking alerts"],
  ["notify_entered_top10", "Entered Top 10"],
  ["notify_left_top10", "Left Top 10"],
  ["notify_improvement", "Rank improved"],
  ["notify_decline", "Rank declined"],
  ["email_enabled", "Also email my verified account"],
] as const;
export function RankingAlertPreferences({ projectId }: { projectId: string }) {
  const auth = useAuth();
  const client = useQueryClient();
  const saveStatus = useRef<HTMLParagraphElement>(null);
  const [saved, setSaved] = useState(false);
  const key = [...alertKeys(auth.user?.id), "preferences", projectId];
  const query = useQuery({
    queryKey: key,
    queryFn: () => getPreferences(auth.request, projectId),
    enabled: auth.isAuthenticated && !auth.requiresEmailVerification,
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: (data: AlertPreferences) =>
      savePreferences(auth.request, projectId, data),
    onMutate: () => setSaved(false),
    onSuccess: (data) => {
      client.setQueryData(key, data);
      setSaved(true);
    },
  });
  useEffect(() => {
    if (saved) saveStatus.current?.focus({ preventScroll: true });
  }, [saved]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      ...Object.fromEntries(toggles.map(([name]) => [name, form.has(name)])),
      movement_threshold: Number(form.get("movement_threshold")),
    } as AlertPreferences);
  }
  return (
    <section
      id="ranking-alert-preferences"
      className="mt-12 border-t border-border pt-10"
    >
      <h2 className="text-2xl font-semibold">Ranking alert preferences</h2>
      <p className="mt-2 text-sm text-secondary">
        Alerts follow completed checks of the Top 10. Changes apply to future
        evaluations; rank tracking continues when alerts are off.
      </p>
      {query.isPending ? (
        <Skeleton label="Loading alert preferences…" />
      ) : query.isError ? (
        <Alert>
          Alert preferences could not be loaded.{" "}
          <Button onClick={() => void query.refetch()}>Retry</Button>
        </Alert>
      ) : (
        <form
          key={JSON.stringify(query.data)}
          aria-label="Ranking alert preferences"
          onSubmit={submit}
          className="mt-5 grid max-w-xl gap-4"
        >
          {toggles.map(([name, label]) => (
            <label key={name} className="flex items-start gap-3">
              <input
                type="checkbox"
                name={name}
                defaultChecked={query.data[name]}
                className="mt-1 h-4 w-4 shrink-0"
              />
              {label}
            </label>
          ))}
          <label>
            Minimum movement (positions)
            <Input
              name="movement_threshold"
              type="number"
              min={1}
              max={10}
              step={1}
              defaultValue={query.data.movement_threshold}
              required
            />
          </label>
          <p className="text-sm text-secondary">
            Email is off by default and only goes to your verified account.{" "}
            {query.data.email_available
              ? "Email delivery is available."
              : "Email delivery is currently unavailable. Your preference can still be saved."}
          </p>
          {mutation.isError && (
            <Alert>
              Alert preferences could not be saved. Please try again.
            </Alert>
          )}
          {saved && (
            <p role="status" ref={saveStatus} tabIndex={-1}>
              Alert preferences saved.
            </p>
          )}
          <div>
            <Button variant="primary" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Save Alert Preferences"}
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
