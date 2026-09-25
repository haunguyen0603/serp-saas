import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { ReportsPage } from "./reports-page";

const { download, replace, request, refresh } = vi.hoisted(() => ({
  download: vi.fn(),
  replace: vi.fn(),
  request: vi.fn(),
  refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));
vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    isAuthenticated: true,
    error: null,
    request,
    download,
    refresh,
  }),
}));

const project = {
  id: "project-1",
  name: "Vietnam Reports",
  search_engine: "google",
  country_code: "VN",
  language_code: "vi",
  device: "desktop",
  location: null,
  status: "active",
  keyword_count: 2,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const preview = {
  project_id: project.id,
  project_name: project.name,
  device: "desktop",
  period_start_utc: "2026-08-24T00:00:00Z",
  period_end_utc: "2026-09-23T00:00:00Z",
  report_timezone: "UTC",
  active_scope: "active_keywords_and_tracked_sites",
  no_matching_keywords: false,
  matching_keywords_without_observations: false,
  filters: {},
  metrics: {
    distinct_keywords: 2,
    keyword_site_pairs: 2,
    distinct_tracked_sites: 1,
    observed_pairs: 2,
    never_checked: 0,
    effective_depth: 10,
    latest_successful_check_at: "2026-09-22T00:00:00Z",
    comparison_basis: "range_boundary",
    distribution: { top_3: 1, positions_4_10: 0, not_found_in_depth: 1 },
    movements: {
      improved: 1,
      declined: 0,
      unchanged: 0,
      entered_checked_depth: 0,
      left_checked_depth: 1,
      no_previous_data: 0,
      never_checked: 0,
    },
    biggest_winners: [],
    biggest_losers: [],
  },
  sample: [
    {
      keyword_id: "keyword-1",
      keyword: "cà phê ngon",
      tracked_site_id: "site-1",
      tracked_site_name: "Main site",
      comparison: {
        checked_at_utc: "2026-08-22T00:00:00Z",
        position: 8,
        depth: 10,
        status: "ranked",
      },
      current: {
        checked_at_utc: "2026-09-22T00:00:00Z",
        position: 2,
        depth: 10,
        status: "ranked",
      },
      movement_type: "improved",
      numeric_change: 6,
    },
  ],
};
const generated = {
  id: "report-1",
  project_id: project.id,
  report_schedule_id: null,
  report_type: "project_pdf",
  status: "queued",
  period_start_utc: preview.period_start_utc,
  period_end_utc: preview.period_end_utc,
  filters_snapshot: {},
  metrics_snapshot: {},
  schema_version: 1,
  mime_type: null,
  byte_size: null,
  filename: null,
  created_at: "2026-09-23T00:00:00Z",
  started_at: null,
  completed_at: null,
  expires_at: "2026-10-23T00:00:00Z",
  error_code: null,
  attempt_count: 0,
};

function api() {
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === "/api/v1/projects/project-1") return project;
    if (path.endsWith("/keyword-groups"))
      return {
        items: [
          {
            id: "group-1",
            name: "Brand",
            active_keyword_count: 1,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
      };
    if (path.endsWith("/keyword-tags"))
      return {
        items: [
          {
            id: "tag-1",
            name: "Priority",
            active_keyword_count: 1,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
          {
            id: "tag-2",
            name: "Local",
            active_keyword_count: 1,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
      };
    if (path.startsWith("/api/v1/tracked-sites"))
      return {
        items: [
          {
            id: "site-1",
            name: "Main site",
            status: "active",
            primary_domain: "example.com",
            domain_alias_count: 0,
            domains: [],
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
        next_cursor: null,
        has_more: false,
      };
    if (path.includes("/reports/preview")) return preview;
    if (path.endsWith("/reports") && options?.method === "POST")
      return generated;
    if (path.includes("/reports?limit="))
      return { items: [], next_cursor: null, has_more: false };
    if (path.endsWith("/report-schedules"))
      return {
        items: [],
        delivery_configured: false,
        recipient_mode: "verified_account",
      };
    throw new Error(`Unexpected request: ${path}`);
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  api();
});

const view = () =>
  render(
    <Providers>
      <ReportsPage projectId="project-1" />
    </Providers>,
  );

it("previews checked-depth semantics and sends Group plus Tags ALL filters", async () => {
  view();
  expect(await screen.findByRole("heading", { name: "Reports" })).toBeVisible();
  expect(screen.getByText(/no new rank check is run/i)).toBeVisible();
  expect(await screen.findByText("Not found in Top 10")).toBeVisible();
  expect(screen.getByText("Entered Top 10")).toBeVisible();

  fireEvent.change(screen.getByLabelText("Tracked Site"), {
    target: { value: "site-1" },
  });
  fireEvent.change(screen.getByLabelText("Keyword Group"), {
    target: { value: "group-1" },
  });
  const tagSelect = screen.getByLabelText("Keyword Tags") as HTMLSelectElement;
  for (const option of tagSelect.options) option.selected = true;
  fireEvent.change(tagSelect);
  fireEvent.change(screen.getByLabelText("Tag matching"), {
    target: { value: "all" },
  });
  await waitFor(() => {
    const paths = request.mock.calls.map(([path]) => String(path));
    expect(
      paths.some(
        (path) =>
          path.includes("tracked_site_id=site-1") &&
          path.includes("keyword_group_id=group-1") &&
          path.includes("keyword_tag_ids=tag-1%2Ctag-2") &&
          path.includes("tag_match=all"),
      ),
    ).toBe(true);
  });
});

it("validates custom dates, prevents duplicate generation, and shows delivery unavailable", async () => {
  view();
  await screen.findByText("cà phê ngon");
  fireEvent.change(screen.getByLabelText("Reporting period"), {
    target: { value: "custom" },
  });
  fireEvent.change(screen.getByLabelText("Start date (UTC)"), {
    target: { value: "2026-09-20" },
  });
  fireEvent.change(screen.getByLabelText("End date (UTC)"), {
    target: { value: "2026-09-01" },
  });
  expect(
    screen.getByText(/Choose a start date on or before the end date/),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Generate PDF" })).toBeDisabled();

  fireEvent.change(screen.getByLabelText("End date (UTC)"), {
    target: { value: "2026-09-30" },
  });
  const button = await screen.findByRole("button", { name: "Generate PDF" });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  await waitFor(() =>
    expect(
      request.mock.calls.filter(
        ([path, options]) =>
          String(path).endsWith("/reports") && options?.method === "POST",
      ),
    ).toHaveLength(1),
  );
  expect(await screen.findByText("Project PDF queued.")).toBeVisible();
  expect(
    await screen.findByText(/Email delivery is not configured/),
  ).toBeVisible();
});

it("edits a configured report schedule and sends explicit calendar fields", async () => {
  const baseImplementation = request.getMockImplementation();
  const schedule = {
    id: "schedule-1",
    project_id: project.id,
    name: "Monday report",
    report_type: "project_pdf",
    frequency: "weekly",
    report_timezone: "UTC",
    scheduled_hour: 9,
    weekday: 0,
    month_day: null,
    filters: {},
    active: true,
    delivery_configured: true,
    recipient_mode: "verified_account",
    next_run_at_utc: "2026-09-28T09:00:00Z",
    last_run_at_utc: null,
    last_delivery_status: null,
    last_error_code: null,
    created_at: "2026-09-20T00:00:00Z",
    updated_at: "2026-09-20T00:00:00Z",
  };
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.endsWith("/report-schedules") && !options?.method)
      return {
        items: [schedule],
        delivery_configured: true,
        recipient_mode: "verified_account",
      };
    if (path.endsWith("/report-schedules/schedule-1")) return schedule;
    return baseImplementation?.(path, options);
  });

  view();
  expect(await screen.findByText("Monday report")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Edit" }));
  const frequencies = screen.getAllByLabelText("Frequency");
  fireEvent.change(frequencies.at(-1)!, { target: { value: "monthly" } });
  fireEvent.change(screen.getByLabelText("Day of month"), {
    target: { value: "31" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/project-1/report-schedules/schedule-1",
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"month_day":31'),
      }),
    ),
  );
  const patchCall = request.mock.calls.find(
    ([path, options]) =>
      String(path).endsWith("/report-schedules/schedule-1") &&
      options?.method === "PATCH",
  );
  expect(JSON.parse(String(patchCall?.[1]?.body))).toMatchObject({
    frequency: "monthly",
    weekday: null,
    month_day: 31,
  });
});
