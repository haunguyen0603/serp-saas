"use client";

import {
  Alert,
  Button,
  Card,
  Dialog,
  Input,
  Select,
  Skeleton,
  StatCard,
} from "@/design-system/ui";
import {
  getOrganizationAnalytics,
  projectAnalytics,
} from "@/features/analytics/api";
import type { AnalyticsRange } from "@/features/analytics/types";
import { rankingExplorerKeys } from "@/features/ranking-explorer/api";
import { ApiError } from "@/lib/api/client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import {
  createKeywordOrganization,
  deleteKeywordOrganization,
  listKeywordGroups,
  listKeywordTags,
  projectKeys,
  updateKeywordOrganization,
} from "./api";
import { useProtectedAuth } from "./protected";
import type { KeywordOrganization, Project } from "./types";

type Kind = "groups" | "tags";

const errorMessage = (error: unknown) =>
  error instanceof ApiError
    ? error.message
    : "The organization could not be saved.";

export function KeywordOrganizationManager({
  project,
  open,
  onClose,
}: {
  project: Project;
  open: boolean;
  onClose: () => void;
}) {
  const auth = useProtectedAuth();
  const client = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState("");
  const [range, setRange] = useState<AnalyticsRange>("30d");
  const groups = useQuery({
    queryKey: projectKeys.groups(project.id),
    queryFn: () => listKeywordGroups(auth.request, project.id),
    enabled: auth.isAuthenticated && open,
  });
  const tags = useQuery({
    queryKey: projectKeys.tags(project.id),
    queryFn: () => listKeywordTags(auth.request, project.id),
    enabled: auth.isAuthenticated && open,
  });
  const invalidate = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: projectKeys.groups(project.id) }),
      client.invalidateQueries({ queryKey: projectKeys.tags(project.id) }),
      client.invalidateQueries({ queryKey: projectKeys.keywords(project.id) }),
      client.invalidateQueries({
        queryKey: rankingExplorerKeys.all(project.id),
      }),
      client.invalidateQueries({ queryKey: projectAnalytics.all(project.id) }),
    ]);
  };
  const create = useMutation({
    mutationFn: ({ kind, name }: { kind: Kind; name: string }) =>
      createKeywordOrganization(auth.request, project.id, kind, name),
    onSuccess: invalidate,
    onError: (failure) => setError(errorMessage(failure)),
  });
  const rename = useMutation({
    mutationFn: ({
      kind,
      id,
      name,
    }: {
      kind: Kind;
      id: string;
      name: string;
    }) => updateKeywordOrganization(auth.request, project.id, kind, id, name),
    onSuccess: invalidate,
    onError: (failure) => setError(errorMessage(failure)),
  });
  const remove = useMutation({
    mutationFn: ({ kind, id }: { kind: Kind; id: string }) =>
      deleteKeywordOrganization(auth.request, project.id, kind, id),
    onSuccess: async (_, variables) => {
      if (scope === `${variables.kind}:${variables.id}`) setScope("");
      await invalidate();
    },
    onError: (failure) => setError(errorMessage(failure)),
  });
  const analytics = useQuery({
    queryKey: projectAnalytics.organization(
      project.id,
      scope,
      project.device,
      range,
    ),
    queryFn: () => {
      const [kind, id] = scope.split(":");
      return getOrganizationAnalytics(
        auth.request,
        project.id,
        project.device,
        range,
        kind === "groups" ? { group_id: id } : { tag_id: id },
      );
    },
    enabled: auth.isAuthenticated && open && !!scope,
    retry: false,
  });

  const createForm = (kind: Kind, label: string) => (
    <form
      className="mt-3 flex flex-wrap gap-2"
      aria-label={`Create ${label}`}
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError(null);
        const form = event.currentTarget;
        const name = String(new FormData(form).get("name") ?? "");
        create.mutate({ kind, name }, { onSuccess: () => form.reset() });
      }}
    >
      <Input
        name="name"
        required
        maxLength={kind === "groups" ? 80 : 40}
        aria-label={`${label} name`}
        placeholder={`New ${label} name`}
      />
      <Button type="submit" disabled={create.isPending}>
        Add {label}
      </Button>
    </form>
  );

  const catalog = (
    kind: Kind,
    label: string,
    items: KeywordOrganization[] | undefined,
  ) => (
    <Card>
      <h3 className="text-lg font-semibold">{label}s</h3>
      {createForm(kind, label)}
      <div className="mt-4 grid gap-3">
        {items?.map((item) => (
          <form
            key={item.id}
            className="flex flex-wrap items-center gap-2"
            aria-label={`Rename ${item.name}`}
            onSubmit={(event) => {
              event.preventDefault();
              const name = String(
                new FormData(event.currentTarget).get("name") ?? "",
              );
              rename.mutate({ kind, id: item.id, name });
            }}
          >
            <Input
              name="name"
              defaultValue={item.name}
              required
              maxLength={kind === "groups" ? 80 : 40}
              aria-label={`${label} name`}
            />
            <span className="text-sm text-secondary">
              {item.active_keyword_count} active
            </span>
            <Button size="sm" type="submit" disabled={rename.isPending}>
              Rename
            </Button>
            <Button
              size="sm"
              type="button"
              variant="danger"
              confirmation={`Delete ${label} “${item.name}”? This removes its organization from ${item.active_keyword_count} active Keywords without deleting Keywords or history.`}
              onClick={() => remove.mutate({ kind, id: item.id })}
            >
              Delete
            </Button>
          </form>
        ))}
        {!items?.length && (
          <p className="text-sm text-secondary">
            No {label.toLowerCase()}s yet.
          </p>
        )}
      </div>
    </Card>
  );

  const summary = analytics.data;
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Manage Keyword organization"
      className="keyword-organization-dialog"
    >
      <p className="text-secondary">
        Groups are exclusive; Tags can overlap. Counts include active Keywords.
      </p>
      {error && <Alert className="mt-4 text-danger">{error}</Alert>}
      {(groups.isPending || tags.isPending) && (
        <Skeleton label="Loading Groups and Tags…" />
      )}
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {catalog("groups", "Group", groups.data?.items)}
        {catalog("tags", "Tag", tags.data?.items)}
      </div>
      <Card className="mt-5">
        <h3 className="text-lg font-semibold">Organization performance</h3>
        <p className="mt-1 text-sm text-secondary">
          Reuses persisted, successful ranking observations and never runs a
          check.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label>
            Group or Tag
            <Select
              value={scope}
              onChange={(event) => setScope(event.target.value)}
            >
              <option value="">Select a scope</option>
              <optgroup label="Groups">
                {groups.data?.items.map((item) => (
                  <option key={item.id} value={`groups:${item.id}`}>
                    {item.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Tags">
                {tags.data?.items.map((item) => (
                  <option key={item.id} value={`tags:${item.id}`}>
                    {item.name}
                  </option>
                ))}
              </optgroup>
            </Select>
          </label>
          <label>
            Comparison range
            <Select
              value={range}
              onChange={(event) =>
                setRange(event.target.value as AnalyticsRange)
              }
            >
              <option value="7d">7 days</option>
              <option value="30d">30 days</option>
              <option value="90d">90 days</option>
            </Select>
          </label>
        </div>
        {analytics.isPending && scope && (
          <Skeleton label="Loading organization performance…" />
        )}
        {analytics.isError && (
          <Alert className="mt-4">
            Organization performance could not be loaded.
          </Alert>
        )}
        {summary && (
          <div className="analytics-kpis mt-4">
            <StatCard label="Active Keywords" value={summary.total_keywords} />
            <StatCard label="Top 3" value={summary.top_3} />
            <StatCard label="Top 10" value={summary.top_10} />
            <StatCard label="Improved" value={summary.improved} />
            <StatCard label="Declined" value={summary.declined} />
            <StatCard label="Unchanged" value={summary.unchanged} />
            <StatCard
              label={`Not found in Top ${summary.distribution.effective_depth}`}
              value={summary.not_found_in_depth}
            />
            <StatCard
              label="Entered checked depth"
              value={summary.entered_checked_depth}
            />
            <StatCard
              label="Left checked depth"
              value={summary.left_checked_depth}
            />
          </div>
        )}
      </Card>
      <Button className="mt-5" onClick={onClose}>
        Close
      </Button>
    </Dialog>
  );
}
