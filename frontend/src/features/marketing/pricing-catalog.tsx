"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge, Card, ErrorState, Skeleton } from "@/design-system/ui";
import { useAuth } from "@/features/auth/auth-provider";
import type { Plan } from "@/features/billing/types";
import { requestJson } from "@/lib/api/client";

const tierOrder = ["free", "starter", "pro"];
const tierCopy: Record<string, string> = {
  free: "Try the workflow with a small keyword set.",
  starter: "For freelancers, small sites and focused SEO teams.",
  pro: "For agencies and teams with higher tracking volume.",
};

export function groupPlans(plans: Plan[]) {
  return (["desktop", "mobile"] as const).map((device) => ({
    device,
    plans: plans
      .filter((plan) => plan.device_scope === device)
      .sort(
        (a, b) =>
          tierOrder.indexOf(a.code.split("_").at(-1) ?? "") -
          tierOrder.indexOf(b.code.split("_").at(-1) ?? ""),
      ),
  }));
}

function planPrice(plan: Plan) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: plan.currency,
    maximumFractionDigits: 0,
  }).format(plan.price_monthly_minor_units / 100);
}

function scheduleText(plan: Plan) {
  if (!plan.scheduled_checks_enabled) return "No scheduled checks";
  return `${plan.max_scheduled_frequency.replace(/^./, (letter) => letter.toUpperCase())} scheduling`;
}

export function PricingCatalog() {
  const auth = useAuth();
  const query = useQuery({
    queryKey: ["public-plans"],
    queryFn: () => requestJson<Plan[]>("/api/v1/billing/plans"),
    staleTime: 60_000,
  });

  return (
    <main className="public-main pricing-main">
      <section className="pricing-hero" aria-labelledby="pricing-title">
        <p className="public-eyebrow">Simple, device-specific Plans</p>
        <h1 id="pricing-title">Choose the capacity your rankings need.</h1>
        <p>
          Desktop and Mobile are independent product scopes. Start with both
          Free Plans, then request activation for the scope that needs more.
        </p>
      </section>

      <div className="manual-payment-note" role="note">
        <strong>Transparent manual activation</strong>
        <span>
          Paid Plans are currently activated manually after bank-transfer
          payment confirmation by an administrator.
        </span>
      </div>

      {query.isPending && <Skeleton label="Loading current Plans…" rows={6} />}
      {query.isError && (
        <ErrorState
          title="Current Plans are unavailable"
          onRetry={() => void query.refetch()}
        >
          We could not load the authoritative Plan catalog. Please try again; no
          fallback prices are being shown.
        </ErrorState>
      )}
      {query.data &&
        groupPlans(query.data).map(({ device, plans }) => (
          <section
            key={device}
            className="pricing-group"
            aria-labelledby={`${device}-plans`}
          >
            <div className="pricing-group-heading">
              <div>
                <p className="public-eyebrow">{device} search results</p>
                <h2 id={`${device}-plans`}>
                  {device === "desktop" ? "Desktop" : "Mobile"} Rank Tracking
                </h2>
              </div>
              <p>
                {device === "desktop"
                  ? "Track rankings as they appear in desktop Google searches."
                  : "Measure the separate mobile search experience and its limits."}
              </p>
            </div>
            <div className="pricing-grid">
              {plans.map((plan) => {
                const tier = plan.code.split("_").at(-1) ?? "";
                const paid = plan.price_monthly_minor_units > 0;
                const href = auth.isAuthenticated
                  ? paid
                    ? "/settings/billing"
                    : "/app"
                  : "/register";
                const label = auth.isAuthenticated
                  ? paid
                    ? "Request Activation"
                    : "Open App"
                  : paid
                    ? "Request Activation"
                    : "Start Free";
                return (
                  <Card
                    key={plan.code}
                    className={`pricing-card${tier === "starter" ? " pricing-card-featured" : ""}`}
                    aria-label={plan.name}
                  >
                    <div className="pricing-card-heading">
                      <h3>{plan.name.replace(/^(Desktop|Mobile) /, "")}</h3>
                      {tier === "starter" && <Badge tone="info">Popular</Badge>}
                    </div>
                    <p className="pricing-audience">{tierCopy[tier]}</p>
                    <p className="pricing-price">
                      <strong>{planPrice(plan)}</strong>
                      <span>/ month</span>
                    </p>
                    <ul className="pricing-limits">
                      <li>
                        <strong>
                          {plan.max_projects.toLocaleString("en-US")}
                        </strong>{" "}
                        {plan.max_projects === 1 ? "Project" : "Projects"}
                      </li>
                      <li>
                        <strong>
                          {plan.max_keywords.toLocaleString("en-US")}
                        </strong>{" "}
                        Keywords
                      </li>
                      <li>
                        <strong>
                          {plan.monthly_keyword_checks.toLocaleString("en-US")}
                        </strong>{" "}
                        monthly checks
                      </li>
                      <li>
                        <strong>{scheduleText(plan)}</strong>
                      </li>
                    </ul>
                    <Link
                      href={href}
                      className={
                        tier === "starter"
                          ? "ui-link-button"
                          : "pricing-card-cta"
                      }
                    >
                      {label}
                    </Link>
                    {paid && (
                      <p className="pricing-manual">
                        Manual bank-transfer activation
                      </p>
                    )}
                  </Card>
                );
              })}
            </div>
          </section>
        ))}

      <section className="pricing-faq" aria-labelledby="faq-title">
        <div className="public-section-heading">
          <p className="public-eyebrow">Plan details</p>
          <h2 id="faq-title">Frequently asked questions</h2>
        </div>
        <div className="faq-list">
          {[
            [
              "What is a keyword check?",
              "One logical keyword check is one customer usage unit.",
            ],
            [
              "Why are Desktop and Mobile Plans separate?",
              "Desktop and Mobile Google results can differ. Their Projects, limits, usage and subscriptions are managed independently.",
            ],
            [
              "When does monthly usage reset?",
              "Free usage follows the calendar month. Paid usage periods follow the active subscription period shown in Billing & Usage.",
            ],
            [
              "Can I use Desktop and Mobile together?",
              "Yes. Every account has both scopes, and a paid Desktop subscription can coexist with a paid or Free Mobile subscription.",
            ],
            [
              "What happens when I reach a limit?",
              "Existing data remains readable, while new Projects, Keywords or checks in that device scope wait until capacity is available.",
            ],
            [
              "Can I upgrade later?",
              "Yes. Create an account and use Billing & Usage to review your current limits and request a manual Plan change.",
            ],
            [
              "How are paid Plans activated?",
              "An administrator activates a paid Plan after confirming the bank transfer.",
            ],
          ].map(([question, answer]) => (
            <details key={question}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="public-final-cta pricing-final-cta">
        <h2>Start with clear limits and room to grow.</h2>
        <p>
          Create an account to use the Free Plans or review manual upgrade
          options.
        </p>
        <Link
          href={auth.isAuthenticated ? "/settings/billing" : "/register"}
          className="ui-link-button"
        >
          {auth.isAuthenticated ? "Open Billing & Usage" : "Start Free"}
        </Link>
      </section>
    </main>
  );
}
