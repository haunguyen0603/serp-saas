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
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
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
  expect(body).not.toHaveProperty("domain");
  expect(body).not.toHaveProperty("provider");
});

function detailApi() {
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === "/api/v1/projects/project-1" && !options) return project;
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

it("renders query-only Keyword columns and project-wide settings warning", async () => {
  detailApi();
  view(<ProjectDetail projectId="project-1" />);
  await screen.findByText("rank tracker");
  const table = screen.getByRole("table");
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
      expect.objectContaining({ body: '{"keyword":"new keyword"}' }),
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
    });
  });
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
  expect(body).not.toHaveProperty("default_country_code");
  expect(body).not.toHaveProperty("domain");
});
