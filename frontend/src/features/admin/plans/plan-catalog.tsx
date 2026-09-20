"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Skeleton,
} from "@/design-system/ui";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import type { Plan } from "@/features/billing/types";
import { money } from "@/features/billing/billing-page";

export interface AdminPlan extends Plan {
  updated_at: string;
}
interface PlanChange {
  id: string;
  created_at: string;
  actor_user_id: string | null;
  before: Plan;
  after: Plan;
}
const fields = [
  ["max_projects", "Max projects"],
  ["max_keywords", "Max keywords"],
  ["monthly_keyword_checks", "Monthly checks"],
] as const;

function PlanEditor({ plan }: { plan: AdminPlan }) {
  const auth = useProtectedAuth();
  const client = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [values, setValues] = useState({
    price: (plan.price_monthly_minor_units / 100).toFixed(2),
    max_projects: String(plan.max_projects),
    max_keywords: String(plan.max_keywords),
    monthly_keyword_checks: String(plan.monthly_keyword_checks),
  });
  const [version, setVersion] = useState(plan.updated_at);
  const mutation = useMutation({
    mutationFn: (input: Record<string, string | number>) =>
      auth.request<AdminPlan>(`/api/v1/admin/plans/${plan.code}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),
    onSuccess: async (updated) => {
      setVersion(updated.updated_at);
      setSaved(true);
      client.setQueryData<AdminPlan[]>(
        ["admin-plans", auth.user?.id],
        (plans) =>
          plans?.map((item) => (item.code === updated.code ? updated : item)),
      );
      await Promise.all([
        client.invalidateQueries({ queryKey: ["admin-plan-history"] }),
        client.invalidateQueries({ queryKey: ["public-plans"] }),
        client.invalidateQueries({ queryKey: ["plans"] }),
      ]);
    },
    onError: (failure: Error) => setError(failure.message),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    if (!/^\d+(\.\d{1,2})?$/.test(values.price)) {
      setError("Enter a price with at most two decimal places.");
      return;
    }
    const [whole, fraction = ""] = values.price.split(".");
    const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
    if (!Number.isSafeInteger(cents) || cents > 2147483647) {
      setError("Price is too large.");
      return;
    }
    const limits = Object.fromEntries(
      fields.map(([key]) => [key, Number(values[key])]),
    );
    if (
      fields.some(
        ([key]) => !/^\d+$/.test(values[key]) || limits[key] > 2147483647,
      )
    ) {
      setError("Limits must be whole numbers from 0 to 2147483647.");
      return;
    }
    mutation.mutate({
      expected_updated_at: version,
      price_monthly_minor_units: cents,
      ...limits,
    });
  }

  return (
    <Card>
      <form
        aria-label={`Edit ${plan.name}`}
        onSubmit={submit}
        className="space-y-4"
        onChange={() => {
          setSaved(false);
          setError(null);
        }}
      >
        <h3>{plan.name}</h3>
        <fieldset disabled={mutation.isPending} className="space-y-4">
          <label className="block">
            Monthly price ({plan.currency})
            <Input
              type="number"
              min={plan.code.endsWith("_free") ? "0" : "0.01"}
              max="21474836.47"
              step="0.01"
              required
              value={values.price}
              readOnly={plan.code.endsWith("_free")}
              onChange={(e) => setValues({ ...values, price: e.target.value })}
            />
          </label>
          {plan.code.endsWith("_free") && (
            <p className="text-sm text-secondary">
              Free Plans stay at $0. Their limits can be edited.
            </p>
          )}
          {fields.map(([key, label]) => (
            <label className="block" key={key}>
              {label}
              <Input
                type="number"
                min="0"
                max="2147483647"
                step="1"
                required
                value={values[key]}
                onChange={(e) =>
                  setValues({ ...values, [key]: e.target.value })
                }
              />
            </label>
          ))}
          <p className="text-sm text-secondary">
            {plan.scheduled_checks_enabled
              ? `${plan.max_scheduled_frequency} scheduling`
              : "No scheduled checks"}
          </p>
          <Button variant="primary" type="submit" loading={mutation.isPending}>
            Save {plan.name}
          </Button>
        </fieldset>
        {saved && (
          <p role="status" className="text-sm text-success">
            Saved. New activations will use these terms.
          </p>
        )}
        {error && <Alert>{error}</Alert>}
      </form>
    </Card>
  );
}

export function PlanCatalog() {
  const auth = useProtectedAuth();
  const [revision, setRevision] = useState(0);
  const enabled = auth.isAuthenticated && !!auth.user?.is_platform_admin;
  const plans = useQuery({
    queryKey: ["admin-plans", auth.user?.id],
    queryFn: () => auth.request<AdminPlan[]>("/api/v1/admin/plans"),
    enabled,
    retry: false,
  });
  const history = useQuery({
    queryKey: ["admin-plan-history", auth.user?.id],
    queryFn: () => auth.request<PlanChange[]>("/api/v1/admin/plans/history"),
    enabled,
    retry: false,
  });
  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  if (!auth.user?.is_platform_admin)
    return (
      <main>
        <h1>Administrator access required</h1>
      </main>
    );

  return (
    <main className="space-y-6">
      <PageHeader
        title="Plans & Pricing"
        description="Manage Desktop and Mobile pricing and capacity independently."
      />
      <Card role="note" className="text-secondary">
        Changes update the public Pricing catalog and new subscription
        activations. Existing subscriptions, including Free Plans and
        extensions, keep their saved prices and limits.
      </Card>
      <Button
        disabled={plans.isFetching}
        onClick={async () => {
          const result = await plans.refetch();
          if (result.isSuccess) setRevision((value) => value + 1);
        }}
      >
        Reload catalog (discard edits)
      </Button>
      {plans.isPending && <Skeleton label="Loading Plan catalog…" />}
      {plans.isError && (
        <ErrorState onRetry={() => void plans.refetch()}>
          Plan catalog could not be loaded.
        </ErrorState>
      )}
      {plans.data?.length === 0 && (
        <EmptyState title="No Plans available">
          No active Plans were found.
        </EmptyState>
      )}
      {plans.data &&
        (["desktop", "mobile"] as const).map((device) => (
          <section
            key={device}
            aria-label={`${device} Plans`}
            className="space-y-4"
          >
            <h2>{device === "desktop" ? "Desktop" : "Mobile"} Plans</h2>
            <div className="grid gap-4 xl:grid-cols-3">
              {plans.data
                .filter((plan) => plan.device_scope === device)
                .map((plan) => (
                  <PlanEditor key={`${plan.code}:${revision}`} plan={plan} />
                ))}
            </div>
          </section>
        ))}
      <Card aria-label="Plan change history" className="space-y-4">
        <h2>Recent changes</h2>
        <p className="text-sm text-secondary">
          The latest 20 catalog updates, including the administrator and
          previous values.
        </p>
        {history.isPending && <Skeleton label="Loading Plan changes…" />}
        {history.isError && (
          <ErrorState onRetry={() => void history.refetch()}>
            Change history could not be loaded.
          </ErrorState>
        )}
        {history.data?.length === 0 && (
          <p className="text-secondary">No Plan changes yet.</p>
        )}
        {history.data?.map((change) => (
          <details key={change.id} className="border-t border-border pt-4">
            <summary>
              {change.after.name} ·{" "}
              {new Date(change.created_at).toLocaleString()}
            </summary>
            <p className="text-sm text-secondary break-all">
              Administrator: {change.actor_user_id ?? "Deleted account"}
            </p>
            <p>
              Monthly price: {money(change.before)} → {money(change.after)}
            </p>
            {fields.map(([key, label]) => (
              <p key={key}>
                {label}: {change.before[key]} → {change.after[key]}
              </p>
            ))}
          </details>
        ))}
      </Card>
    </main>
  );
}
