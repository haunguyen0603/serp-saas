"use client";
import {
  Alert,
  ConfirmDialog,
  Button,
  Input,
  Select,
  Textarea,
  Toast,
} from "@/design-system/ui";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useProtectedAuth } from "@/features/projects/protected";
import {
  DeviceCard,
  button,
  control,
  date,
  money,
} from "@/features/billing/billing-page";
import type {
  BillingSummary,
  Plan,
  Subscription,
  UsageHistory,
} from "@/features/billing/types";

export function CustomerBilling({ userId }: { userId: string }) {
  const auth = useProtectedAuth();
  const cache = useQueryClient();
  const root = `/api/v1/admin/customers/${userId}`;
  const enabled = auth.isAuthenticated && !!auth.user?.is_platform_admin;
  const billing = useQuery({
    queryKey: ["admin-billing", userId],
    queryFn: () => auth.request<BillingSummary>(`${root}/billing`),
    enabled,
    retry: false,
  });
  const plans = useQuery({
    queryKey: ["plans"],
    queryFn: () => auth.request<Plan[]>("/api/v1/billing/plans"),
    enabled,
  });
  const history = useQuery({
    queryKey: ["admin-history", userId],
    queryFn: () => auth.request<Subscription[]>(`${root}/subscriptions`),
    enabled,
  });
  const usage = useQuery({
    queryKey: ["admin-usage", userId],
    queryFn: () => auth.request<UsageHistory>(`${root}/usage`),
    enabled,
  });
  const [replacement, setReplacement] = useState<object | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [planCode, setPlanCode] = useState("desktop_starter");
  const selected = plans.data?.find((plan) => plan.code === planCode);
  async function mutate(path: string, body: object) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await auth.request(`${root}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await Promise.all(
        [
          "admin-billing",
          "admin-history",
          "admin-usage",
          "admin-customers",
          "billing",
        ].map((key) => cache.invalidateQueries({ queryKey: [key] })),
      );
      setMessage("Billing updated.");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }
  function activate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const body = {
      plan_code: planCode,
      period_start: data.get("period_start")
        ? new Date(String(data.get("period_start"))).toISOString()
        : new Date().toISOString(),
      period_end: new Date(String(data.get("period_end"))).toISOString(),
      payment_method: selected?.price_monthly_minor_units
        ? "manual_bank_transfer"
        : null,
      payment_reference: selected?.price_monthly_minor_units
        ? data.get("reference") || null
        : null,
      note: data.get("note") || null,
      replace_existing: data.get("replace") === "on",
    };
    if (body.replace_existing) setReplacement(body);
    else void mutate("/subscriptions", body);
  }
  if (auth.isAuthenticated && !auth.user?.is_platform_admin)
    return (
      <main>
        <h1>Administrator access required</h1>
      </main>
    );
  return (
    <main className="space-y-6">
      <ConfirmDialog
        open={!!replacement}
        onClose={() => setReplacement(null)}
        title="Replace subscription"
        description="This ends the current subscription in this device scope. Lower limits may disable incompatible schedules. Subscription history will be retained."
        onConfirm={() => {
          if (replacement) void mutate("/subscriptions", replacement);
          setReplacement(null);
        }}
      />
      <Link href="/admin/customers">← Customers</Link>
      <h1 className="text-3xl">Customer billing: {billing.data?.email}</h1>
      {(error || billing.isError || history.isError || usage.isError) && (
        <Alert className="text-danger">
          {error ||
            billing.error?.message ||
            history.error?.message ||
            usage.error?.message}
        </Alert>
      )}
      {message && <Toast key={message}>{message}</Toast>}
      <div className="grid gap-6 lg:grid-cols-2">
        {billing.data?.devices.map((device) => (
          <div key={device.device_scope} className="space-y-3">
            <DeviceCard device={device} />
            {device.period_end && (
              <form
                className="ui-card space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  void mutate(
                    `/subscriptions/${device.subscription_id}/extend`,
                    {
                      period_end: new Date(
                        String(data.get("end")),
                      ).toISOString(),
                    },
                  );
                }}
              >
                <label>
                  Extend {device.device_scope} until
                  <Input
                    className={control}
                    type="datetime-local"
                    name="end"
                    required
                  />
                </label>
                <Button variant="primary" className={button} disabled={busy}>
                  Extend {device.device_scope}
                </Button>
              </form>
            )}
            {device.period_end && (
              <Button
                className={button}
                disabled={busy}
                variant="danger"
                confirmation="Cancel this subscription now? This device returns to Free and incompatible schedules stop."
                onClick={() => {
                  void mutate(
                    `/subscriptions/${device.subscription_id}/cancel`,
                    {},
                  );
                }}
              >
                Cancel {device.device_scope} subscription
              </Button>
            )}
          </div>
        ))}
      </div>
      <form className="ui-card space-y-3" onSubmit={activate}>
        <h2 className="text-xl">Activate / Change Plan</h2>
        <label>
          Plan
          <Select
            className={control}
            value={planCode}
            onChange={(e) => setPlanCode(e.target.value)}
          >
            {plans.data?.map((plan) => (
              <option key={plan.code} value={plan.code}>
                {plan.name} — {money(plan)} / month
              </option>
            ))}
          </Select>
        </label>
        <label>
          Period start (leave empty for immediate)
          <Input
            className={control}
            type="datetime-local"
            name="period_start"
          />
        </label>
        <label>
          Period end
          <Input
            className={control}
            type="datetime-local"
            name="period_end"
            required
          />
        </label>
        <label className="block">
          <Input type="checkbox" name="replace" /> Replace current Plan
          immediately (fresh monthly quota)
        </label>
        <p>
          For a scheduled downgrade, set the start to the current subscription
          end. No automatic proration.
        </p>
        {!!selected?.price_monthly_minor_units && (
          <>
            <p>
              Payment method: manual bank transfer. Confirm payment externally
              before activating.
            </p>
            <label>
              Payment reference
              <Input className={control} name="reference" maxLength={200} />
            </label>
          </>
        )}
        <label>
          Internal note
          <Textarea className={control} name="note" maxLength={2000} />
        </label>
        <Button
          variant="primary"
          className={button}
          disabled={busy || !selected}
        >
          Activate Plan
        </Button>
      </form>
      <form
        className="ui-card space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          void mutate("/usage-adjustments", {
            device_scope: data.get("device"),
            amount: Number(data.get("amount")),
            note: data.get("note"),
          });
        }}
      >
        <h2 className="text-xl">Adjust current usage allowance</h2>
        <label>
          Device
          <Select className={control} name="device">
            <option value="desktop">Desktop</option>
            <option value="mobile">Mobile</option>
          </Select>
        </label>
        <label>
          Checks to add or subtract
          <Input
            className={control}
            type="number"
            name="amount"
            min={-10000000}
            max={10000000}
            required
          />
        </label>
        <label>
          Adjustment reason
          <Input className={control} name="note" required maxLength={2000} />
        </label>
        <Button variant="primary" className={button} disabled={busy}>
          Adjust usage
        </Button>
      </form>
      <section className="ui-card space-y-3">
        <h2 className="text-xl">Subscription history</h2>
        {history.data?.map((sub) => (
          <article key={sub.id} className="border-t border-border py-3">
            <h3>
              {sub.snapshot.name} · {sub.status} · {money(sub.snapshot)} / month
            </h3>
            <p>
              {date(sub.period_start)} → {date(sub.period_end)}
            </p>
            <p>
              {sub.payment_method} · Reference: {sub.payment_reference || "—"}
            </p>
            <p>Internal note: {sub.payment_note || "—"}</p>
            {sub.status === "scheduled" && (
              <Button
                className={button}
                disabled={busy}
                variant="danger"
                confirmation="Cancel this scheduled Plan? It will no longer activate on its start date."
                onClick={() => {
                  void mutate(`/subscriptions/${sub.id}/cancel`, {});
                }}
              >
                Cancel scheduled {sub.device_scope} Plan
              </Button>
            )}
          </article>
        ))}
      </section>
      <section className="ui-card space-y-3">
        <h2 className="text-xl">Usage events</h2>
        {usage.data?.events.map((event) => (
          <p key={event.id}>
            {date(event.created_at)} · {event.device_scope} · {event.event_type}
            : {event.amount}
          </p>
        ))}
      </section>
      <section className="ui-card space-y-3">
        <h2 className="text-xl">Billing audit</h2>
        {usage.data?.audit.map((event) => (
          <p key={event.id}>
            {date(event.created_at)} · {event.device_scope} · {event.event_type}{" "}
            · Actor: {event.actor_user_id || "System"} ·{" "}
            {JSON.stringify(event.safe_metadata)}
          </p>
        ))}
      </section>
    </main>
  );
}
