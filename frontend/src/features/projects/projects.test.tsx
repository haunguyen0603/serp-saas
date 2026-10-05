import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { ProjectDetail } from "./project-detail";
import { ProjectForm } from "./project-form";
import { ProjectList } from "./project-list";
import type { Keyword, Project } from "./types";

const { replace, request, refresh } = vi.hoisted(() => ({
  replace: vi.fn(),
  request: vi.fn(),
  refresh: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
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
  name: "Vietnam Desktop",
  search_engine: "google",
  country_code: "VN",
  language_code: "vi",
  device: "desktop",
  location: "Ho Chi Minh City",
  status: "active",
  keyword_count: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const keyword: Keyword = {
  id: "keyword-1",
  keyword: "rank tracker",
  active: true,
  group: null,
  tags: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const group = {
  id: "group-1",
  name: "Brand",
  active_keyword_count: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const tag = { ...group, id: "tag-1", name: "Priority" };
const view = (node: React.ReactNode) => render(<Providers>{node}</Providers>);
beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal(
    "confirm",
    vi.fn(() => true),
  );
});

it("lists projects with SERP environment and keyword count", async () => {
  request.mockResolvedValue({
    items: [project],
    next_cursor: null,
    has_more: false,
  });
  view(<ProjectList />);
  expect(await screen.findByText("Vietnam Desktop")).toBeVisible();
  expect(screen.getByText(/Google · VN · vi/)).toBeVisible();
  expect(screen.getByText("1")).toBeVisible();
  expect(screen.queryByText("example.com")).not.toBeInTheDocument();
});

it("creates a Project with initial keywords and no domain", async () => {
  request.mockResolvedValue({
    project,
    keywords: {
      submitted: 3,
      normalized_unique: 2,
      created: 2,
      skipped_duplicates: 1,
      skipped_empty: 0,
    },
  });
  view(<ProjectForm />);
  const country = screen.getByRole("combobox", { name: "Country" });
  const language = screen.getByRole("combobox", { name: "Language" });
  expect(country).toHaveValue("");
  expect(country).toHaveAttribute("placeholder", "Select country");
  expect(language).toHaveValue("");
  expect(language).toHaveAttribute("placeholder", "Select language");
  fireEvent.change(country, { target: { value: "United States" } });
  fireEvent.click(screen.getByRole("option", { name: "United States (US)" }));
  fireEvent.change(language, { target: { value: "English" } });
  fireEvent.click(screen.getByRole("option", { name: "English (en)" }));
  expect(
    screen.queryByRole("combobox", { name: /provider/i }),
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Project name"), {
    target: { value: "Vietnam Desktop" },
  });
  fireEvent.change(screen.getByLabelText("Keywords, one per line"), {
    target: { value: "one\ntwo\none" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Create project" }));
  await waitFor(() =>
    expect(replace).toHaveBeenCalledWith("/app/projects/project-1"),
  );
  const body = JSON.parse(String(request.mock.calls[0][1].body));
  expect(body.keywords).toEqual(["one", "two", "one"]);
  expect(body.country_code).toBe("US");
  expect(body.language_code).toBe("en");
  expect(body).not.toHaveProperty("domain");
  expect(body).not.toHaveProperty("provider");
});

it("requires explicit country and language selections before creating a project", () => {
  view(<ProjectForm />);
  fireEvent.submit(screen.getByRole("form", { name: "Create project" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Select a country and language",
  );
  expect(request).not.toHaveBeenCalled();
});

function detailApi(settings: Partial<Project> = {}) {
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.includes("/analytics/summary"))
      return {
        ...summaryFixture,
        project_id: project.id,
        device: project.device,
      };
    if (path.includes("/analytics/movers")) return { winners: [], losers: [] };
    if (path.includes("rank-check-batches?") || path.includes("/jobs?"))
      return { items: [], next_cursor: null, has_more: false };
    if (path.endsWith("rank-schedule")) return null;
    if (path === "/api/v1/projects/project-1" && !options)
      return { ...project, ...settings };
    if (path.endsWith("/rankings/latest"))
      return {
        items: [
          {
            keyword_id: keyword.id,
            keyword: keyword.keyword,
            latest_check: null,
          },
        ],
      };
    if (path.endsWith("/keyword-groups")) return { items: [group] };
    if (path.endsWith("/keyword-tags")) return { items: [tag] };
    if (path.includes("/analytics/organization-summary"))
      return { ...summaryFixture, total_keywords: 1 };
    if (path.includes("/rank-checks"))
      return { items: [], next_cursor: null, has_more: false };
    if (path.includes("/keywords") && !options)
      return { items: [keyword], next_cursor: null, has_more: false };
    if (path.endsWith("/keywords/bulk"))
      return {
        submitted: 3,
        normalized_unique: 2,
        created: 2,
        skipped_duplicates: 1,
        skipped_empty: 0,
        items: [],
      };
    if (path.endsWith("/keywords/bulk-organize"))
      return {
        operation: "assign_group",
        selected_count: 1,
        affected_keyword_count: 1,
        assignment_count: null,
      };
    if (options?.method === "PATCH" && path.includes("/keywords/"))
      return { ...keyword, ...JSON.parse(String(options.body)) };
    if (options?.method === "PATCH")
      return {
        ...project,
        ...JSON.parse(String(options.body)),
        updated_at: "2026-01-02T00:00:00Z",
      };
    if (options?.method === "POST") return keyword;
    return undefined;
  });
}

const summaryFixture = {
  range: "30d",
  as_of: "2026-09-22T00:00:00Z",
  comparison_basis: "none",
  total_keywords: 1,
  observed_keywords: 0,
  never_checked: 1,
  ranked_keywords: 0,
  not_found_in_depth: 0,
  top_3: 0,
  top_10: 0,
  improved: 0,
  declined: 0,
  unchanged: 0,
  newly_ranked: 0,
  lost_ranking: 0,
  entered_checked_depth: 0,
  left_checked_depth: 0,
  no_previous_data: 1,
  distribution: {
    effective_depth: 10,
    buckets: { top_3: 0, positions_4_10: 0, not_found_in_depth: 0 },
  },
};

it("renders query-only Keyword columns and project-wide settings warning", async () => {
  detailApi();
  view(<ProjectDetail projectId="project-1" />);
  await screen.findByText("rank tracker");
  const table = screen
    .getAllByRole("table")
    .find((item) => !item.getAttribute("aria-label"))!;
  expect(within(table).getByText("rank tracker")).toBeVisible();
  for (const heading of [
    "Keyword",
    "Status",
    "Last checked",
    "Tracked rankings",
    "Actions",
  ])
    expect(within(table).getByText(heading)).toBeVisible();
  expect(within(table).getByText("Never checked")).toBeVisible();
  expect(
    screen.getByText("These settings apply to every keyword in this project."),
  ).toBeVisible();
  expect(screen.queryByText("Domain")).not.toBeInTheDocument();
});

it("adds and edits only Keyword query data", async () => {
  detailApi();
  view(<ProjectDetail projectId="project-1" />);
  await screen.findByText("rank tracker");
  fireEvent.click(screen.getByRole("button", { name: "Add Keyword" }));
  fireEvent.change(screen.getByLabelText("Keyword", { exact: true }), {
    target: { value: "new keyword" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Add keyword" }));
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/project-1/keywords",
      expect.objectContaining({
        body: '{"keyword":"new keyword","group_id":null,"tag_ids":[]}',
      }),
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Edit" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Edit keyword" }), {
    target: { value: "updated" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Edit keyword" }));
  await waitFor(() => {
    const call = request.mock.calls.find(
      ([path, options]) =>
        path.endsWith("keyword-1") && options?.method === "PATCH",
    );
    expect(JSON.parse(String(call?.[1].body))).toEqual({
      keyword: "updated",
      active: true,
      group_id: null,
      tag_ids: [],
    });
  });
});

it("manages organization and bulk assigns the current loaded rows", async () => {
  detailApi();
  view(<ProjectDetail projectId="project-1" />);
  await screen.findByText("rank tracker");
  fireEvent.click(screen.getByLabelText("Select rank tracker"));
  expect(screen.getByText("1 selected on loaded rows")).toBeVisible();
  fireEvent.change(
    within(screen.getByLabelText("Bulk Keyword actions")).getByLabelText(
      "Group",
    ),
    { target: { value: "group-1" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  await waitFor(() => {
    const call = request.mock.calls.find(([path]) =>
      path.endsWith("/keywords/bulk-organize"),
    );
    expect(JSON.parse(String(call?.[1].body))).toEqual({
      keyword_ids: ["keyword-1"],
      operation: "assign_group",
      group_id: "group-1",
    });
  });
  fireEvent.click(screen.getByRole("button", { name: "Manage Groups & Tags" }));
  expect(
    await screen.findByRole("heading", { name: "Manage Keyword organization" }),
  ).toBeVisible();
  expect(screen.getByDisplayValue("Brand")).toBeVisible();
  expect(screen.getByDisplayValue("Priority")).toBeVisible();
});

it("bulk adds cleaned keyword lines and displays counts", async () => {
  detailApi();
  view(<ProjectDetail projectId="project-1" />);
  await screen.findByText("rank tracker");
  fireEvent.click(screen.getByRole("button", { name: "Bulk Add" }));
  fireEvent.change(screen.getByLabelText("Keywords, one per line"), {
    target: { value: "one\ntwo\none" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Bulk add keywords" }));
  expect(await screen.findByText(/2 keywords added/)).toHaveTextContent(
    "1 duplicates",
  );
});

it("updates Project SERP settings without default fields", async () => {
  detailApi();
  view(<ProjectDetail projectId="project-1" />);
  await screen.findByText("rank tracker");
  fireEvent.change(screen.getByLabelText("Project name"), {
    target: { value: "Renamed" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Project settings" }));
  await waitFor(() =>
    expect(screen.getByText("Project settings saved.")).toBeVisible(),
  );
  const call = request.mock.calls.find(
    ([path, options]) =>
      path === "/api/v1/projects/project-1" && options?.method === "PATCH",
  );
  const body = JSON.parse(String(call?.[1].body));
  expect(body).toHaveProperty("country_code", "VN");
  expect(body).toHaveProperty("language_code", "vi");
  expect(body).not.toHaveProperty("default_country_code");
  expect(body).not.toHaveProperty("domain");
});

it("saves selected country and regional language codes from Project settings", async () => {
  detailApi();
  view(<ProjectDetail projectId="project-1" />);
  const country = await screen.findByRole("combobox", { name: "Country" });
  const language = screen.getByRole("combobox", { name: "Language" });
  expect(country).toHaveValue("Vietnam (VN)");
  expect(language).toHaveValue("Vietnamese (vi)");
  fireEvent.change(country, { target: { value: "US" } });
  fireEvent.click(screen.getByRole("option", { name: "United States (US)" }));
  fireEvent.change(language, { target: { value: "en-GB" } });
  fireEvent.click(
    screen.getByRole("option", { name: "English (United Kingdom) (en-GB)" }),
  );
  fireEvent.submit(screen.getByRole("form", { name: "Project settings" }));
  await screen.findByText("Project settings saved.");
  const call = request.mock.calls.find(
    ([path, options]) =>
      path === "/api/v1/projects/project-1" && options?.method === "PATCH",
  );
  expect(JSON.parse(String(call?.[1].body))).toMatchObject({
    country_code: "US",
    language_code: "en-GB",
  });
});

it("preserves saved locale codes outside the catalog when editing other settings", async () => {
  detailApi({ country_code: "GB", language_code: "zh-Hant" });
  view(<ProjectDetail projectId="project-1" />);
  const country = await screen.findByRole("combobox", { name: "Country" });
  expect(country).toHaveValue("United Kingdom (GB)");
  expect(screen.getByRole("combobox", { name: "Language" })).toHaveValue(
    "zh-Hant (current value)",
  );
  fireEvent.change(screen.getByLabelText("Project name"), {
    target: { value: "Renamed" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Project settings" }));
  await screen.findByText("Project settings saved.");
  const call = request.mock.calls.find(
    ([path, options]) =>
      path === "/api/v1/projects/project-1" && options?.method === "PATCH",
  );
  expect(JSON.parse(String(call?.[1].body))).toMatchObject({
    name: "Renamed",
    country_code: "GB",
    language_code: "zh-Hant",
  });
});
