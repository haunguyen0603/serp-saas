"use client";

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
      className="my-8 rounded-xl border border-slate-700 p-5"
      aria-label="Ranking batches"
    >
      <h3 className="text-xl font-semibold">Ranking progress</h3>
      {(history.isError ||
        progress.isError ||
        jobs.isError ||
        cancel.isError) && (
        <p role="alert">
          Ranking progress could not be updated. Please try again.
        </p>
      )}
      {batch && (
        <div role="status" className="my-4">
          <p className="capitalize">{batch.status.replaceAll("_", " ")}</p>
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
            <button
              disabled={cancel.isPending}
              onClick={() => cancel.mutate()}
              className="mt-2 text-red-300"
            >
              Cancel pending checks
            </button>
          )}
        </div>
      )}
      <h3 className="mt-5 font-semibold">Recent batches</h3>
      <div className="overflow-x-auto">
        <table aria-label="Batch history" className="w-full text-left">
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
                    <button
                      className="text-teal-300 underline"
                      onClick={() => onSelect(item.id)}
                    >
                      {new Date(item.requested_at).toLocaleString()}
                    </button>
                  </td>
                  <td>{item.trigger_type.replaceAll("_", " ")}</td>
                  <td>{item.status.replaceAll("_", " ")}</td>
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
        </table>
      </div>
      {history.hasNextPage && (
        <button onClick={() => void history.fetchNextPage()}>
          Load more batches
        </button>
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
            <button onClick={() => void jobs.fetchNextPage()}>
              Load more checks
            </button>
          )}
        </details>
      )}
    </section>
  );
}

export function SchedulePanel({
  projectId,
  archived,
}: {
  projectId: string;
  archived: boolean;
}) {
  const auth = useProtectedAuth();
  const client = useQueryClient();
  const key = ["projects", projectId, "rank-schedule"];
  const url = `/api/v1/projects/${projectId}/rank-schedule`;
  const [notice, setNotice] = useState("");
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
    <section className="my-8 rounded-xl border border-slate-700 p-5">
      <h3 className="text-xl font-semibold">Schedule</h3>
      {(save.isError || remove.isError || query.isError) && (
        <p role="alert">
          Schedule could not be updated. Check the time and timezone.
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {!query.isPending && (
        <form
          key={schedule ? JSON.stringify(schedule) : "new"}
          onSubmit={submit}
          aria-label="Rank schedule"
          className="mt-4 flex flex-wrap items-end gap-4"
        >
          <label>
            <input
              name="enabled"
              type="checkbox"
              defaultChecked={schedule?.enabled ?? true}
            />{" "}
            Enabled
          </label>
          <label>
            Frequency{" "}
            <select
              className="bg-slate-950 p-2"
              name="frequency"
              defaultValue={schedule?.frequency ?? "daily"}
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </label>
          <label>
            Weekly day{" "}
            <select
              className="bg-slate-950 p-2"
              name="weekday"
              defaultValue={schedule?.weekday ?? 0}
            >
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
            </select>
          </label>
          <label>
            Local time{" "}
            <input
              className="bg-slate-950 p-2"
              type="time"
              name="local_time"
              defaultValue={schedule?.local_time ?? "07:00"}
              required
            />
          </label>
          <label>
            Timezone{" "}
            <input
              className="bg-slate-950 p-2"
              name="timezone"
              defaultValue={
                schedule?.timezone ??
                Intl.DateTimeFormat().resolvedOptions().timeZone
              }
              required
            />
          </label>
          <button
            className="rounded border border-teal-500 px-4 py-2"
            disabled={archived || save.isPending}
          >
            Save schedule
          </button>
          {schedule && (
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
            >
              Delete schedule
            </button>
          )}
        </form>
      )}
      {schedule && (
        <p className="mt-4">
          {schedule.enabled
            ? `Next check: ${new Date(schedule.next_run_at).toLocaleString()} (${schedule.timezone})`
            : "Schedule paused"}
        </p>
      )}
    </section>
  );
}
