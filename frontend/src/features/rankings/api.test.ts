import { expect, it, vi } from "vitest";
import type { AuthenticatedRequest } from "@/features/auth/session";
import {
  checkKeyword,
  checkProject,
  getLatestRankings,
  getRankCheck,
  listRankChecks,
} from "./api";

it("uses only authenticated nested ranking routes and typed request bodies", async () => {
  const request = vi
    .fn()
    .mockResolvedValue({}) as unknown as AuthenticatedRequest;
  await checkProject(request, "project-1", ["keyword-1"]);
  await checkKeyword(request, "project-1", "keyword-1");
  await listRankChecks(request, "project-1", "keyword-1", {
    status: "succeeded",
    limit: 25,
    cursor: "opaque",
  });
  await getRankCheck(request, "project-1", "keyword-1", "check-1");
  await getLatestRankings(request, "project-1");
  const calls = vi.mocked(request).mock.calls;
  expect(calls.map((call) => call[0])).toEqual([
    "/api/v1/projects/project-1/rank-checks",
    "/api/v1/projects/project-1/keywords/keyword-1/rank-checks",
    "/api/v1/projects/project-1/keywords/keyword-1/rank-checks?status=succeeded&limit=25&cursor=opaque",
    "/api/v1/projects/project-1/keywords/keyword-1/rank-checks/check-1",
    "/api/v1/projects/project-1/rankings/latest",
  ]);
  expect(JSON.parse(String(calls[0][1]?.body))).toEqual({
    keyword_ids: ["keyword-1"],
  });
  expect(JSON.parse(String(calls[1][1]?.body))).toEqual({});
  expect(String(calls[0][1]?.body)).not.toContain("provider");
  expect(String(calls[1][1]?.body)).not.toContain("provider");
  expect(calls[0][1]).not.toHaveProperty("api_key");
});
