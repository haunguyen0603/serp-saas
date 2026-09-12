import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { ProjectDetail } from "@/features/projects/project-detail";
import type { Keyword, Project } from "@/features/projects/types";
import type { RankCheck, RankCheckDetail } from "./types";

const { request, refresh } = vi.hoisted(() => ({
  request: vi.fn(),
  refresh: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
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
    refresh,
  }),
}));

const project: Project = {
  id: "project-1",
  name: "Ranking Project",
  search_engine: "google",
  country_code: "VN",
  language_code: "vi",
  device: "desktop",
  location: "Ho Chi Minh City",
  status: "active",
  keyword_count: 3,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const keywords: Keyword[] = [
  "ranked keyword",
  "missing keyword",
  "failed keyword",
].map((keyword, index) => ({
  id: `keyword-${index + 1}`,
  keyword,
  active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
}));
const ranking = {
  tracked_site_id: "site-1",
  tracked_domain_id: "domain-1",
  tracked_site_name: "Owned Site",
  matched_domain: "old.example",
  position: 2,
  result_url: "https://old.example/page",
  result_hostname: "old.example",
  title: "Owned page",
};
const check: RankCheck = {
  id: "check-1",
  project_id: project.id,
  keyword_id: keywords[0].id,
  provider: "serpapi",
  status: "succeeded",
  query_snapshot: "ranked keyword",
  search_engine_snapshot: "google",
  country_code_snapshot: "VN",
  language_code_snapshot: "vi",
  device_snapshot: "desktop",
  location_snapshot: "Ho Chi Minh City",
  result_limit: 10,
  provider_request_count: 1,
  provider_request_id: "request-1",
  requested_at: "2026-09-11T01:00:00Z",
  completed_at: "2026-09-11T01:00:01Z",
  error_code: null,
  error_message: null,
  result_count: 2,
  rankings: [ranking],
  provider_attempts: [
    {
      provider: "serpapi",
      attempt_number: 1,
      status: "succeeded",
      started_at: "2026-09-11T01:00:00Z",
      completed_at: "2026-09-11T01:00:01Z",
      error_code: null,
      provider_request_count: 1,
    },
  ],
  created_at: "2026-09-11T01:00:00Z",
};
const missingCheck: RankCheck = {
  ...check,
  id: "check-2",
  keyword_id: keywords[1].id,
  query_snapshot: "missing keyword",
  rankings: [],
};
const failedCheck: RankCheck = {
  ...check,
  id: "check-3",
  keyword_id: keywords[2].id,
  query_snapshot: "failed keyword",
  status: "failed",
  result_count: 0,
  rankings: [],
  error_code: "SERP_PROVIDER_TIMEOUT",
  error_message: "The SERP provider timed out.",
};
const detail: RankCheckDetail = {
  ...check,
  organic_results: [
    {
      position: 1,
      title: "Competitor",
      url: "https://competitor.example/page",
      hostname: "competitor.example",
      displayed_url: null,
      snippet: null,
    },
    {
      position: 2,
      title: "Owned page",
      url: ranking.result_url,
      hostname: ranking.result_hostname,
      displayed_url: null,
      snippet: null,
    },
  ],
};

function mockApi() {
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.includes("rank-check-batches?") || path.includes("/jobs?"))
      return { items: [], next_cursor: null, has_more: false };
    if (path.endsWith("rank-schedule")) return null;
    if (path === "/api/v1/projects/project-1" && !options) return project;
    if (path.endsWith("/rankings/latest"))
      return {
        items: [
          {
            keyword_id: keywords[0].id,
            keyword: keywords[0].keyword,
            latest_check: check,
          },
          {
            keyword_id: keywords[1].id,
            keyword: keywords[1].keyword,
            latest_check: missingCheck,
          },
          {
            keyword_id: keywords[2].id,
            keyword: keywords[2].keyword,
            latest_check: failedCheck,
          },
        ],
      };
    if (path.endsWith("/rank-checks/check-1")) return detail;
    if (path.includes("keyword-1/rank-checks") && !options)
      return { items: [check], next_cursor: null, has_more: false };
    if (path.includes("/keywords") && !options)
      return { items: keywords, next_cursor: null, has_more: false };
    if (path.endsWith("/rank-check-batches") && options?.method === "POST") {
      return {
        batch_id: "batch-1",
        job_id: null,
        status: "queued",
        requested_keyword_count: 3,
      };
    }
    if (path.includes("rank-check-batches") && path.includes("/jobs"))
      return { items: [], next_cursor: null, has_more: false };
    if (path.endsWith("rank-check-batches/batch-1"))
      return {
        id: "batch-1",
        status: "completed",
        trigger_type: "manual_project",
        requested_keyword_count: 3,
        succeeded_keyword_count: 3,
        failed_keyword_count: 0,
        cancelled_keyword_count: 0,
        running_keyword_count: 0,
        queued_keyword_count: 0,
        progress_percent: 100,
        requested_at: check.requested_at,
        started_at: null,
        completed_at: check.requested_at,
      };
    if (path.includes("rank-check-batches?"))
      return { items: [], next_cursor: null, has_more: false };
    if (path.endsWith("rank-schedule")) return null;
    return undefined;
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  mockApi();
});

it("hides provider and fallback metadata from ranking history", async () => {
  const fallbackCheck: RankCheck = {
    ...check,
    provider: "serper",
    provider_request_count: 2,
    provider_attempts: [
      {
        ...check.provider_attempts[0],
        provider: "serpapi",
        status: "failed",
        error_code: "SERP_PROVIDER_RATE_LIMITED",
      },
      {
        ...check.provider_attempts[0],
        provider: "serper",
        attempt_number: 2,
      },
    ],
  };
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.includes("rank-check-batches?") || path.includes("/jobs?"))
      return { items: [], next_cursor: null, has_more: false };
    if (path.endsWith("rank-schedule")) return null;
    if (path === "/api/v1/projects/project-1" && !options) return project;
    if (path.endsWith("/rankings/latest"))
      return {
        items: [
          {
            keyword_id: keywords[0].id,
            keyword: keywords[0].keyword,
            latest_check: fallbackCheck,
          },
        ],
      };
    if (path.includes("keyword-1/rank-checks") && !options)
      return { items: [fallbackCheck], next_cursor: null, has_more: false };
    if (path.includes("/keywords") && !options)
      return { items: keywords, next_cursor: null, has_more: false };
    return undefined;
  });
  render(
    <Providers>
      <ProjectDetail projectId="project-1" />
    </Providers>,
  );
  await screen.findByText("ranked keyword");
  fireEvent.click(screen.getAllByRole("button", { name: "History" })[0]);
  const history = await screen.findByRole("region", {
    name: "Ranking history",
  });
  expect(within(history).queryByText(/Serper/)).not.toBeInTheDocument();
  expect(within(history).queryByText(/attempts/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/provider/i)).not.toBeInTheDocument();
});

it("renders latest ranking, no-match, and failed states from real API data", async () => {
  render(
    <Providers>
      <ProjectDetail projectId="project-1" />
    </Providers>,
  );
  await screen.findByText("Owned Site #2");
  const table = screen
    .getAllByRole("table")
    .find((item) => !item.getAttribute("aria-label"))!;
  expect(within(table).getByText("Owned Site #2")).toBeVisible();
  expect(within(table).getByText("Not found in Top 10")).toBeVisible();
  expect(within(table).getByText("Check failed")).toBeVisible();
});

it("runs project and single Keyword checks with loading-safe actions", async () => {
  render(
    <Providers>
      <ProjectDetail projectId="project-1" />
    </Providers>,
  );
  await screen.findByText("ranked keyword");
  fireEvent.click(screen.getByRole("button", { name: "Check Rankings" }));
  expect(await screen.findByText("Ranking checks queued.")).toBeVisible();
  fireEvent.click(screen.getAllByRole("button", { name: "Check now" })[0]);
  expect(await screen.findByText("Keyword check queued.")).toBeVisible();
  expect(request).toHaveBeenCalledWith(
    "/api/v1/projects/project-1/rank-check-batches",
    expect.objectContaining({ method: "POST" }),
  );
});

it("opens history and detail with snapshots and tracked result labels", async () => {
  render(
    <Providers>
      <ProjectDetail projectId="project-1" />
    </Providers>,
  );
  await screen.findByText("ranked keyword");
  fireEvent.click(screen.getAllByRole("button", { name: "History" })[0]);
  const history = await screen.findByRole("region", {
    name: "Ranking history",
  });
  expect(within(history).queryByText("SerpApi")).not.toBeInTheDocument();
  expect(within(history).getByText("Owned Site #2")).toBeVisible();
  fireEvent.click(
    within(history).getByRole("button", { name: "View results" }),
  );
  const checkDetail = await screen.findByRole("region", {
    name: "Rank Check detail",
  });
  expect(within(checkDetail).getByText("competitor.example")).toBeVisible();
  expect(within(checkDetail).getByText("Tracked · Owned Site")).toBeVisible();
  expect(within(checkDetail).getByText(/VN · vi · desktop/)).toBeVisible();
  expect(
    within(checkDetail).queryByText(/Data source: SerpApi/),
  ).not.toBeInTheDocument();
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/project-1/keywords/keyword-1/rank-checks/check-1",
    ),
  );
});
