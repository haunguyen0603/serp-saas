import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import { BatchPanel, SchedulePanel } from "./batch-panel";
import { terminalBatch, type Batch } from "./batches";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/features/projects/protected", () => ({
  useProtectedAuth: () => ({ request, isAuthenticated: true }),
}));
const batch: Batch = {
  id: "batch-1",
  status: "queued",
  trigger_type: "manual_project",
  requested_keyword_count: 2,
  queued_keyword_count: 2,
  running_keyword_count: 0,
  succeeded_keyword_count: 0,
  failed_keyword_count: 0,
  cancelled_keyword_count: 0,
  progress_percent: 0,
  requested_at: "2026-09-12T00:00:00Z",
  started_at: null,
  completed_at: null,
};
const view = (node: React.ReactNode) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>{node}</QueryClientProvider>,
    ),
  };
};
beforeEach(() => vi.resetAllMocks());

it("renders queued progress, polls until completion, then refreshes rankings and stops", async () => {
  let current = batch;
  request.mockImplementation(async (path: string) =>
    path.includes("/jobs?")
      ? { items: [], next_cursor: null }
      : path.includes("?limit")
        ? { items: [current], next_cursor: null }
        : current,
  );
  const { client, unmount } = view(
    <BatchPanel
      projectId="project"
      selectedBatch="batch-1"
      onSelect={() => {}}
    />,
  );
  const invalidation = vi.spyOn(client, "invalidateQueries");
  await screen.findByText(/0 \/ 2 completed/);
  expect(screen.getByRole("progressbar")).toHaveAttribute("value", "0");
  current = {
    ...batch,
    status: "completed",
    succeeded_keyword_count: 2,
    queued_keyword_count: 0,
    progress_percent: 100,
    completed_at: batch.requested_at,
  };
  await screen.findByText(/2 \/ 2 completed/, {}, { timeout: 5000 });
  expect(invalidation).toHaveBeenCalledWith({
    queryKey: ["projects", "project", "rankings"],
  });
  await waitFor(() => expect(client.isFetching()).toBe(0));
  const count = request.mock.calls.length;
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 2200));
  });
  expect(request.mock.calls.length).toBe(count);
  unmount();
});

it("shows safe failure text, batch history, and cancellation", async () => {
  request.mockImplementation(async (path: string) =>
    path.includes("/jobs?")
      ? { items: [], next_cursor: null }
      : path.includes("?limit")
        ? { items: [batch], next_cursor: null }
        : { ...batch, failed_keyword_count: 1 },
  );
  view(
    <BatchPanel
      projectId="project"
      selectedBatch="batch-1"
      onSelect={() => {}}
    />,
  );
  await screen.findByText("Some keyword checks could not be completed.");
  expect(screen.getByRole("table", { name: "Batch history" })).toBeVisible();
  fireEvent.click(
    screen.getByRole("button", { name: "Cancel pending checks" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Confirm action" }));
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/project/rank-check-batches/batch-1/cancel",
      { method: "POST" },
    ),
  );
  expect(
    screen.queryByText(/gserviceaccount|cloud tasks|serper/i),
  ).not.toBeInTheDocument();
});

it.each([
  [
    "SERP_PROVIDER_UNSUPPORTED_CONFIGURATION",
    "Ranking checks are not available for this project's search settings. Please contact support.",
  ],
  [
    "SERP_NO_PROVIDER_AVAILABLE",
    "Ranking checks are currently unavailable for this project. Please contact support.",
  ],
  [
    "SERP_PROVIDER_AUTH_ERROR",
    "The ranking service could not authenticate. Please contact support.",
  ],
  ["SERP_PROVIDER_TIMEOUT", "The ranking check timed out. Please try again."],
  ["unknown-upstream-secret", "Check could not be completed"],
  [null, "Check could not be completed"],
])("explains failed keyword checks safely for %s", async (code, message) => {
  const completed = {
    ...batch,
    status: "completed_with_errors",
    queued_keyword_count: 0,
    failed_keyword_count: 2,
    progress_percent: 100,
  };
  request.mockImplementation(async (path: string) =>
    path.includes("/jobs?")
      ? {
          items: [
            {
              id: "job-1",
              keyword: "vinfast",
              status: "failed",
              attempt_count: 1,
              last_error_code: code,
            },
          ],
          next_cursor: null,
        }
      : path.includes("?limit")
        ? { items: [completed], next_cursor: null }
        : completed,
  );
  view(
    <BatchPanel
      projectId="project"
      selectedBatch="batch-1"
      onSelect={() => {}}
    />,
  );
  fireEvent.click(await screen.findByText("Keyword check details"));
  expect(
    await screen.findByText(`vinfast: failed · Attempts: 1 · ${message}`),
  ).toBeVisible();
  if (code) expect(screen.queryByText(code, { exact: false })).toBeNull();
});

it("creates, pauses and deletes a timezone-aware schedule", async () => {
  request.mockImplementation(async (_: string, options?: RequestInit) =>
    options?.method === "PUT"
      ? {
          id: "schedule",
          ...JSON.parse(String(options.body)),
          next_run_at: "2026-09-13T00:00:00Z",
        }
      : null,
  );
  view(<SchedulePanel projectId="project" archived={false} />);
  await screen.findByRole("form", { name: "Rank schedule" });
  fireEvent.change(screen.getByLabelText("Timezone"), {
    target: { value: "Asia/Ho_Chi_Minh" },
  });
  fireEvent.change(screen.getByLabelText("Frequency"), {
    target: { value: "weekly" },
  });
  fireEvent.click(screen.getByLabelText("Enabled"));
  fireEvent.submit(screen.getByRole("form", { name: "Rank schedule" }));
  await screen.findByText("Schedule saved.");
  expect(screen.getByText("Schedule paused")).toBeVisible();
  const call = request.mock.calls.find(
    ([, options]) => options?.method === "PUT",
  );
  expect(JSON.parse(call![1].body)).toMatchObject({
    enabled: false,
    frequency: "weekly",
    timezone: "Asia/Ho_Chi_Minh",
  });
  expect(screen.getByRole("button", { name: "Save schedule" })).toHaveClass(
    "ui-button--primary",
  );
  const deleteButton = screen.getByRole("button", {
    name: "Delete schedule",
  });
  expect(deleteButton).toHaveClass("ui-button--danger");
  fireEvent.click(deleteButton);
  fireEvent.click(screen.getByRole("button", { name: "Confirm action" }));
  await screen.findByText("Schedule deleted.");
});

it("recognizes all terminal batch states", () => {
  for (const status of [
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
  ])
    expect(terminalBatch(status)).toBe(true);
  expect(terminalBatch("running")).toBe(false);
});
