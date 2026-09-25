"use client";

import {
  Alert,
  Badge,
  Button,
  Card,
  CursorPagination,
  Input,
  PageHeader,
  Select,
  Skeleton,
  StatCard,
  StatusBadge,
  Table,
} from "@/design-system/ui";
import { useProtectedAuth } from "@/features/projects/protected";
import {
  getProject,
  listKeywordGroups,
  listKeywordTags,
  projectKeys,
} from "@/features/projects/api";
import {
  listTrackedSites,
  trackedSiteKeys,
} from "@/features/tracked-sites/api";
import { ApiError } from "@/lib/api/client";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import {
  createReport,
  createReportSchedule,
  deleteReportSchedule,
  listReports,
  listReportSchedules,
  previewReport,
  reportKeys,
  retryReport,
  updateReportSchedule,
} from "./api";
import type {
  GeneratedReport,
  ReportFilters,
  ReportPeriod,
  ReportScheduleInput,
  ReportScheduleUpdateInput,
  ReportType,
} from "./types";

const labels: Record<string, string> = {
  top_3: "Top 3",
  positions_4_10: "Positions 4–10",
  positions_11_20: "Positions 11–20",
  positions_21_50: "Positions 21–50",
  positions_51_100: "Positions 51–100",
  improved: "Improved",
  declined: "Declined",
  unchanged: "Unchanged",
  no_previous_data: "No previous data",
  never_checked: "Never checked",
};

const reportTypeLabels: Record<ReportType, string> = {
  comparison_csv: "Comparison CSV",
  history_csv: "History CSV",
  project_pdf: "Project PDF",
};

const formatDate = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      }).format(new Date(value)) + " UTC"
    : "—";

function ErrorMessage({ error }: { error: unknown }) {
  return (
    <Alert className="text-danger">
      {error instanceof ApiError
        ? error.message
        : "The report request could not be completed."}
    </Alert>
  );
}

export function ReportsPage({ projectId }: { projectId: string }) {
  const auth = useProtectedAuth();
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState<ReportPeriod>("30d");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [trackedSiteId, setTrackedSiteId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [tagMatch, setTagMatch] = useState<"any" | "all">("any");
  const [includeDetails, setIncludeDetails] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const recentPollCount = useRef(0);

  const filters = useMemo<ReportFilters>(
    () => ({
      period,
      start_date: period === "custom" ? startDate || undefined : undefined,
      end_date: period === "custom" ? endDate || undefined : undefined,
      tracked_site_id: trackedSiteId || undefined,
      keyword_group_id: groupId || undefined,
      keyword_tag_ids: tagIds,
      tag_match: tagMatch,
      include_keyword_details: includeDetails,
    }),
    [
      period,
      startDate,
      endDate,
      trackedSiteId,
      groupId,
      tagIds,
      tagMatch,
      includeDetails,
    ],
  );
  const validDates =
    period !== "custom" || (!!startDate && !!endDate && startDate <= endDate);

  const project = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => getProject(auth.request, projectId),
    enabled: auth.isAuthenticated,
    retry: false,
  });
  const groups = useQuery({
    queryKey: projectKeys.groups(projectId),
    queryFn: () => listKeywordGroups(auth.request, projectId),
    enabled: auth.isAuthenticated,
  });
  const tags = useQuery({
    queryKey: projectKeys.tags(projectId),
    queryFn: () => listKeywordTags(auth.request, projectId),
    enabled: auth.isAuthenticated,
  });
  const sites = useQuery({
    queryKey: trackedSiteKeys.list({ status: "active", limit: 100 }),
    queryFn: () =>
      listTrackedSites(auth.request, { status: "active", limit: 100 }),
    enabled: auth.isAuthenticated,
  });
  const preview = useQuery({
    queryKey: reportKeys.preview(projectId, filters),
    queryFn: () => previewReport(auth.request, projectId, filters),
    enabled: auth.isAuthenticated && validDates,
    retry: false,
  });
  const recent = useInfiniteQuery({
    queryKey: reportKeys.recent(projectId),
    queryFn: ({ pageParam }) => listReports(auth.request, projectId, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor,
    enabled: auth.isAuthenticated,
    refetchInterval: (query) => {
      const active = query.state.data?.pages.some((page) =>
        page.items.some((item) =>
          ["pending", "queued", "running"].includes(item.status),
        ),
      );
      if (!active) {
        recentPollCount.current = 0;
        return false;
      }
      if (recentPollCount.current >= 60) return false;
      recentPollCount.current += 1;
      return 2000;
    },
  });
  const schedules = useQuery({
    queryKey: reportKeys.schedules(projectId),
    queryFn: () => listReportSchedules(auth.request, projectId),
    enabled: auth.isAuthenticated,
  });

  const generate = useMutation({
    mutationFn: (reportType: ReportType) =>
      createReport(
        auth.request,
        projectId,
        reportType,
        filters,
        globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${reportType}`,
      ),
    onSuccess: async (report) => {
      recentPollCount.current = 0;
      setNotice(`${reportTypeLabels[report.report_type]} queued.`);
      await queryClient.invalidateQueries({
        queryKey: reportKeys.recent(projectId),
      });
    },
  });
  const retry = useMutation({
    mutationFn: (reportId: string) =>
      retryReport(auth.request, projectId, reportId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: reportKeys.recent(projectId) }),
  });

  async function download(report: GeneratedReport) {
    setNotice(null);
    try {
      const file = await auth.download(
        `/api/v1/projects/${projectId}/reports/${report.id}/download`,
      );
      const url = URL.createObjectURL(file.blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = file.filename;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setNotice(`${file.filename} downloaded.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Download failed.");
    }
  }

  if (!auth.isAuthenticated || project.isPending)
    return <Skeleton label="Loading Reports…" />;
  if (project.isError) return <ErrorMessage error={project.error} />;

  const reportItems = recent.data?.pages.flatMap((page) => page.items) ?? [];
  const depth = preview.data?.metrics.effective_depth ?? 10;
  const depthLabels: Record<string, string> = {
    ...labels,
    not_found_in_depth: `Not found in Top ${depth}`,
    entered_checked_depth: `Entered Top ${depth}`,
    left_checked_depth: `Left Top ${depth}`,
  };

  return (
    <main>
      <Link
        className="text-brand underline"
        href={`/app/projects/${projectId}`}
      >
        ← {project.data.name}
      </Link>
      <PageHeader
        eyebrow="Project reports"
        title="Reports"
        description="Export persisted ranking data or schedule a PDF summary. Reports never run a new rank check."
      />

      <Alert className="mb-6">
        Report uses existing ranking data; no new rank check is run and no
        keyword-check quota is consumed.
      </Alert>

      <Card className="report-config">
        <h2 className="text-xl font-semibold">Report configuration</h2>
        <div className="report-form-grid mt-5">
          <label>
            Reporting period
            <Select
              value={period}
              onChange={(event) =>
                setPeriod(event.target.value as ReportPeriod)
              }
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="custom">Custom UTC dates</option>
            </Select>
          </label>
          {period === "custom" && (
            <>
              <label>
                Start date (UTC)
                <Input
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                />
              </label>
              <label>
                End date (UTC)
                <Input
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                />
              </label>
            </>
          )}
          <label>
            Tracked Site
            <Select
              value={trackedSiteId}
              onChange={(event) => setTrackedSiteId(event.target.value)}
            >
              <option value="">All active Tracked Sites</option>
              {sites.data?.items.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Keyword Group
            <Select
              value={groupId}
              onChange={(event) => setGroupId(event.target.value)}
            >
              <option value="">All Groups</option>
              {groups.data?.items.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Keyword Tags
            <Select
              multiple
              size={Math.min(5, Math.max(2, tags.data?.items.length ?? 2))}
              value={tagIds}
              onChange={(event) =>
                setTagIds(
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
          <label>
            Tag matching
            <Select
              value={tagMatch}
              disabled={tagIds.length < 2}
              onChange={(event) =>
                setTagMatch(event.target.value as "any" | "all")
              }
            >
              <option value="any">ANY selected tag</option>
              <option value="all">ALL selected tags</option>
            </Select>
          </label>
          <label className="report-checkbox">
            <Input
              type="checkbox"
              checked={includeDetails}
              onChange={(event) => setIncludeDetails(event.target.checked)}
            />
            Include keyword details in PDF
          </label>
        </div>
        {!validDates && (
          <Alert className="mt-4 text-danger">
            Choose a start date on or before the end date.
          </Alert>
        )}
      </Card>

      <section className="mt-8" aria-labelledby="report-preview-title">
        <h2 id="report-preview-title" className="text-2xl font-semibold">
          Preview
        </h2>
        {preview.isPending && validDates && (
          <Skeleton label="Calculating report preview…" />
        )}
        {preview.isError && <ErrorMessage error={preview.error} />}
        {preview.data && (
          <>
            <p className="mt-2 text-sm text-secondary">
              {formatDate(preview.data.period_start_utc)} →{" "}
              {formatDate(preview.data.period_end_utc)} · UTC · Active Keywords
              and active Tracked Sites
            </p>
            <p className="mt-1 text-sm text-secondary">
              Data as of{" "}
              {formatDate(preview.data.metrics.latest_successful_check_at)} ·
              Effective checked depth: Top {depth} · Comparison basis:{" "}
              {preview.data.metrics.comparison_basis.replaceAll("_", " ")}
            </p>
            <div className="ui-stat-grid mt-5">
              <StatCard
                label="Distinct Keywords"
                value={preview.data.metrics.distinct_keywords}
              />
              <StatCard
                label="Keyword × Site pairs"
                value={preview.data.metrics.keyword_site_pairs}
              />
              <StatCard
                label="Observed pairs"
                value={preview.data.metrics.observed_pairs}
              />
              <StatCard label="Checked depth" value={`Top ${depth}`} />
            </div>
            {preview.data.no_matching_keywords ? (
              <Alert className="mt-5">No matching Keywords.</Alert>
            ) : preview.data.matching_keywords_without_observations ? (
              <Alert className="mt-5">
                Matching Keywords have no ranking observations for this period.
              </Alert>
            ) : (
              <div className="report-preview-grid mt-5">
                <Card>
                  <h3 className="font-semibold">Ranking distribution</h3>
                  <dl className="report-metric-list mt-3">
                    {Object.entries(preview.data.metrics.distribution).map(
                      ([key, value]) => (
                        <div key={key}>
                          <dt>{depthLabels[key] ?? key}</dt>
                          <dd>{value}</dd>
                        </div>
                      ),
                    )}
                  </dl>
                </Card>
                <Card>
                  <h3 className="font-semibold">Movements</h3>
                  <dl className="report-metric-list mt-3">
                    {Object.entries(preview.data.metrics.movements).map(
                      ([key, value]) => (
                        <div key={key}>
                          <dt>
                            {depthLabels[key] ?? key.replaceAll("_", " ")}
                          </dt>
                          <dd>{value}</dd>
                        </div>
                      ),
                    )}
                  </dl>
                </Card>
              </div>
            )}
            {!!preview.data.sample.length && (
              <Table className="mt-5">
                <thead>
                  <tr>
                    <th>Keyword</th>
                    <th>Tracked Site</th>
                    <th>Previous</th>
                    <th>Current</th>
                    <th>Movement</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.data.sample.map((row) => (
                    <tr key={`${row.keyword_id}-${row.tracked_site_id}`}>
                      <td>{row.keyword}</td>
                      <td>{row.tracked_site_name}</td>
                      <td>{row.comparison?.position ?? "—"}</td>
                      <td>{row.current?.position ?? "—"}</td>
                      <td>
                        {depthLabels[row.movement_type] ?? row.movement_type}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </>
        )}
      </section>

      <div className="report-actions mt-7" aria-live="polite">
        <Button
          disabled={!preview.data || generate.isPending}
          loading={generate.isPending && generate.variables === "project_pdf"}
          variant="primary"
          onClick={() => generate.mutate("project_pdf")}
        >
          Generate PDF
        </Button>
        <Button
          disabled={!preview.data || generate.isPending}
          loading={
            generate.isPending && generate.variables === "comparison_csv"
          }
          onClick={() => generate.mutate("comparison_csv")}
        >
          Export Comparison CSV
        </Button>
        <Button
          disabled={!preview.data || generate.isPending}
          loading={generate.isPending && generate.variables === "history_csv"}
          onClick={() => generate.mutate("history_csv")}
        >
          Export History CSV
        </Button>
      </div>
      {generate.isError && <ErrorMessage error={generate.error} />}
      {notice && (
        <p className="mt-3 text-sm" role="status">
          {notice}
        </p>
      )}

      <section className="mt-12" aria-labelledby="recent-reports-title">
        <h2 id="recent-reports-title" className="text-2xl font-semibold">
          Recent reports
        </h2>
        {recent.isPending ? (
          <Skeleton label="Loading recent reports…" />
        ) : recent.isError ? (
          <ErrorMessage error={recent.error} />
        ) : reportItems.length === 0 ? (
          <p className="mt-4 text-secondary">No reports generated yet.</p>
        ) : (
          <>
            <Table className="mt-5">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Period</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Expires</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {reportItems.map((report) => (
                  <tr key={report.id}>
                    <td>{reportTypeLabels[report.report_type]}</td>
                    <td>
                      {new Date(report.period_start_utc)
                        .toISOString()
                        .slice(0, 10)}{" "}
                      →{" "}
                      {new Date(report.period_end_utc)
                        .toISOString()
                        .slice(0, 10)}
                    </td>
                    <td>
                      <StatusBadge status={report.status} />
                      {report.error_code && (
                        <span className="ml-2 text-xs text-danger">
                          {report.error_code}
                        </span>
                      )}
                    </td>
                    <td>{formatDate(report.created_at)}</td>
                    <td>{formatDate(report.expires_at)}</td>
                    <td>
                      {report.status === "ready" ? (
                        <Button size="sm" onClick={() => void download(report)}>
                          Download
                        </Button>
                      ) : ["failed", "expired"].includes(report.status) ? (
                        <Button
                          size="sm"
                          loading={
                            retry.isPending && retry.variables === report.id
                          }
                          onClick={() => retry.mutate(report.id)}
                        >
                          Regenerate
                        </Button>
                      ) : (
                        <span className="text-sm text-secondary">
                          Processing…
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <CursorPagination
              hasMore={recent.hasNextPage}
              loading={recent.isFetchingNextPage}
              onNext={() => void recent.fetchNextPage()}
            />
          </>
        )}
      </section>

      <ScheduledReports
        projectId={projectId}
        filters={filters}
        schedules={schedules.data}
        loading={schedules.isPending}
        error={schedules.error}
      />
    </main>
  );
}

function ScheduledReports({
  projectId,
  filters,
  schedules,
  loading,
  error,
}: {
  projectId: string;
  filters: ReportFilters;
  schedules: Awaited<ReturnType<typeof listReportSchedules>> | undefined;
  loading: boolean;
  error: unknown;
}) {
  const auth = useProtectedAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState("Weekly ranking report");
  const [frequency, setFrequency] = useState<"weekly" | "monthly">("weekly");
  const [hour, setHour] = useState(9);
  const [weekday, setWeekday] = useState(1);
  const [monthDay, setMonthDay] = useState(1);
  const [draft, setDraft] = useState<{
    id: string;
    name: string;
    frequency: "weekly" | "monthly";
    scheduledHour: number;
    weekday: number;
    monthDay: number;
  } | null>(null);
  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: reportKeys.schedules(projectId),
    });
  const create = useMutation({
    mutationFn: (input: ReportScheduleInput) =>
      createReportSchedule(auth.request, projectId, input),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: ReportScheduleUpdateInput;
    }) => updateReportSchedule(auth.request, projectId, id, input),
    onSuccess: () => {
      setDraft(null);
      return invalidate();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) =>
      deleteReportSchedule(auth.request, projectId, id),
    onSuccess: invalidate,
  });
  return (
    <section className="mt-12" aria-labelledby="scheduled-reports-title">
      <h2 id="scheduled-reports-title" className="text-2xl font-semibold">
        Scheduled reports
      </h2>
      <p className="mt-2 text-sm text-secondary">
        Report schedules are independent of rank-check schedules and never
        collect new rankings. Delivery is limited to your verified account
        email.
      </p>
      {loading ? (
        <Skeleton label="Loading report schedules…" />
      ) : error ? (
        <ErrorMessage error={error} />
      ) : !schedules?.delivery_configured ? (
        <Alert className="mt-5">
          Email delivery is not configured. Manual CSV and PDF reports remain
          available.
        </Alert>
      ) : (
        <>
          <Card className="mt-5">
            <h3 className="font-semibold">Create schedule</h3>
            <div className="report-form-grid mt-4">
              <label>
                Schedule name
                <Input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
              <label>
                Frequency
                <Select
                  value={frequency}
                  onChange={(event) =>
                    setFrequency(event.target.value as "weekly" | "monthly")
                  }
                >
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </Select>
              </label>
              <label>
                Scheduled hour (UTC)
                <Input
                  type="number"
                  min={0}
                  max={23}
                  value={hour}
                  onChange={(event) => setHour(Number(event.target.value))}
                />
              </label>
              {frequency === "weekly" ? (
                <label>
                  Weekday
                  <Select
                    value={weekday}
                    onChange={(event) => setWeekday(Number(event.target.value))}
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
                      <option key={day} value={index}>
                        {day}
                      </option>
                    ))}
                  </Select>
                </label>
              ) : (
                <label>
                  Day of month
                  <Input
                    type="number"
                    min={1}
                    max={31}
                    value={monthDay}
                    onChange={(event) =>
                      setMonthDay(Number(event.target.value))
                    }
                  />
                </label>
              )}
            </div>
            <Button
              className="mt-4"
              loading={create.isPending}
              disabled={!name.trim()}
              onClick={() =>
                create.mutate({
                  ...filters,
                  period: "30d",
                  start_date: undefined,
                  end_date: undefined,
                  name: name.trim(),
                  frequency,
                  scheduled_hour: hour,
                  weekday: frequency === "weekly" ? weekday : undefined,
                  month_day: frequency === "monthly" ? monthDay : undefined,
                  active: true,
                })
              }
            >
              Create schedule
            </Button>
            {create.isError && <ErrorMessage error={create.error} />}
          </Card>
          <div className="mt-5 grid gap-4">
            {schedules.items.map((schedule) => (
              <Card key={schedule.id} className="report-schedule-card">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold">{schedule.name}</h3>
                    <Badge tone={schedule.active ? "success" : "warning"}>
                      {schedule.active ? "Active" : "Paused"}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm text-secondary">
                    {schedule.frequency} · Next run{" "}
                    {formatDate(schedule.next_run_at_utc)} · Last run{" "}
                    {formatDate(schedule.last_run_at_utc)}
                  </p>
                  <p className="mt-1 text-sm text-secondary">
                    Last delivery: {schedule.last_delivery_status ?? "Not run"}
                    {schedule.last_error_code
                      ? ` · ${schedule.last_error_code}`
                      : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    loading={
                      update.isPending && update.variables?.id === schedule.id
                    }
                    onClick={() =>
                      update.mutate({
                        id: schedule.id,
                        input: { active: !schedule.active },
                      })
                    }
                  >
                    {schedule.active ? "Pause" : "Resume"}
                  </Button>
                  <Button
                    size="sm"
                    onClick={() =>
                      setDraft({
                        id: schedule.id,
                        name: schedule.name,
                        frequency: schedule.frequency,
                        scheduledHour: schedule.scheduled_hour,
                        weekday: schedule.weekday ?? 0,
                        monthDay: schedule.month_day ?? 1,
                      })
                    }
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    confirmation={`Delete report schedule “${schedule.name}”?`}
                    loading={
                      remove.isPending && remove.variables === schedule.id
                    }
                    onClick={() => remove.mutate(schedule.id)}
                  >
                    Delete
                  </Button>
                </div>
                {draft?.id === schedule.id && (
                  <div className="report-schedule-editor">
                    <div className="report-form-grid">
                      <label>
                        Schedule name
                        <Input
                          value={draft.name}
                          onChange={(event) =>
                            setDraft({ ...draft, name: event.target.value })
                          }
                        />
                      </label>
                      <label>
                        Frequency
                        <Select
                          value={draft.frequency}
                          onChange={(event) =>
                            setDraft({
                              ...draft,
                              frequency: event.target.value as
                                | "weekly"
                                | "monthly",
                            })
                          }
                        >
                          <option value="weekly">Weekly</option>
                          <option value="monthly">Monthly</option>
                        </Select>
                      </label>
                      <label>
                        Scheduled hour (UTC)
                        <Input
                          type="number"
                          min={0}
                          max={23}
                          value={draft.scheduledHour}
                          onChange={(event) =>
                            setDraft({
                              ...draft,
                              scheduledHour: Number(event.target.value),
                            })
                          }
                        />
                      </label>
                      {draft.frequency === "weekly" ? (
                        <label>
                          Weekday
                          <Select
                            value={draft.weekday}
                            onChange={(event) =>
                              setDraft({
                                ...draft,
                                weekday: Number(event.target.value),
                              })
                            }
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
                              <option key={day} value={index}>
                                {day}
                              </option>
                            ))}
                          </Select>
                        </label>
                      ) : (
                        <label>
                          Day of month
                          <Input
                            type="number"
                            min={1}
                            max={31}
                            value={draft.monthDay}
                            onChange={(event) =>
                              setDraft({
                                ...draft,
                                monthDay: Number(event.target.value),
                              })
                            }
                          />
                        </label>
                      )}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={!draft.name.trim()}
                        loading={
                          update.isPending &&
                          update.variables?.id === schedule.id
                        }
                        onClick={() =>
                          update.mutate({
                            id: schedule.id,
                            input: {
                              name: draft.name.trim(),
                              frequency: draft.frequency,
                              scheduled_hour: draft.scheduledHour,
                              weekday:
                                draft.frequency === "weekly"
                                  ? draft.weekday
                                  : null,
                              month_day:
                                draft.frequency === "monthly"
                                  ? draft.monthDay
                                  : null,
                            },
                          })
                        }
                      >
                        Save changes
                      </Button>
                      <Button size="sm" onClick={() => setDraft(null)}>
                        Cancel
                      </Button>
                    </div>
                    {update.isError && <ErrorMessage error={update.error} />}
                  </div>
                )}
              </Card>
            ))}
            {schedules.items.length === 0 && (
              <p className="text-secondary">No scheduled reports yet.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}
