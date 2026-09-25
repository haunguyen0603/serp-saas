"use client";
import {
  Alert,
  Badge,
  Button,
  Dialog,
  Input,
  Select,
  Skeleton,
  Table,
  StatusBadge,
  EmptyState,
  Textarea,
  Toast,
} from "@/design-system/ui";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import Link from "next/link";
import { Fragment, useState, type FormEvent } from "react";
import { rankingExplorerKeys } from "@/features/ranking-explorer/api";
import {
  checkKeyword,
  checkProject,
  getLatestRankings,
  getRankCheck,
  listRankChecks,
  rankingKeys,
} from "@/features/rankings/api";
import { RankCheckDetail } from "@/features/rankings/rank-check-detail";
import { RankCheckHistory } from "@/features/rankings/rank-check-history";
import { BatchPanel, SchedulePanel } from "@/features/rankings/batch-panel";
import { batchKey } from "@/features/rankings/batches";
import type { RankCheck } from "@/features/rankings/types";
import {
  getKeywordRankingHistory,
  projectAnalytics,
} from "@/features/analytics/api";
import type { AnalyticsRange } from "@/features/analytics/types";
import {
  listTrackedSites,
  trackedSiteKeys,
} from "@/features/tracked-sites/api";
import { ApiError } from "@/lib/api/client";
import {
  bulkCreateKeywords,
  bulkOrganizeKeywords,
  createKeyword,
  deleteKeyword,
  listKeywords,
  listKeywordGroups,
  listKeywordTags,
  projectKeys,
  updateKeyword,
} from "./api";
import { KeywordOrganizationManager } from "./keyword-organization-manager";
import { useProtectedAuth } from "./protected";
import type {
  Keyword,
  KeywordBulkResult,
  KeywordBulkOperation,
  KeywordUpdate,
  Project,
} from "./types";

const field = "";
const message = (error: unknown, fallback: string) =>
  error instanceof ApiError ? error.message : fallback;

export function KeywordManager({ project }: { project: Project }) {
  const auth = useProtectedAuth();
  const queryClient = useQueryClient();
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState<"true" | "false" | "all">("true");
  const [groupFilter, setGroupFilter] = useState("");
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [tagMatch, setTagMatch] = useState<"any" | "all">("any");
  const [organizationOpen, setOrganizationOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkOperation, setBulkOperation] =
    useState<KeywordBulkOperation>("assign_group");
  const [bulkGroupId, setBulkGroupId] = useState("");
  const [bulkTagIds, setBulkTagIds] = useState<string[]>([]);
  const [panel, setPanel] = useState<"single" | "bulk" | null>(null);
  const [editing, setEditing] = useState<Keyword | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyKeywordId, setHistoryKeywordId] = useState<string | null>(null);
  const [historyPage, setHistoryPage] = useState(0);
  const [historyCursors, setHistoryCursors] = useState<(string | null)[]>([
    null,
  ]);
  const [detailCheck, setDetailCheck] = useState<RankCheck | null>(null);
  const [historyRange, setHistoryRange] = useState<AnalyticsRange>("30d");
  const [historySiteId, setHistorySiteId] = useState<string | null>(null);
  const filters = {
    search,
    active,
    group_id: groupFilter || undefined,
    tag_ids: tagFilter.length ? tagFilter.join(",") : undefined,
    tag_match: tagMatch,
    limit: 50,
  } as const;
  const keywords = useInfiniteQuery({
    queryKey: projectKeys.keywordList(project.id, filters),
    queryFn: ({ pageParam }) =>
      listKeywords(auth.request, project.id, { ...filters, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: auth.isAuthenticated,
  });
  const latest = useQuery({
    queryKey: rankingKeys.latest(project.id),
    queryFn: () => getLatestRankings(auth.request, project.id),
    enabled: auth.isAuthenticated,
  });
  const groups = useQuery({
    queryKey: projectKeys.groups(project.id),
    queryFn: () => listKeywordGroups(auth.request, project.id),
    enabled: auth.isAuthenticated,
  });
  const tags = useQuery({
    queryKey: projectKeys.tags(project.id),
    queryFn: () => listKeywordTags(auth.request, project.id),
    enabled: auth.isAuthenticated,
  });
  const items = keywords.data?.pages.flatMap((page) => page.items) ?? [];
  const historyKeyword =
    items.find((item) => item.id === historyKeywordId) ?? null;
  const historyCursor = historyCursors[historyPage] ?? null;
  const history = useQuery({
    queryKey: [
      ...rankingKeys.history(project.id, historyKeyword?.id ?? ""),
      historyCursor ?? "first",
      10,
    ],
    queryFn: () =>
      listRankChecks(auth.request, project.id, historyKeyword?.id ?? "", {
        limit: 10,
        cursor: historyCursor,
      }),
    enabled: auth.isAuthenticated && historyKeyword !== null,
    staleTime: 30_000,
  });
  const trackedSites = useQuery({
    queryKey: trackedSiteKeys.list({ status: "active", limit: 200 }),
    queryFn: () =>
      listTrackedSites(auth.request, { status: "active", limit: 200 }),
    enabled: auth.isAuthenticated && historyKeyword !== null,
    staleTime: 60_000,
  });
  const selectedHistorySiteId =
    historySiteId ?? trackedSites.data?.items[0]?.id ?? null;
  const chart = useQuery({
    queryKey: projectAnalytics.history(
      project.id,
      historyKeyword?.id ?? "",
      selectedHistorySiteId ?? "",
      project.device,
      historyRange,
    ),
    queryFn: () =>
      getKeywordRankingHistory(
        auth.request,
        project.id,
        historyKeyword?.id ?? "",
        selectedHistorySiteId ?? "",
        project.device,
        historyRange,
      ),
    enabled:
      auth.isAuthenticated &&
      historyKeyword !== null &&
      selectedHistorySiteId !== null,
    staleTime: 30_000,
  });
  const detail = useQuery({
    queryKey: rankingKeys.detail(
      project.id,
      historyKeyword?.id ?? "",
      detailCheck?.id ?? "",
    ),
    queryFn: () =>
      getRankCheck(
        auth.request,
        project.id,
        historyKeyword?.id ?? "",
        detailCheck?.id ?? "",
      ),
    enabled:
      auth.isAuthenticated && historyKeyword !== null && detailCheck !== null,
  });
  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: projectKeys.keywords(project.id),
      }),
      queryClient.invalidateQueries({
        queryKey: projectKeys.detail(project.id),
      }),
      queryClient.invalidateQueries({
        queryKey: projectKeys.groups(project.id),
      }),
      queryClient.invalidateQueries({ queryKey: projectKeys.tags(project.id) }),
      queryClient.invalidateQueries({
        queryKey: rankingExplorerKeys.all(project.id),
      }),
      queryClient.invalidateQueries({
        queryKey: projectAnalytics.all(project.id),
      }),
    ]);
  };
  const single = useMutation({
    mutationFn: (input: {
      keyword: string;
      group_id: string | null;
      tag_ids: string[];
    }) => createKeyword(auth.request, project.id, input),
    onSuccess: async () => {
      setPanel(null);
      setNotice("Keyword added.");
      await invalidate();
    },
  });
  const bulk = useMutation({
    mutationFn: (lines: string[]) =>
      bulkCreateKeywords(auth.request, project.id, { keywords: lines }),
    onSuccess: async (result: KeywordBulkResult) => {
      setNotice(
        `${result.created} keywords added. ${result.skipped_duplicates} duplicates and ${result.skipped_empty} empty lines skipped.`,
      );
      await invalidate();
    },
  });
  const update = useMutation({
    mutationFn: ({ id, input }: { id: string; input: KeywordUpdate }) =>
      updateKeyword(auth.request, project.id, id, input),
    onSuccess: async () => {
      setEditing(null);
      await invalidate();
    },
  });
  const organize = useMutation({
    mutationFn: () => {
      const base = {
        keyword_ids: [...selected],
        operation: bulkOperation,
      };
      if (bulkOperation === "assign_group")
        return bulkOrganizeKeywords(auth.request, project.id, {
          ...base,
          group_id: bulkGroupId || null,
        });
      if (
        bulkOperation === "add_tags" ||
        bulkOperation === "remove_tags" ||
        bulkOperation === "replace_tags"
      )
        return bulkOrganizeKeywords(auth.request, project.id, {
          ...base,
          tag_ids: bulkTagIds,
        });
      return bulkOrganizeKeywords(auth.request, project.id, base);
    },
    onSuccess: async (result) => {
      setNotice(
        `${result.affected_keyword_count} of ${result.selected_count} selected Keywords updated.`,
      );
      setSelected(new Set());
      await invalidate();
    },
    onError: (failure) =>
      setError(message(failure, "Selected Keywords could not be updated.")),
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteKeyword(auth.request, project.id, id),
    onSuccess: invalidate,
    onError: (failure) =>
      setError(message(failure, "Keyword could not be deleted.")),
  });
  const projectCheck = useMutation({
    mutationFn: () => checkProject(auth.request, project.id),
    onSuccess: async (result) => {
      setNotice("Ranking checks queued.");
      setSelectedBatch(result.batch_id);
      await queryClient.invalidateQueries({ queryKey: batchKey(project.id) });
    },
    onError: (failure) =>
      setError(message(failure, "Project rankings could not be checked.")),
  });
  const keywordCheck = useMutation({
    mutationFn: (keywordId: string) =>
      checkKeyword(auth.request, project.id, keywordId),
    onSuccess: async (result) => {
      setNotice("Keyword check queued.");
      setSelectedBatch(result.batch_id);
      await queryClient.invalidateQueries({ queryKey: batchKey(project.id) });
    },
    onError: (failure) =>
      setError(message(failure, "Keyword ranking could not be checked.")),
  });
  const latestByKeyword = new Map(
    latest.data?.items.map((item) => [item.keyword_id, item.latest_check]) ??
      [],
  );
  function submitSingle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const values = new FormData(form);
    single.mutate(
      {
        keyword: String(values.get("keyword") ?? ""),
        group_id: String(values.get("group_id") ?? "") || null,
        tag_ids: values.getAll("tag_ids").map(String),
      },
      {
        onError: (failure) =>
          setError(message(failure, "Keyword could not be added.")),
      },
    );
  }
  function submitBulk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const lines = String(
      new FormData(event.currentTarget).get("keywords") ?? "",
    ).split(/\r?\n/);
    if (lines.length > 1000) {
      setError("A bulk request may contain at most 1000 keywords.");
      return;
    }
    bulk.mutate(lines, {
      onError: (failure) =>
        setError(message(failure, "Keywords could not be added.")),
    });
  }
  function toggleHistory(keyword: Keyword) {
    const opening = historyKeywordId !== keyword.id;
    setHistoryKeywordId(opening ? keyword.id : null);
    setHistoryPage(0);
    setHistoryCursors([null]);
    setDetailCheck(null);
    setHistorySiteId(null);
  }
  return (
    <section id="keywords">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold">
          Keywords{" "}
          <span className="text-base text-secondary">
            ({project.keyword_count})
          </span>
        </h2>
        <div className="flex flex-wrap gap-3">
          <Button
            variant="primary"
            disabled={project.status !== "active" || projectCheck.isPending}
            onClick={() => {
              setError(null);
              projectCheck.mutate();
            }}
          >
            {projectCheck.isPending ? "Queueing…" : "Check Rankings"}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setPanel(panel === "single" ? null : "single")}
          >
            Add Keyword
          </Button>
          <Button onClick={() => setPanel(panel === "bulk" ? null : "bulk")}>
            Bulk Add
          </Button>
          <Button onClick={() => setOrganizationOpen(true)}>
            Manage Groups &amp; Tags
          </Button>
        </div>
      </div>
      {panel === "single" && (
        <form
          aria-label="Add keyword"
          onSubmit={submitSingle}
          className="mt-5 rounded-xl border border-border p-5"
        >
          <label>
            Keyword
            <Input className={field} name="keyword" required maxLength={512} />
          </label>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label>
              Group
              <Select name="group_id" defaultValue="">
                <option value="">No Group</option>
                {groups.data?.items.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </Select>
            </label>
            <label>
              Tags
              <Select name="tag_ids" multiple aria-label="Tags for new Keyword">
                {tags.data?.items.map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
              </Select>
            </label>
          </div>
          <Button
            disabled={single.isPending}
            className="mt-4"
            variant="primary"
          >
            {single.isPending ? "Adding…" : "Add keyword"}
          </Button>
        </form>
      )}
      {panel === "bulk" && (
        <form
          aria-label="Bulk add keywords"
          onSubmit={submitBulk}
          className="mt-5 rounded-xl border border-border p-5"
        >
          <label>
            Keywords, one per line
            <Textarea
              className={`${field} min-h-40`}
              name="keywords"
              required
            />
          </label>
          <p className="mt-2 text-sm text-secondary">
            Maximum 1000 lines. Empty and duplicate lines are cleaned.
          </p>
          <Button disabled={bulk.isPending} className="mt-4" variant="primary">
            {bulk.isPending ? "Adding…" : "Add keywords"}
          </Button>
        </form>
      )}
      {error && <Alert className="mt-4 text-danger">{error}</Alert>}
      {notice && <Toast key={notice}>{notice}</Toast>}
      <div className="my-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <label>
          Search keywords
          <Input
            className={field}
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setSelected(new Set());
            }}
          />
        </label>
        <label>
          Keyword state
          <Select
            className={field}
            value={active}
            onChange={(event) => {
              setActive(event.target.value as typeof active);
              setSelected(new Set());
            }}
          >
            <option value="true">Active</option>
            <option value="false">Paused</option>
            <option value="all">All</option>
          </Select>
        </label>
        <label>
          Group
          <Select
            value={groupFilter}
            onChange={(event) => {
              setGroupFilter(event.target.value);
              setSelected(new Set());
            }}
          >
            <option value="">All Groups</option>
            <option value="none">No Group</option>
            {groups.data?.items.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </Select>
        </label>
        <label>
          Tags
          <Select
            multiple
            aria-label="Filter Tags"
            value={tagFilter}
            onChange={(event) => {
              setTagFilter(
                Array.from(
                  event.target.selectedOptions,
                  (option) => option.value,
                ),
              );
              setSelected(new Set());
            }}
          >
            {tags.data?.items.map((tag) => (
              <option key={tag.id} value={tag.id}>
                {tag.name}
              </option>
            ))}
          </Select>
        </label>
        <label>
          Tag matching
          <Select
            value={tagMatch}
            disabled={!tagFilter.length}
            onChange={(event) => {
              setTagMatch(event.target.value as "any" | "all");
              setSelected(new Set());
            }}
          >
            <option value="any">Any selected Tag</option>
            <option value="all">All selected Tags</option>
          </Select>
        </label>
      </div>
      {keywords.isPending && <Skeleton label="Loading keywords…" />}
      {keywords.isError && <Alert>Keywords could not be loaded.</Alert>}
      {editing && (
        <form
          aria-label="Edit keyword"
          className="mb-5 rounded-xl border border-brand p-5"
          onSubmit={(event) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            update.mutate({
              id: editing.id,
              input: {
                keyword: String(values.get("keyword") ?? ""),
                active: values.get("active") === "on",
                group_id: String(values.get("group_id") ?? "") || null,
                tag_ids: values.getAll("tag_ids").map(String),
              },
            });
          }}
        >
          <label>
            Edit keyword
            <Input
              className={field}
              name="keyword"
              defaultValue={editing.keyword}
              required
            />
          </label>
          <label className="mt-4 flex gap-3">
            <Input
              name="active"
              type="checkbox"
              defaultChecked={editing.active}
            />
            Active
          </label>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label>
              Group
              <Select name="group_id" defaultValue={editing.group?.id ?? ""}>
                <option value="">No Group</option>
                {groups.data?.items.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </Select>
            </label>
            <label>
              Tags
              <Select
                name="tag_ids"
                multiple
                defaultValue={editing.tags.map((tag) => tag.id)}
                aria-label="Keyword Tags"
              >
                {tags.data?.items.map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
              </Select>
            </label>
          </div>
          <Button className="mt-4" variant="primary">
            Save Keyword
          </Button>
          <Button
            type="button"
            className="ml-3"
            onClick={() => setEditing(null)}
          >
            Cancel
          </Button>
        </form>
      )}
      {!keywords.isPending && !keywords.isError && !items.length && (
        <EmptyState title="No keywords in this view">
          Add keywords to start tracking, or adjust the search and state
          filters.
        </EmptyState>
      )}
      {!!selected.size && (
        <div
          className="mb-4 rounded-xl border border-brand p-4"
          aria-label="Bulk Keyword actions"
        >
          <div className="flex flex-wrap items-end gap-3">
            <strong>{selected.size} selected on loaded rows</strong>
            <label>
              Operation
              <Select
                value={bulkOperation}
                onChange={(event) => {
                  setBulkOperation(event.target.value as KeywordBulkOperation);
                  setBulkTagIds([]);
                }}
              >
                <option value="assign_group">Assign Group</option>
                <option value="add_tags">Add Tags</option>
                <option value="remove_tags">Remove Tags</option>
                <option value="replace_tags">Replace all Tags</option>
                <option value="archive">Archive</option>
                <option value="restore">Restore</option>
              </Select>
            </label>
            {bulkOperation === "assign_group" && (
              <label>
                Group
                <Select
                  value={bulkGroupId}
                  onChange={(event) => setBulkGroupId(event.target.value)}
                >
                  <option value="">No Group</option>
                  {groups.data?.items.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </Select>
              </label>
            )}
            {["add_tags", "remove_tags", "replace_tags"].includes(
              bulkOperation,
            ) && (
              <label>
                Tags
                <Select
                  multiple
                  value={bulkTagIds}
                  aria-label="Bulk Tags"
                  onChange={(event) =>
                    setBulkTagIds(
                      Array.from(
                        event.target.selectedOptions,
                        (option) => option.value,
                      ),
                    )
                  }
                >
                  {tags.data?.items.map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.name}
                    </option>
                  ))}
                </Select>
              </label>
            )}
            <Button
              variant="primary"
              disabled={
                organize.isPending ||
                ((bulkOperation === "add_tags" ||
                  bulkOperation === "remove_tags") &&
                  !bulkTagIds.length)
              }
              confirmation={
                bulkOperation === "archive"
                  ? `Archive ${selected.size} selected Keywords? Future scheduled checks will skip them.`
                  : bulkOperation === "replace_tags"
                    ? `Replace every Tag on ${selected.size} selected Keywords? Existing Tags not selected here will be removed.`
                    : undefined
              }
              onClick={() => organize.mutate()}
            >
              {organize.isPending ? "Applying…" : "Apply"}
            </Button>
            <Button variant="ghost" onClick={() => setSelected(new Set())}>
              Clear selection
            </Button>
          </div>
        </div>
      )}
      <div id="rankings" className="overflow-x-auto">
        <Table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="p-3">
                <Input
                  type="checkbox"
                  aria-label="Select all loaded Keywords"
                  aria-checked={
                    selected.size > 0 && selected.size < items.length
                      ? "mixed"
                      : undefined
                  }
                  checked={!!items.length && selected.size === items.length}
                  onChange={(event) =>
                    setSelected(
                      event.target.checked
                        ? new Set(items.map((item) => item.id))
                        : new Set(),
                    )
                  }
                />
              </th>
              <th className="p-3">Keyword</th>
              <th className="p-3">Group</th>
              <th className="p-3">Tags</th>
              <th className="p-3">Status</th>
              <th className="p-3">Last checked</th>
              <th className="p-3">Tracked rankings</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const expanded = historyKeyword?.id === item.id;
              const historyRegionId = `keyword-history-${item.id}`;
              return (
                <Fragment key={item.id}>
                  <tr
                    id={`keyword-${item.id}`}
                    className="border-b border-border"
                  >
                    <td className="p-3" data-label="Select">
                      <Input
                        type="checkbox"
                        aria-label={`Select ${item.keyword}`}
                        checked={selected.has(item.id)}
                        onChange={(event) =>
                          setSelected((current) => {
                            const next = new Set(current);
                            if (event.target.checked) next.add(item.id);
                            else next.delete(item.id);
                            return next;
                          })
                        }
                      />
                    </td>
                    <td className="p-3" data-label="Keyword">
                      <button
                        type="button"
                        className="ui-text-link keyword-history-trigger text-sm font-medium"
                        aria-expanded={expanded}
                        aria-controls={historyRegionId}
                        onClick={() => toggleHistory(item)}
                      >
                        <span>{item.keyword}</span>
                        <span aria-hidden="true">{expanded ? "▴" : "▸"}</span>
                      </button>
                    </td>
                    <td className="p-3" data-label="Group">
                      {item.group ? <Badge>{item.group.name}</Badge> : "—"}
                    </td>
                    <td className="p-3" data-label="Tags">
                      <div className="flex flex-wrap gap-1">
                        {item.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag.id} title={tag.name}>
                            {tag.name}
                          </Badge>
                        ))}
                        {item.tags.length > 3 && (
                          <Badge
                            title={item.tags
                              .slice(3)
                              .map((tag) => tag.name)
                              .join(", ")}
                          >
                            +{item.tags.length - 3}
                          </Badge>
                        )}
                        {!item.tags.length && "—"}
                      </div>
                    </td>
                    <td className="p-3" data-label="Status">
                      <StatusBadge status={item.active ? "active" : "paused"} />
                    </td>
                    <td className="p-3" data-label="Last checked">
                      {(() => {
                        const check = latestByKeyword.get(item.id);
                        if (!check) return "Never checked";
                        return new Date(check.requested_at).toLocaleString();
                      })()}
                    </td>
                    <td className="p-3" data-label="Tracked rankings">
                      {(() => {
                        const check = latestByKeyword.get(item.id);
                        if (!check) return "—";
                        if (check.status === "failed") return "Check failed";
                        if (
                          check.status === "pending" ||
                          check.status === "running"
                        )
                          return "Running";
                        if (!check.rankings.length)
                          return `Not found in Top ${check.result_limit}`;
                        return (
                          <div className="flex flex-wrap gap-2">
                            {check.rankings.map((ranking) => {
                              const label = `${ranking.matched_domain} #${ranking.position}`;
                              return ranking.tracked_site_id ? (
                                <Link
                                  key={`${ranking.tracked_site_id}:${ranking.position}`}
                                  className="ui-text-link"
                                  href={`/app/tracked-sites/${ranking.tracked_site_id}`}
                                >
                                  {label}
                                </Link>
                              ) : (
                                <span
                                  key={`${ranking.tracked_site_name}:${ranking.position}`}
                                >
                                  {label}
                                </span>
                              );
                            })}
                          </div>
                        );
                      })()}
                    </td>
                    <td className="p-3" data-label="Actions">
                      <Button
                        className="mr-3"
                        disabled={
                          !item.active ||
                          (keywordCheck.isPending &&
                            keywordCheck.variables === item.id)
                        }
                        onClick={() => {
                          setError(null);
                          keywordCheck.mutate(item.id);
                        }}
                      >
                        {keywordCheck.isPending &&
                        keywordCheck.variables === item.id
                          ? "Queueing…"
                          : "Check now"}
                      </Button>
                      <Button className="mr-3" onClick={() => setEditing(item)}>
                        Edit
                      </Button>
                      <Button
                        size="md"
                        onClick={() =>
                          update.mutate({
                            id: item.id,
                            input: { active: !item.active },
                          })
                        }
                      >
                        {item.active ? "Pause" : "Resume"}
                      </Button>
                      <Button
                        variant="danger"
                        confirmation="Delete this Keyword? Its checks will stop. Keywords with ranking history must be paused instead."
                        onClick={() => remove.mutate(item.id)}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="keyword-history-row">
                      <td className="keyword-history-cell" colSpan={8}>
                        <RankCheckHistory
                          id={historyRegionId}
                          keyword={item.keyword}
                          checks={history.data?.items ?? []}
                          loading={history.isPending}
                          error={history.isError}
                          page={historyPage}
                          hasNextPage={history.data?.has_more ?? false}
                          onPreviousPage={() => {
                            setHistoryPage((current) =>
                              Math.max(0, current - 1),
                            );
                            setDetailCheck(null);
                          }}
                          onNextPage={() => {
                            const cursor = history.data?.next_cursor;
                            if (!cursor) return;
                            setHistoryCursors((current) => [
                              ...current.slice(0, historyPage + 1),
                              cursor,
                            ]);
                            setHistoryPage((current) => current + 1);
                            setDetailCheck(null);
                          }}
                          onOpen={setDetailCheck}
                          onRetry={() => void history.refetch()}
                          chart={chart.data}
                          chartLoading={
                            chart.isPending && !!selectedHistorySiteId
                          }
                          chartError={chart.isError}
                          chartRange={historyRange}
                          trackedSites={
                            trackedSites.data?.items.map((site) => ({
                              id: site.id,
                              name: site.name,
                            })) ?? []
                          }
                          trackedSiteId={selectedHistorySiteId ?? ""}
                          onChartRangeChange={setHistoryRange}
                          onTrackedSiteChange={setHistorySiteId}
                          onChartRetry={() => void chart.refetch()}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </Table>
      </div>
      {keywords.hasNextPage && (
        <Button className="mt-5" onClick={() => void keywords.fetchNextPage()}>
          Load more keywords
        </Button>
      )}
      <Dialog
        open={detailCheck !== null}
        onClose={() => setDetailCheck(null)}
        title="Rank Check detail"
        className="rank-check-dialog"
      >
        {detail.isPending && detailCheck && (
          <Skeleton label="Loading Rank Check detail…" />
        )}
        {detail.isError && (
          <Alert>Rank Check detail could not be loaded.</Alert>
        )}
        {detail.data && <RankCheckDetail check={detail.data} />}
      </Dialog>
      <KeywordOrganizationManager
        project={project}
        open={organizationOpen}
        onClose={() => setOrganizationOpen(false)}
      />
      <BatchPanel
        projectId={project.id}
        selectedBatch={selectedBatch}
        onSelect={setSelectedBatch}
      />
      <SchedulePanel
        projectId={project.id}
        archived={project.status !== "active"}
        device={project.device}
      />
    </section>
  );
}
