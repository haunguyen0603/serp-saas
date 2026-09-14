"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  useProtectedAuth,
  ProtectedStatus,
} from "@/features/projects/protected";
import type { BillingSummary } from "@/features/billing/types";
import type { Batch } from "@/features/rankings/batches";
import {
  Card,
  EmptyState,
  ErrorState,
  Icon,
  PageHeader,
  Skeleton,
  StatCard,
  StatusBadge,
  Table,
  UsageMeter,
} from "@/design-system/ui";
export type OverviewData = {
  billing: BillingSummary;
  active_tracked_sites: number;
  recent_batches: (Batch & { project_id: string; project_name: string })[];
};
export function Overview() {
  const auth = useProtectedAuth();
  const query = useQuery({
    queryKey: ["overview", auth.user?.id],
    queryFn: () => auth.request<OverviewData>("/api/v1/overview"),
    enabled: auth.isAuthenticated,
    staleTime: 0,
    refetchInterval: (q) =>
      q.state.data?.recent_batches.some((b) =>
        ["pending", "queued", "running"].includes(b.status),
      )
        ? 3000
        : false,
  });
  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  const data = query.data;
  return (
    <main>
      <PageHeader
        eyebrow="YOUR WORKSPACE"
        title="Overview"
        description="A clear view of your rank tracking and monthly usage."
        actions={
          <Link className="ui-link-button" href="/app/projects/new">
            <Icon name="plus" />
            Create Project
          </Link>
        }
      />
      {query.isPending && <Skeleton label="Loading overview…" rows={4} />}
      {query.isError && (
        <ErrorState onRetry={() => void query.refetch()}>
          Your workspace summary could not be loaded. Your projects are still
          available from the navigation.
        </ErrorState>
      )}
      {data && (
        <>
          <div className="overview-stats">
            <StatCard
              label="Active projects"
              icon="folder"
              value={data.billing.devices.reduce(
                (n, d) => n + d.projects_used,
                0,
              )}
              detail="Across Desktop & Mobile"
            />
            <StatCard
              label="Active keywords"
              icon="chart"
              value={data.billing.devices
                .reduce((n, d) => n + d.keywords_used, 0)
                .toLocaleString("en-US")}
              detail="Across active projects"
            />
            <StatCard
              label="Tracked sites"
              icon="globe"
              value={data.active_tracked_sites}
              detail="Domains matched in results"
            />
            <StatCard
              label="Checks this period"
              icon="check"
              value={data.billing.devices
                .reduce((n, d) => n + d.usage.used, 0)
                .toLocaleString("en-US")}
              detail="Each device has its own allowance"
            />
          </div>
          <div className="overview-columns">
            <Card>
              <div className="overview-section-heading">
                <h2>Recent ranking activity</h2>
                <Link href="/app/rankings" className="text-brand text-sm">
                  View rankings →
                </Link>
              </div>
              {data.recent_batches.length ? (
                <Table aria-label="Recent ranking activity">
                  <thead>
                    <tr>
                      <th>Project</th>
                      <th>Status</th>
                      <th>Checks</th>
                      <th>Requested</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_batches.map((batch) => (
                      <tr key={batch.id}>
                        <td>
                          <Link
                            className="text-brand font-semibold"
                            href={`/app/projects/${batch.project_id}#batches`}
                          >
                            {batch.project_name}
                          </Link>
                          <p className="ui-caption">
                            {batch.trigger_type.replaceAll("_", " ")}
                          </p>
                        </td>
                        <td>
                          <StatusBadge status={batch.status} />
                        </td>
                        <td>
                          {batch.succeeded_keyword_count +
                            batch.failed_keyword_count +
                            batch.cancelled_keyword_count}{" "}
                          / {batch.requested_keyword_count}
                        </td>
                        <td>{new Date(batch.requested_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <EmptyState
                  title="Your first check starts here"
                  action={
                    <Link href="/app/projects" className="ui-link-button">
                      Open Projects
                    </Link>
                  }
                >
                  Add keywords to a project, then run Check Rankings to see your
                  positions here.
                </EmptyState>
              )}
            </Card>
            <Card>
              <h2>Make your workspace ready</h2>
              <p className="text-secondary text-sm mt-2">
                Four simple steps to your first ranking.
              </p>
              <div className="overview-checklist">
                <Link href="/app/tracked-sites">
                  Add a Tracked Site{" "}
                  {data.active_tracked_sites > 0 && (
                    <StatusBadge status="completed" />
                  )}
                </Link>
                <Link href="/app/projects/new">Create a Project</Link>
                <Link href="/app/projects">Add your Keywords</Link>
                <Link href="/app/rankings">Run a rank check</Link>
              </div>
            </Card>
          </div>
          <div className="overview-section-heading mt-8">
            <h2>Your Plans & usage</h2>
            <Link href="/settings/billing" className="text-brand text-sm">
              Billing & Usage →
            </Link>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            {data.billing.devices.map((device) => (
              <Card key={device.device_scope}>
                <div className="overview-section-heading">
                  <h3>{device.plan.name}</h3>
                  <StatusBadge status={device.status} />
                </div>
                <UsageMeter
                  label={`${device.device_scope === "desktop" ? "Desktop" : "Mobile"} checks`}
                  used={device.usage.used}
                  limit={device.usage.limit}
                  reserved={device.usage.reserved}
                />
                <p className="ui-caption">
                  Next reset{" "}
                  {new Date(device.usage.period_end).toLocaleDateString()} ·{" "}
                  {device.usage.remaining.toLocaleString("en-US")} remaining
                </p>
              </Card>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
