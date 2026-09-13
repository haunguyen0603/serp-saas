"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useProtectedAuth } from "./protected";
import {
  batchKey,
  batchUrl,
  type Batch,
  type Page,
  type Schedule,
} from "@/features/rankings/batches";
import { Skeleton, StatusBadge, ErrorState } from "@/design-system/ui";

// Load secondary metadata on demand instead of issuing two requests per list row.
export function ProjectActivity({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const auth = useProtectedAuth();
  const batch = useQuery({
    queryKey: [...batchKey(projectId), "preview"],
    queryFn: () => auth.request<Page<Batch>>(`${batchUrl(projectId)}?limit=1`),
    enabled: open && auth.isAuthenticated,
  });
  const schedule = useQuery({
    queryKey: ["projects", projectId, "rank-schedule"],
    queryFn: () =>
      auth.request<Schedule | null>(
        `/api/v1/projects/${projectId}/rank-schedule`,
      ),
    enabled: open && auth.isAuthenticated,
  });
  const latest = batch.data?.items[0];
  return (
    <details className="mt-4" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary className="text-brand cursor-pointer">
        Activity & actions
      </summary>
      <div className="mt-3 space-y-3">
        {(batch.isFetching || schedule.isFetching) && (
          <Skeleton label="Loading project activity…" rows={1} />
        )}
        {(batch.isError || schedule.isError) && (
          <ErrorState
            onRetry={() => {
              void batch.refetch();
              void schedule.refetch();
            }}
          />
        )}
        {batch.data && (
          <p>
            Latest check:{" "}
            {latest ? (
              <>
                <StatusBadge status={latest.status} /> ·{" "}
                {new Date(latest.requested_at).toLocaleString()}
              </>
            ) : (
              "Never checked"
            )}
          </p>
        )}
        {schedule.isSuccess && (
          <p>
            Schedule:{" "}
            <StatusBadge
              status={
                schedule.data?.enabled
                  ? schedule.data.frequency
                  : schedule.data
                    ? "Disabled"
                    : "Not configured"
              }
            />
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <Link href={`/app/projects/${projectId}#keywords`}>
            Open keywords
          </Link>
          <Link href={`/app/projects/${projectId}#schedule`}>
            Manage schedule
          </Link>
          <Link href={`/app/projects/${projectId}`}>Project settings</Link>
        </div>
      </div>
    </details>
  );
}
