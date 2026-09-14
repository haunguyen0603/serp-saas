"use client";
import {
  Alert,
  Button,
  Input,
  Select,
  Table,
  Toast,
  StatusBadge,
  EmptyState,
  Skeleton,
} from "@/design-system/ui";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { useProtectedAuth } from "@/features/projects/protected";
import {
  batchKey,
  batchUrl,
  getBatch,
  terminalBatch,
  type Batch,
  type Job,
  type Page,
  type Schedule,
} from "./batches";
import { rankingKeys } from "./api";
import type { BillingSummary } from "@/features/billing/types";
import { ApiError } from "@/lib/api/client";

export function BatchPanel({
  projectId,
  selectedBatch,
  onSelect,
}: {
  projectId: string;
  selectedBatch: string | null;
  onSelect: (id: string) => void;
}) {
  const auth = useProtectedAuth();
  const client = useQueryClient();
  const history = useInfiniteQuery({
    queryKey: batchKey(projectId),
    queryFn: ({ pageParam }) =>
      auth.request<Page<Batch>>(
        `${batchUrl(projectId)}?limit=10${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ""}`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    refetchInterval: (query) =>
      query.state.data?.pages.some((page) =>
        page.items.some((batch) => !terminalBatch(batch.status)),
      )
        ? 2000
        : false,
  });
  const activeId = selectedBatch ?? history.data?.pages[0]?.items[0]?.id;
  const progress = useQuery({
    queryKey: [...batchKey(projectId), activeId],
    queryFn: () => getBatch(auth.request, projectId, activeId!),
    enabled: !!activeId,
    refetchInterval: (query) =>
      query.state.data && !terminalBatch(query.state.data.status)
        ? 2000
        : false,
  });
  const jobs = useInfiniteQuery({
    queryKey: [...batchKey(projectId), activeId, "jobs", progress.data?.status],
    queryFn: ({ pageParam }) =>
      auth.request<Page<Job>>(
        `${batchUrl(projectId)}/${activeId}/jobs?limit=20${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ""}`,
      ),
    enabled: !!activeId,
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    refetchInterval:
      progress.data && !terminalBatch(progress.data.status) ? 2000 : false,
  });
  const progressStatus = progress.data?.status;
  const progressId = progress.data?.id;
  useEffect(() => {
    if (progressStatus && terminalBatch(progressStatus)) {
      void client.invalidateQueries({ queryKey: rankingKeys.all(projectId) });
      void client.invalidateQueries({
        queryKey: ["projects", projectId, "keywords"],
      });
      void client.invalidateQueries({
        queryKey: batchKey(projectId),
        exact: true,
      });
    }
  }, [progressStatus, progressId, client, projectId]); // terminal transition refreshes history and latest
  const cancel = useMutation({
    mutationFn: () =>
      auth.request(`${batchUrl(projectId)}/${activeId}/cancel`, {
        method: "POST",
      }),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: batchKey(projectId) }),
  });
  const batch = progress.data;
  return (
    <section
      className="my-8 rounded-xl border border-border p-5"
      id="batches"
      aria-label="Ranking batches"
    >
      <h3 className="text-xl font-semibold">Ranking progress</h3>
      {(history.isError ||
        progress.isError ||
        jobs.isError ||
        cancel.isError) && (
        <Alert>Ranking progress could not be updated. Please try again.</Alert>
      )}
      {batch && (
        <div role="status" className="my-4">
          <StatusBadge status={batch.status} />
          <progress
            aria-label="Batch progress"
            max={100}
            value={batch.progress_percent}
            className="w-full"
          />
          <p>
            {batch.succeeded_keyword_count +
              batch.failed_keyword_count +
              batch.cancelled_keyword_count}{" "}
            / {batch.requested_keyword_count} completed (
            {batch.progress_percent}%) · {batch.running_keyword_count} running
          </p>
          {!!batch.failed_keyword_count && (
            <p>Some keyword checks could not be completed.</p>
          )}
          {!terminalBatch(batch.status) && (
            <Button
              disabled={cancel.isPending}
              confirmation="Cancel checks that have not started? Completed and running checks will keep their usage."
              onClick={() => cancel.mutate()}
              className="mt-2 text-danger"
            >
              Cancel pending checks
            </Button>
          )}
        </div>
      )}
      {history.isPending && <Skeleton label="Loading batch history…" />}
      {!history.isPending &&
        !history.isError &&
        !history.data?.pages[0]?.items.length && (
          <EmptyState title="No ranking history yet">
            Run Check Rankings to start a batch. Its progress and results will
            appear here.
          </EmptyState>
        )}
      <h3 className="mt-5 font-semibold">Recent batches</h3>
      <div className="overflow-x-auto">
        <Table aria-label="Batch history" className="w-full">
          <thead>
            <tr>
              {[
                "Date",
                "Trigger",
                "Status",
                "Keywords",
                "Succeeded",
                "Failed",
                "Duration",
              ].map((title) => (
                <th className="p-2" key={title}>
                  {title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.data?.pages
              .flatMap((page) => page.items)
              .map((item) => (
                <tr key={item.id}>
                  <td className="p-2">
                    <Button onClick={() => onSelect(item.id)}>
                      {new Date(item.requested_at).toLocaleString()}
                    </Button>
                  </td>
                  <td>{item.trigger_type.replaceAll("_", " ")}</td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td>{item.requested_keyword_count}</td>
                  <td>{item.succeeded_keyword_count}</td>
                  <td>{item.failed_keyword_count}</td>
                  <td>
                    {item.completed_at
                      ? `${Math.max(0, Math.round((Date.parse(item.completed_at) - Date.parse(item.requested_at)) / 1000))}s`
                      : "—"}
                  </td>
                </tr>
              ))}
          </tbody>
        </Table>
      </div>
      {history.hasNextPage && (
        <Button onClick={() => void history.fetchNextPage()}>
          Load more batches
        </Button>
      )}
      {!!jobs.data?.pages[0]?.items.length && (
        <details className="mt-4">
          <summary>Keyword check details</summary>
          <ul>
            {jobs.data.pages
              .flatMap((page) => page.items)
              .map((job) => (
                <li key={job.id}>
                  {job.keyword}: {job.status} · Attempts: {job.attempt_count}
                  {job.status === "failed"
                    ? " · Check could not be completed"
                    : ""}
                </li>
              ))}
          </ul>
          {jobs.hasNextPage && (
            <Button onClick={() => void jobs.fetchNextPage()}>
              Load more checks
            </Button>
          )}
        </details>
      )}
    </section>
  );
}

export function SchedulePanel({
  projectId,
  archived,
  device,
}: {
  projectId: string;
  archived: boolean;
  device?: string;
}) {
  const auth = useProtectedAuth();
  const client = useQueryClient();
  const key = ["projects", projectId, "rank-schedule"];
  const url = `/api/v1/projects/${projectId}/rank-schedule`;
  const [notice, setNotice] = useState("");
  const [frequency, setFrequency] = useState<string | null>(null);
  const billing = useQuery({
    queryKey: ["billing", auth.user?.id],
    queryFn: () => auth.request<BillingSummary>("/api/v1/billing/me"),
    enabled: auth.isAuthenticated && !!auth.user?.id,
    refetchInterval: 5000,
  });
  const entitlement = billing.data?.devices?.find(
    (item) => item.device_scope === device,
  )?.plan;
  const planBlocked = entitlement
    ? !entitlement.scheduled_checks_enabled
    : false;
  const query = useQuery({
    queryKey: key,
    queryFn: () => auth.request<Schedule | null>(url),
  });
  const save = useMutation({
    mutationFn: (body: object) =>
      auth.request<Schedule>(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: (value) => {
      client.setQueryData(key, value);
      setNotice("Schedule saved.");
    },
  });
  const remove = useMutation({
    mutationFn: () => auth.request(url, { method: "DELETE" }),
    onSuccess: () => {
      client.setQueryData(key, null);
      setNotice("Schedule deleted.");
    },
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setNotice("");
    save.mutate({
      enabled: values.get("enabled") === "on",
      frequency: values.get("frequency"),
      local_time: values.get("local_time"),
      timezone: values.get("timezone"),
      weekday: Number(values.get("weekday")),
    });
  }
  const schedule = query.data;
  return (
    <section id="schedule" className="ui-card my-8">
      <h3 className="text-xl font-semibold">Schedule</h3>
      {(save.isError || remove.isError || query.isError) && (
        <Alert>
          {save.error instanceof ApiError
            ? save.error.message
            : "Schedule could not be updated. Check the time and timezone."}
        </Alert>
      )}
      {notice && <Toast key={notice}>{notice}</Toast>}
      {query.isPending && <Skeleton label="Loading schedule…" rows={2} />}
      {planBlocked ? (
        <p className="text-secondary mt-3">
          <StatusBadge status="Disabled by Plan" /> Scheduled checks are not
          included in this Plan. Visit Billing &amp; Usage to see upgrade
          options.
        </p>
      ) : !schedule && !query.isPending ? (
        <p className="text-secondary mt-3">
          Not configured. Choose a time to check your keywords automatically.
        </p>
      ) : null}
      {entitlement?.max_scheduled_frequency === "weekly" && (
        <p className="text-secondary mt-3">
          Your Plan includes weekly scheduled checks.
        </p>
      )}
      {!query.isPending && (
        <form
          key={`${schedule ? JSON.stringify(schedule) : "new"}:${planBlocked}`}
          onSubmit={submit}
          aria-label="Rank schedule"
          className="mt-5"
        >
          <label className="inline-flex items-center gap-2">
            <Input
              name="enabled"
              type="checkbox"
              defaultChecked={schedule?.enabled ?? !planBlocked}
              disabled={planBlocked}
            />
            <span>Enabled</span>
          </label>
          <div className="mt-4 grid items-start gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <label>
              Frequency
              <Select
                name="frequency"
                value={
                  frequency ??
                  schedule?.frequency ??
                  (entitlement?.max_scheduled_frequency === "weekly"
                    ? "weekly"
                    : "daily")
                }
                onChange={(e) => setFrequency(e.target.value)}
              >
                <option
                  value="daily"
                  disabled={entitlement?.max_scheduled_frequency === "weekly"}
                >
                  Daily
                </option>
                <option value="weekly">Weekly</option>
              </Select>
            </label>
            <label
              hidden={
                (frequency ??
                  schedule?.frequency ??
                  (entitlement?.max_scheduled_frequency === "weekly"
                    ? "weekly"
                    : "daily")) !== "weekly"
              }
            >
              Weekly day
              <Select name="weekday" defaultValue={schedule?.weekday ?? 0}>
                {[
                  "Monday",
                  "Tuesday",
                  "Wednesday",
                  "Thursday",
                  "Friday",
                  "Saturday",
                  "Sunday",
                ].map((day, index) => (
                  <option value={index} key={day}>
                    {day}
                  </option>
                ))}
              </Select>
            </label>
            <label>
              Local time
              <Input
                type="time"
                name="local_time"
                defaultValue={schedule?.local_time ?? "07:00"}
                required
              />
            </label>
            <label>
              Timezone
              <Input
                name="timezone"
                defaultValue={
                  schedule?.timezone ??
                  Intl.DateTimeFormat().resolvedOptions().timeZone
                }
                required
              />
            </label>
          </div>
          {schedule && (
            <p className="mt-4">
              {schedule.enabled
                ? `Next check: ${new Date(schedule.next_run_at).toLocaleString()} (${schedule.timezone})`
                : "Schedule paused"}
            </p>
          )}
          <div className="mt-6 flex flex-wrap justify-end gap-3 border-t border-border pt-5">
            <Button
              type="submit"
              variant="primary"
              className="w-full sm:w-auto"
              disabled={archived || save.isPending || planBlocked}
            >
              Save schedule
            </Button>
            {schedule && (
              <Button
                type="button"
                variant="danger"
                className="w-full sm:w-auto"
                disabled={remove.isPending}
                confirmation="Delete this schedule? Automatic checks will stop; existing results are kept."
                onClick={() => remove.mutate()}
              >
                Delete schedule
              </Button>
            )}
          </div>
        </form>
      )}
    </section>
  );
}
