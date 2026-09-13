"use client";
import { Alert, Skeleton, Card, StatusBadge } from "@/design-system/ui";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useProtectedAuth } from "@/features/projects/protected";
import type { BillingSummary, DeviceBilling, Plan } from "./types";

export const money = (plan: Plan) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: plan.currency,
  }).format(plan.price_monthly_minor_units / 100);
export const date = (value: string) => new Date(value).toLocaleString();
// Legacy exports preserve the existing public pricing page; customer controls use UI primitives.
export const panel =
  "rounded-xl border border-slate-700 bg-slate-900/50 p-6 space-y-3";
export const control = "";
export const button = "";

export function DeviceCard({ device }: { device: DeviceBilling }) {
  const { plan, usage } = device;
  return (
    <Card className="billing-card" aria-label={device.device_scope}>
      <div className="overview-section-heading">
        <h2>{plan.name}</h2>
        <StatusBadge status={device.status} />
      </div>
      <p>
        {money(plan)} / month · {device.status}
      </p>
      <p>
        Subscription: {date(device.period_start)} →{" "}
        {device.period_end ? date(device.period_end) : "Free, ongoing"}
      </p>
      <dl className="billing-metrics">
        <div>
          <dt>Projects</dt>
          <dd>
            {device.projects_used} / {plan.max_projects}
          </dd>
          <progress
            max={Math.max(1, plan.max_projects)}
            value={Math.min(device.projects_used, plan.max_projects)}
            aria-label={`${device.device_scope} Projects usage`}
          />
        </div>
        <div>
          <dt>Keywords</dt>
          <dd>
            {device.keywords_used} / {plan.max_keywords}
          </dd>
          <progress
            max={Math.max(1, plan.max_keywords)}
            value={Math.min(device.keywords_used, plan.max_keywords)}
            aria-label={`${device.device_scope} Keywords usage`}
          />
        </div>
        <div>
          <dt>Monthly checks</dt>
          <dd>
            {usage.used} / {usage.limit}
          </dd>
          <progress
            max={Math.max(1, usage.limit)}
            value={Math.min(usage.used + usage.reserved, usage.limit)}
            aria-label={`${device.device_scope} Monthly checks usage`}
          />
          <p className="ui-caption">
            {usage.limit
              ? Math.min(
                  100,
                  Math.round(
                    ((usage.used + usage.reserved) / usage.limit) * 100,
                  ),
                )
              : 0}
            % used or reserved
          </p>
        </div>
        <div>
          <dt>Reserved checks</dt>
          <dd>{usage.reserved}</dd>
        </div>
        <div>
          <dt>Remaining checks</dt>
          <dd>{usage.remaining}</dd>
        </div>
        <div>
          <dt>Next reset</dt>
          <dd>{date(usage.period_end)}</dd>
        </div>
        <div>
          <dt>Scheduled checks</dt>
          <dd>
            {plan.scheduled_checks_enabled
              ? `Up to ${plan.max_scheduled_frequency}`
              : "Not included"}
          </dd>
        </div>
      </dl>
      {device.over_limit && (
        <Alert className="text-warning">
          Resource limit exceeded. Your data remains available. Archive Projects
          or pause Keywords before adding more.
        </Alert>
      )}
    </Card>
  );
}
export function BillingPage() {
  const auth = useProtectedAuth();
  const billing = useQuery({
    queryKey: ["billing", auth.user?.id],
    queryFn: () => auth.request<BillingSummary>("/api/v1/billing/me"),
    enabled: auth.isAuthenticated,
    refetchInterval: 10000,
  });
  return (
    <main className="space-y-6">
      <Link href="/app">← Account</Link>
      <div>
        <h1>Billing &amp; Usage</h1>
        <p className="text-secondary mt-2">
          Your Plans, allowances and next reset — independently for each device.
        </p>
      </div>
      {billing.isError && <Alert>{billing.error.message}</Alert>}
      {!billing.data && !billing.isError && (
        <Skeleton label="Loading billing…" />
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        {billing.data?.devices.map((device) => (
          <DeviceCard key={device.device_scope} device={device} />
        ))}
      </div>
      <Card>
        <h2 className="mb-2">Need more room to grow?</h2>
        <p>
          To change your Plan, contact your administrator for bank-transfer
          instructions. Paid Plans are activated after payment is confirmed.
        </p>
      </Card>
      <Link className="text-brand underline" href="/pricing">
        View Plans and prices
      </Link>
    </main>
  );
}
