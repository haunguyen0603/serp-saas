"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  Dialog,
  EmptyState,
  ErrorState,
  Icon,
  PageHeader,
  Skeleton,
  StatusBadge,
  Tabs,
} from "@/design-system/ui";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import { groupPlans, planCatalogQuery, planPrice } from "./plan-catalog";
import type { BillingSummary, Plan } from "./types";

type ProductLine = Plan["device_scope"];
const productName = (device: ProductLine) =>
  device === "desktop" ? "Desktop" : "Mobile";

function PlanCard({
  plan,
  current,
  onPlanSelect,
}: {
  plan: Plan;
  current: boolean;
  onPlanSelect: (planId: string, productLine: ProductLine) => void;
}) {
  return (
    <Card
      className={`change-plan-card${current ? " change-plan-card--current" : ""}`}
      aria-label={plan.name}
      data-plan-code={plan.code}
    >
      <div className="change-plan-card-header">
        <span className="change-plan-icon">
          <Icon name="wallet" width={26} height={26} />
        </span>
        <h3>{plan.name}</h3>
        <p className="change-plan-price">
          <strong>{planPrice(plan)}</strong> <span>/ month</span>
        </p>
        <div className="change-plan-badge">
          {current && <Badge tone="info">Current Plan</Badge>}
        </div>
      </div>
      <dl className="change-plan-entitlements">
        <div>
          <dt>Projects</dt>
          <dd>{plan.max_projects.toLocaleString("en-US")}</dd>
        </div>
        <div>
          <dt>Keywords</dt>
          <dd>{plan.max_keywords.toLocaleString("en-US")}</dd>
        </div>
        <div>
          <dt>Checks / month</dt>
          <dd>{plan.monthly_keyword_checks.toLocaleString("en-US")}</dd>
        </div>
        <div>
          <dt>Schedule</dt>
          <dd>
            {plan.scheduled_checks_enabled
              ? `Up to ${plan.max_scheduled_frequency}`
              : "Not included"}
          </dd>
        </div>
        <div>
          <dt>Product line</dt>
          <dd>{productName(plan.device_scope)}</dd>
        </div>
      </dl>
      <Button
        type="button"
        variant={current ? "secondary" : "primary"}
        disabled={current}
        onClick={() => onPlanSelect(plan.id ?? plan.code, plan.device_scope)}
      >
        {current ? "Current Plan" : "Select"}
      </Button>
    </Card>
  );
}

export function ChangePlanPage() {
  const auth = useProtectedAuth();
  const router = useRouter();
  const verified = auth.isAuthenticated && auth.user?.email_verified === true;
  const [productLine, setProductLine] = useState<ProductLine>("desktop");
  const [selection, setSelection] = useState<{
    planId: string;
    productLine: ProductLine;
  } | null>(null);
  useEffect(() => {
    if (auth.isAuthenticated && !verified) router.replace("/verify-email");
  }, [auth.isAuthenticated, verified, router]);
  const catalog = useQuery({ ...planCatalogQuery, enabled: verified });
  const billing = useQuery({
    queryKey: ["billing", auth.user?.id],
    queryFn: () => auth.request<BillingSummary>("/api/v1/billing/me"),
    enabled: verified,
  });
  const current = billing.isError
    ? undefined
    : billing.data?.devices.find(
        (device) => device.device_scope === productLine,
      );
  const plans = groupPlans(catalog.data ?? []).find(
    (group) => group.device === productLine,
  )!.plans;

  // This boundary intentionally only opens local informational state in M7J.
  function onPlanSelect(planId: string, selectedProductLine: ProductLine) {
    setSelection({ planId, productLine: selectedProductLine });
  }

  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  if (!verified)
    return (
      <main>
        <p role="status">Redirecting to email verification…</p>
      </main>
    );

  return (
    <main className="change-plan-page space-y-6">
      <PageHeader
        title="Change Plan"
        description="Compare available plans and choose the option that best matches your tracking needs."
      />
      <p className="text-secondary">
        Online plan changes are coming soon. Selecting a new plan does not
        change your subscription yet.
      </p>
      <Tabs
        label="Plan product line"
        items={[
          { value: "desktop", label: "Desktop" },
          { value: "mobile", label: "Mobile" },
        ]}
        value={productLine}
        onChange={(value) => setProductLine(value as ProductLine)}
      />
      <section
        role="tabpanel"
        aria-label={`${productName(productLine)} plans`}
        className="space-y-6"
      >
        <h2>{productName(productLine)} plans</h2>
        {billing.isPending && (
          <Skeleton label="Loading current subscription…" />
        )}
        {billing.isError && (
          <ErrorState
            title="Unable to load your current subscription."
            onRetry={() => void billing.refetch()}
          >
            Your current plan could not be identified. Please try again.
          </ErrorState>
        )}
        {current && (
          <Card className="change-plan-summary">
            <div>
              <p className="text-secondary">
                Current {productName(productLine)} plan
              </p>
              <h3>{current.plan.name}</h3>
            </div>
            <div>
              <p className="text-secondary">Subscription status</p>
              <StatusBadge status={current.status} />
            </div>
            {current.period_end && (
              <div>
                <p className="text-secondary">Active until</p>
                <time dateTime={current.period_end}>
                  {new Intl.DateTimeFormat("en-US", {
                    dateStyle: "medium",
                    timeZone: "UTC",
                  }).format(new Date(current.period_end))}
                  {" (UTC)"}
                </time>
              </div>
            )}
          </Card>
        )}
        {billing.isSuccess && !current && (
          <p role="status" className="text-secondary">
            No current {productName(productLine)} subscription was returned.
          </p>
        )}
        {catalog.isPending && (
          <div className="change-plan-grid">
            {[0, 1, 2].map((index) => (
              <Card key={index}>
                <Skeleton label="Loading plans…" rows={7} />
              </Card>
            ))}
          </div>
        )}
        {catalog.isError && (
          <ErrorState
            title="Unable to load plans."
            onRetry={() => void catalog.refetch()}
          >
            Please try again to load the current plan catalog.
          </ErrorState>
        )}
        {catalog.isSuccess &&
          (plans.length ? (
            <div className="change-plan-grid">
              {plans.map((plan) => (
                <PlanCard
                  key={plan.code}
                  plan={plan}
                  current={
                    current?.plan.code === plan.code &&
                    current.device_scope === plan.device_scope
                  }
                  onPlanSelect={onPlanSelect}
                />
              ))}
            </div>
          ) : (
            <EmptyState title="No plans are currently available.">
              No {productName(productLine)} plans are available. Please check
              again later.
            </EmptyState>
          ))}
      </section>
      <Dialog
        open={selection !== null}
        onClose={() => setSelection(null)}
        title="Plan upgrade coming soon"
      >
        <p>
          Online payment and automatic plan upgrades are being prepared. Your
          current subscription has not been changed.
        </p>
        <div className="ui-dialog-actions">
          <Button type="button" onClick={() => setSelection(null)}>
            Close
          </Button>
        </div>
      </Dialog>
    </main>
  );
}
