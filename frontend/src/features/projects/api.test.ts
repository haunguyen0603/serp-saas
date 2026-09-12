import { expect, it, vi } from "vitest";
import type { AuthenticatedRequest } from "@/features/auth/session";
import {
  bulkCreateKeywords,
  createKeyword,
  createProject,
  deleteKeyword,
  deleteProject,
  getKeyword,
  getProject,
  listKeywords,
  listProjects,
  updateKeyword,
  updateProject,
} from "./api";
const requester = () =>
  vi.fn().mockResolvedValue({}) as unknown as AuthenticatedRequest;

it("uses the refactored authenticated Project contract", async () => {
  const request = requester();
  await createProject(request, {
    name: "Vietnam Desktop",
    search_engine: "google",
    country_code: "VN",
    language_code: "vi",
    device: "desktop",
    location: null,
    keywords: ["one", "two"],
  });
  await listProjects(request, { status: "all", search: "Vietnam", limit: 20 });
  await getProject(request, "project-1");
  await updateProject(request, "project-1", { status: "archived" });
  await deleteProject(request, "project-1");
  const calls = vi.mocked(request).mock.calls;
  expect(calls.map((call) => call[0])).toEqual([
    "/api/v1/projects",
    "/api/v1/projects?status=all&search=Vietnam&limit=20",
    "/api/v1/projects/project-1",
    "/api/v1/projects/project-1",
    "/api/v1/projects/project-1",
  ]);
  const body = JSON.parse(String(calls[0][1]?.body));
  expect(body).not.toHaveProperty("user_id");
  expect(body).not.toHaveProperty("domain");
  expect(body.keywords).toEqual(["one", "two"]);
});

it("sends query-only Keyword payloads and filters", async () => {
  const request = requester();
  await createKeyword(request, "project-1", { keyword: "seo" });
  await bulkCreateKeywords(request, "project-1", { keywords: ["one", "two"] });
  await listKeywords(request, "project-1", {
    active: "false",
    search: "seo",
    cursor: "opaque",
  });
  await getKeyword(request, "project-1", "keyword-1");
  await updateKeyword(request, "project-1", "keyword-1", {
    keyword: "new",
    active: false,
  });
  await deleteKeyword(request, "project-1", "keyword-1");
  const calls = vi.mocked(request).mock.calls;
  expect(calls.map((call) => call[0])).toEqual([
    "/api/v1/projects/project-1/keywords",
    "/api/v1/projects/project-1/keywords/bulk",
    "/api/v1/projects/project-1/keywords?active=false&search=seo&cursor=opaque",
    "/api/v1/projects/project-1/keywords/keyword-1",
    "/api/v1/projects/project-1/keywords/keyword-1",
    "/api/v1/projects/project-1/keywords/keyword-1",
  ]);
  expect(JSON.parse(String(calls[4][1]?.body))).toEqual({
    keyword: "new",
    active: false,
  });
});
