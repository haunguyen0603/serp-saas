"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { requestJson } from "@/lib/api/client";
import type { Plan } from "@/features/billing/types";
import { money, panel } from "@/features/billing/billing-page";
export default function PricingPage() {
  const plans = useQuery({
    queryKey: ["plans"],
    queryFn: () => requestJson<Plan[]>("/api/v1/billing/plans"),
  });
  return (
    <main className="space-y-6">
      <Link href="/settings/billing">← Billing &amp; Usage</Link>
      <h1 className="text-3xl">Plans and pricing</h1>
      {plans.isError && <p role="alert">{plans.error.message}</p>}
      {plans.isPending && <p role="status">Loading Plans…</p>}
      {["desktop", "mobile"].map((device) => (
        <section key={device} className="space-y-4">
          <h2 className="text-2xl capitalize">{device} Rank Tracking</h2>
          <div className="grid gap-4 lg:grid-cols-3">
            {plans.data
              ?.filter((plan) => plan.device_scope === device)
              .map((plan) => (
                <article className={panel} key={plan.code}>
                  <h3 className="text-xl">{plan.name}</h3>
                  <p>{money(plan)} / month</p>
                  <p>
                    {plan.max_projects} Projects · {plan.max_keywords} Keywords
                  </p>
                  <p>{plan.monthly_keyword_checks} monthly checks</p>
                  <p>Schedules: {plan.max_scheduled_frequency}</p>
                  <p>
                    {plan.price_monthly_minor_units
                      ? "Contact your administrator for bank-transfer instructions."
                      : "Included with your account."}
                  </p>
                </article>
              ))}
          </div>
        </section>
      ))}
    </main>
  );
}
