import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.models.project import Project
from app.models.report import GeneratedReport, ReportSchedule
from app.models.tracked_site import TrackedSiteStatus
from app.models.user import User
from app.repositories.analytics import AnalyticsRepository, ExplorerQuery, ExplorerRow
from app.repositories.keyword_organization import KeywordOrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.report import ReportAggregate, ReportRepository
from app.repositories.tracked_site import TrackedSiteRepository
from app.schemas.report import (
    DeliveryAttemptResponse,
    GeneratedReportList,
    GeneratedReportResponse,
    ReportCreateRequest,
    ReportDefinition,
    ReportMetrics,
    ReportObservation,
    ReportPreviewResponse,
    ReportPreviewRow,
    ReportScheduleList,
    ReportScheduleRequest,
    ReportScheduleResponse,
    ReportScheduleUpdate,
)
from app.services.normalization import decode_cursor, encode_cursor
from app.services.report_email import ReportEmailSender
from app.services.report_storage import ReportArtifactStorage
from app.services.task_queue import RankCheckTaskQueue, TaskQueueError

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90}
_SAFE_FILENAME = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ResolvedReport:
    project: Project
    definition: ReportDefinition
    period_start: datetime
    period_end: datetime
    comparison_before: datetime | None
    query: ExplorerQuery
    filters_snapshot: dict[str, object]


class ReportService:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        queue: RankCheckTaskQueue,
        storage: ReportArtifactStorage,
        email_sender: ReportEmailSender,
    ) -> None:
        self.factory = factory
        self.settings = settings
        self.queue = queue
        self.storage = storage
        self.email_sender = email_sender

    @staticmethod
    def _date_bounds(
        definition: ReportDefinition, now: datetime
    ) -> tuple[datetime, datetime, datetime | None]:
        if definition.period == "custom":
            assert definition.start_date is not None
            assert definition.end_date is not None
            start = datetime.combine(definition.start_date, time.min, UTC)
            end = datetime.combine(
                definition.end_date + timedelta(days=1), time.min, UTC
            )
            # Ranking Explorer treats the selected start date as an inclusive
            # comparison date and therefore uses the following midnight.
            return start, end, start + timedelta(days=1)
        days = _PERIOD_DAYS[definition.period]
        return now - timedelta(days=days), now, None

    async def _resolve(
        self,
        session: AsyncSession,
        project_id: UUID,
        user_id: UUID,
        definition: ReportDefinition,
        *,
        now: datetime,
    ) -> ResolvedReport:
        project = await ProjectRepository(session).get_for_user(project_id, user_id)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        start, end, comparison_before = self._date_bounds(definition, now)
        if end > now + timedelta(days=1):
            raise AppError(
                422, "INVALID_REPORT_RANGE", "Reports cannot include future dates."
            )
        if (end - start).days > self.settings.report_max_range_days:
            raise AppError(
                422,
                "INVALID_REPORT_RANGE",
                "Report range cannot exceed "
                f"{self.settings.report_max_range_days} days.",
            )
        site_snapshot: dict[str, str] | None = None
        if definition.tracked_site_id:
            site = await TrackedSiteRepository(session).get_for_user(
                definition.tracked_site_id, user_id
            )
            if site is None or site.status != TrackedSiteStatus.ACTIVE:
                raise AppError(404, "TRACKED_SITE_NOT_FOUND", "Tracked Site not found.")
            site_snapshot = {"id": str(site.id), "name": site.name}
        organizations = KeywordOrganizationRepository(session)
        group_snapshot: dict[str, str] | None = None
        if definition.keyword_group_id:
            group = await organizations.get_group(
                project_id, user_id, definition.keyword_group_id
            )
            if group is None:
                raise AppError(
                    422,
                    "INVALID_GROUP_ASSIGNMENT",
                    "Group filter is invalid.",
                )
            group_snapshot = {"id": str(group.id), "name": group.name}
        tag_ids = set(definition.keyword_tag_ids)
        tags = await organizations.tags_for_project(project_id, tag_ids)
        if len(tags) != len(tag_ids):
            raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
        tags.sort(key=lambda item: (item.normalized_name, str(item.id)))
        snapshot: dict[str, object] = {
            "period": definition.period,
            "resolved_start_utc": start.isoformat(),
            "resolved_end_utc": end.isoformat(),
            "tracked_site": site_snapshot,
            "keyword_group": group_snapshot,
            "keyword_tags": [{"id": str(tag.id), "name": tag.name} for tag in tags],
            "tag_match": definition.tag_match,
            "include_keyword_details": definition.include_keyword_details,
            "timezone": "UTC",
            "scope": "active_keywords_and_tracked_sites",
            "project_name": project.name,
            "device": project.device,
        }
        query = ExplorerQuery(
            project_id=project_id,
            user_id=user_id,
            device=project.device,
            boundary=start,
            current_before=end,
            comparison_before=comparison_before,
            custom_dates=definition.period == "custom",
            search=None,
            movement=None,
            position_bucket=None,
            status=None,
            tracked_site_id=definition.tracked_site_id,
            group_filter=definition.keyword_group_id,
            tag_ids=frozenset(tag_ids),
            tag_match=definition.tag_match,
            sort="keyword",
            order="asc",
            limit=10,
            offset=0,
        )
        return ResolvedReport(
            project, definition, start, end, comparison_before, query, snapshot
        )

    @staticmethod
    def _observation(row: ExplorerRow, *, current: bool) -> ReportObservation | None:
        check_id = row.current_check_id if current else row.comparison_check_id
        checked_at = row.current_checked_at if current else row.comparison_checked_at
        position = row.current_position if current else row.comparison_position
        depth = row.current_depth if current else row.comparison_depth
        if check_id is None or checked_at is None or depth is None:
            return None
        return ReportObservation(
            checked_at_utc=checked_at,
            position=position,
            depth=depth,
            status="ranked" if position is not None else "not_found_in_depth",
        )

    @classmethod
    def _preview_row(cls, row: ExplorerRow) -> ReportPreviewRow:
        return ReportPreviewRow(
            keyword_id=row.keyword_id,
            keyword=row.keyword,
            tracked_site_id=row.tracked_site_id,
            tracked_site_name=row.tracked_site_name,
            comparison=cls._observation(row, current=False),
            current=cls._observation(row, current=True),
            movement_type=row.movement,
            numeric_change=row.change,
        )

    @staticmethod
    def _basis(
        resolved: ResolvedReport,
        earliest_in_range: int,
        total: int,
        never_checked: int,
    ) -> str:
        if total == 0 or total == never_checked:
            return "none"
        if resolved.definition.period == "custom":
            return "custom_dates"
        return "earliest_in_range" if earliest_in_range else "range_boundary"

    async def _metrics(
        self, session: AsyncSession, resolved: ResolvedReport
    ) -> tuple[ReportMetrics, list[ReportPreviewRow]]:
        analytics = AnalyticsRepository(session)
        reports = ReportRepository(session)
        counts = await analytics.explorer_counts(resolved.query)
        aggregate = await reports.aggregate(resolved.query)
        depth = await analytics.explorer_depth(resolved.query)
        sample_rows = await analytics.explorer_page(resolved.query)
        winner_query = ResolvedReportQuery.with_sort(
            resolved.query, "change", "desc", 10
        )
        loser_query = ResolvedReportQuery.with_sort(resolved.query, "change", "asc", 10)
        winner_rows = [
            row
            for row in await analytics.explorer_page(winner_query)
            if row.movement == "improved" and row.change is not None
        ]
        loser_rows = [
            row
            for row in await analytics.explorer_page(loser_query)
            if row.movement == "declined" and row.change is not None
        ]
        distribution = self._distribution(aggregate, depth)
        movement = {
            "improved": counts.improved,
            "declined": counts.declined,
            "unchanged": counts.unchanged,
            "entered_checked_depth": counts.entered_checked_depth,
            "left_checked_depth": counts.left_checked_depth,
            "no_previous_data": counts.no_previous_data,
            "never_checked": counts.never_checked,
        }
        assert sum(movement.values()) == counts.total
        metrics = ReportMetrics(
            distinct_keywords=aggregate.distinct_keywords,
            keyword_site_pairs=aggregate.keyword_site_pairs,
            distinct_tracked_sites=aggregate.distinct_tracked_sites,
            observed_pairs=aggregate.observed_pairs,
            never_checked=counts.never_checked,
            effective_depth=depth,
            latest_successful_check_at=aggregate.latest_successful_check_at,
            comparison_basis=self._basis(
                resolved,
                counts.earliest_in_range,
                counts.total,
                counts.never_checked,
            ),
            distribution=distribution,
            movements=movement,
            biggest_winners=[self._preview_row(row) for row in winner_rows[:10]],
            biggest_losers=[self._preview_row(row) for row in loser_rows[:10]],
        )
        return metrics, [self._preview_row(row) for row in sample_rows]

    @staticmethod
    def _distribution(aggregate: ReportAggregate, depth: int) -> dict[str, int]:
        result = {"top_3": aggregate.top_3}
        if depth >= 4:
            result["positions_4_10"] = aggregate.positions_4_10
        if depth >= 11:
            result["positions_11_20"] = aggregate.positions_11_20
        if depth >= 21:
            result["positions_21_50"] = aggregate.positions_21_50
        if depth >= 51:
            result["positions_51_100"] = aggregate.positions_51_100
        result["not_found_in_depth"] = aggregate.not_found_in_depth
        return result

    async def preview(
        self,
        project_id: UUID,
        user_id: UUID,
        definition: ReportDefinition,
    ) -> ReportPreviewResponse:
        now = datetime.now(UTC)
        async with self.factory() as session:
            resolved = await self._resolve(
                session, project_id, user_id, definition, now=now
            )
            metrics, sample = await self._metrics(session, resolved)
        return ReportPreviewResponse(
            project_id=project_id,
            project_name=resolved.project.name,
            device=resolved.project.device,
            period_start_utc=resolved.period_start,
            period_end_utc=resolved.period_end,
            no_matching_keywords=metrics.keyword_site_pairs == 0,
            matching_keywords_without_observations=(
                metrics.keyword_site_pairs > 0 and metrics.observed_pairs == 0
            ),
            filters=resolved.filters_snapshot,
            metrics=metrics,
            sample=sample,
        )

    @staticmethod
    def _fingerprint(report_type: str, definition: dict[str, object]) -> str:
        payload = json.dumps(
            {"report_type": report_type, "definition": definition},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    async def create(
        self, project_id: UUID, user_id: UUID, request: ReportCreateRequest
    ) -> GeneratedReportResponse:
        now = datetime.now(UTC)
        idempotency_key = (
            request.idempotency_key.strip() if request.idempotency_key else None
        )
        async with self.factory() as session, session.begin():
            repo = ReportRepository(session)
            fingerprint = self._fingerprint(
                request.report_type,
                request.model_dump(
                    mode="json", exclude={"idempotency_key", "report_type"}
                ),
            )
            if idempotency_key:
                existing = await repo.by_idempotency(
                    project_id, user_id, idempotency_key
                )
                if existing:
                    if (
                        existing.filters_snapshot.get("request_fingerprint")
                        != fingerprint
                    ):
                        raise AppError(
                            409,
                            "IDEMPOTENCY_CONFLICT",
                            "Idempotency key was already used for another report.",
                        )
                    return GeneratedReportResponse.model_validate(existing)
            resolved = await self._resolve(
                session, project_id, user_id, request, now=now
            )
            if (
                await repo.active_count(user_id)
                >= self.settings.report_max_concurrent_per_user
            ):
                raise AppError(
                    429,
                    "REPORT_CONCURRENCY_LIMIT",
                    "Too many reports are currently being generated.",
                )
            metrics, _ = await self._metrics(session, resolved)
            if (
                request.report_type != "project_pdf"
                and metrics.keyword_site_pairs > self.settings.report_max_csv_rows
            ):
                raise AppError(
                    413,
                    "REPORT_TOO_LARGE",
                    "Narrow the report filters or reporting period.",
                )
            snapshot = dict(resolved.filters_snapshot)
            snapshot["request_fingerprint"] = fingerprint
            report = GeneratedReport(
                user_id=user_id,
                project_id=project_id,
                report_type=request.report_type,
                status="pending",
                period_start_utc=resolved.period_start,
                period_end_utc=resolved.period_end,
                filters_snapshot=snapshot,
                metrics_snapshot=metrics.model_dump(mode="json"),
                expires_at=now
                + timedelta(days=self.settings.report_artifact_retention_days),
                max_attempts=self.settings.report_job_max_attempts,
                idempotency_key=idempotency_key,
            )
            session.add(report)
            try:
                await session.flush()
            except IntegrityError:
                raise AppError(
                    409,
                    "IDEMPOTENCY_CONFLICT",
                    "Idempotency key was already used.",
                ) from None
            report_id = report.id
        await self.enqueue(report_id)
        return await self.detail(project_id, user_id, report_id)

    async def enqueue(self, report_id: UUID, *, recovery: bool = False) -> bool:
        now = datetime.now(UTC)
        async with self.factory() as session:
            report = await session.get(GeneratedReport, report_id)
            allowed = {"pending"} if not recovery else {"queued", "running"}
            if report is None or report.status not in allowed:
                return False
            if (
                recovery
                and report.status == "running"
                and (report.lease_expires_at is None or report.lease_expires_at > now)
            ):
                return False
            if report.next_retry_at and report.next_retry_at > now:
                return False
            schedule_time = report.next_retry_at
            attempt = report.attempt_count
        try:
            result = await self.queue.enqueue_report_job(
                report_id, schedule_time=schedule_time, attempt=attempt
            )
        except TaskQueueError as error:
            if error.permanent:
                async with self.factory() as session, session.begin():
                    report = await ReportRepository(session).locked(report_id)
                    if report and report.status in allowed:
                        report.status = "failed"
                        report.error_code = "REPORT_TASK_ENQUEUE_FAILED"
                        report.completed_at = datetime.now(UTC)
            return False
        async with self.factory() as session, session.begin():
            report = await ReportRepository(session).locked(report_id)
            if report and report.status in allowed:
                report.status = "queued"
                report.task_name = result.task_name
                report.queued_at = datetime.now(UTC)
                report.worker_execution_id = None
                report.lease_expires_at = None
        return True

    async def recent(
        self,
        project_id: UUID,
        user_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> GeneratedReportList:
        async with self.factory() as session:
            if (
                await ProjectRepository(session).get_for_user(project_id, user_id)
                is None
            ):
                raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
            rows, has_more = await ReportRepository(session).recent(
                project_id, user_id, limit, decode_cursor(cursor)
            )
        return GeneratedReportList(
            items=[GeneratedReportResponse.model_validate(row) for row in rows],
            has_more=has_more,
            next_cursor=(
                encode_cursor(rows[-1].created_at, rows[-1].id)
                if rows and has_more
                else None
            ),
        )

    async def detail(
        self, project_id: UUID, user_id: UUID, report_id: UUID
    ) -> GeneratedReportResponse:
        async with self.factory() as session, session.begin():
            report = await ReportRepository(session).get(
                report_id, project_id, user_id, lock=True
            )
            if report is None:
                raise AppError(404, "REPORT_NOT_FOUND", "Report not found.")
            if report.status == "ready" and report.expires_at <= datetime.now(UTC):
                report.status = "expired"
                report.error_code = "REPORT_EXPIRED"
            return GeneratedReportResponse.model_validate(report)

    async def download(
        self, project_id: UUID, user_id: UUID, report_id: UUID
    ) -> tuple[bytes, str, str]:
        detail = await self.detail(project_id, user_id, report_id)
        if detail.status == "expired":
            raise AppError(410, "REPORT_EXPIRED", "Report artifact has expired.")
        if detail.status != "ready":
            raise AppError(409, "REPORT_NOT_READY", "Report is not ready.")
        async with self.factory() as session:
            report = await ReportRepository(session).get(report_id, project_id, user_id)
            assert report is not None
            if not report.storage_key or not report.mime_type or not report.filename:
                raise AppError(
                    500,
                    "REPORT_GENERATION_FAILED",
                    "Report artifact is unavailable.",
                )
            data = await self.storage.read(report.storage_key)
            if data is None:
                raise AppError(
                    404, "REPORT_ARTIFACT_MISSING", "Report artifact is missing."
                )
            return data, report.mime_type, report.filename

    async def retry(
        self, project_id: UUID, user_id: UUID, report_id: UUID
    ) -> GeneratedReportResponse:
        async with self.factory() as session, session.begin():
            report = await ReportRepository(session).get(
                report_id, project_id, user_id, lock=True
            )
            if report is None:
                raise AppError(404, "REPORT_NOT_FOUND", "Report not found.")
            if report.status not in {"failed", "expired"}:
                raise AppError(
                    409, "REPORT_RETRY_NOT_ALLOWED", "This report cannot be retried."
                )
            if report.attempt_count >= report.max_attempts:
                raise AppError(
                    409,
                    "REPORT_RETRY_EXHAUSTED",
                    "Report retry limit has been reached.",
                )
            report.status = "pending"
            report.error_code = None
            report.completed_at = None
            report.storage_key = None
            report.expires_at = datetime.now(UTC) + timedelta(
                days=self.settings.report_artifact_retention_days
            )
        await self.enqueue(report_id)
        return await self.detail(project_id, user_id, report_id)

    async def delivery_attempts(
        self, project_id: UUID, user_id: UUID, report_id: UUID
    ) -> list[DeliveryAttemptResponse]:
        async with self.factory() as session:
            report = await ReportRepository(session).get(report_id, project_id, user_id)
            if report is None:
                raise AppError(404, "REPORT_NOT_FOUND", "Report not found.")
            rows = await ReportRepository(session).attempts(report_id)
        return [DeliveryAttemptResponse.model_validate(row) for row in rows]

    @staticmethod
    def safe_filename(
        project_name: str, start: datetime, end: datetime, extension: str
    ) -> str:
        ascii_name = (
            unicodedata.normalize("NFKD", project_name.casefold().replace("đ", "d"))
            .encode("ascii", "ignore")
            .decode()
        )
        slug = _SAFE_FILENAME.sub("-", ascii_name).strip("-")[:80]
        if not slug:
            slug = "project"
        end_date = (end - timedelta(microseconds=1)).date().isoformat()
        return (
            f"{slug}-ranking-report-{start.date().isoformat()}_{end_date}.{extension}"
        )


class ResolvedReportQuery:
    @staticmethod
    def with_sort(
        query: ExplorerQuery, sort: str, order: str, limit: int
    ) -> ExplorerQuery:
        return ExplorerQuery(
            **{
                **query.__dict__,
                "sort": sort,
                "order": order,
                "limit": limit,
                "offset": 0,
            }
        )


def next_schedule_run(
    frequency: str,
    scheduled_hour: int,
    weekday: int | None,
    month_day: int | None,
    *,
    after: datetime,
) -> datetime:
    after = after.astimezone(UTC)
    if frequency == "weekly":
        assert weekday is not None
        days = (weekday - after.weekday()) % 7
        candidate = datetime.combine(
            after.date() + timedelta(days=days), time(scheduled_hour), UTC
        )
        if candidate <= after:
            candidate += timedelta(days=7)
        return candidate
    assert month_day is not None
    year, month = after.year, after.month
    while True:
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        candidate = datetime(
            year, month, min(month_day, last_day), scheduled_hour, tzinfo=UTC
        )
        if candidate > after:
            return candidate
        year, month = next_month.year, next_month.month


class ReportScheduleService:
    def __init__(self, reports: ReportService) -> None:
        self.reports = reports

    def _response(self, schedule: ReportSchedule) -> ReportScheduleResponse:
        return ReportScheduleResponse(
            **{
                key: getattr(schedule, key)
                for key in (
                    "id",
                    "project_id",
                    "name",
                    "report_type",
                    "frequency",
                    "report_timezone",
                    "scheduled_hour",
                    "weekday",
                    "month_day",
                    "filters",
                    "active",
                    "next_run_at_utc",
                    "last_run_at_utc",
                    "last_delivery_status",
                    "last_error_code",
                    "created_at",
                    "updated_at",
                )
            },
            delivery_configured=self.reports.email_sender.configured,
        )

    async def list(self, project_id: UUID, user_id: UUID) -> ReportScheduleList:
        async with self.reports.factory() as session:
            if (
                await ProjectRepository(session).get_for_user(project_id, user_id)
                is None
            ):
                raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
            rows = await ReportRepository(session).schedules(project_id, user_id)
        return ReportScheduleList(
            items=[self._response(row) for row in rows],
            delivery_configured=self.reports.email_sender.configured,
        )

    async def create(
        self, project_id: UUID, user_id: UUID, request: ReportScheduleRequest
    ) -> ReportScheduleResponse:
        if not self.reports.email_sender.configured:
            raise AppError(
                503,
                "REPORT_DELIVERY_UNAVAILABLE",
                "Email report delivery is not configured.",
            )
        now = datetime.now(UTC)
        async with self.reports.factory() as session, session.begin():
            user = await session.get(User, user_id)
            if user is None or user.email_verified_at is None:
                raise AppError(
                    422,
                    "REPORT_EMAIL_NOT_VERIFIED",
                    "Verify the account email before scheduling reports.",
                )
            await self.reports._resolve(session, project_id, user_id, request, now=now)
            repo = ReportRepository(session)
            if (
                await repo.active_schedule_count(project_id)
                >= self.reports.settings.report_max_active_schedules_per_project
            ):
                raise AppError(
                    429,
                    "REPORT_SCHEDULE_LIMIT",
                    "Active report schedule limit reached.",
                )
            filters = request.model_dump(
                mode="json",
                exclude={
                    "name",
                    "frequency",
                    "scheduled_hour",
                    "weekday",
                    "month_day",
                    "active",
                    "period",
                    "start_date",
                    "end_date",
                },
            )
            schedule = ReportSchedule(
                user_id=user_id,
                project_id=project_id,
                name=request.name.strip(),
                report_type="project_pdf",
                frequency=request.frequency,
                report_timezone="UTC",
                scheduled_hour=request.scheduled_hour,
                weekday=request.weekday,
                month_day=request.month_day,
                filters=filters,
                active=request.active,
                next_run_at_utc=next_schedule_run(
                    request.frequency,
                    request.scheduled_hour,
                    request.weekday,
                    request.month_day,
                    after=now,
                ),
            )
            session.add(schedule)
            await session.flush()
            await session.refresh(schedule)
            return self._response(schedule)

    async def update(
        self,
        project_id: UUID,
        user_id: UUID,
        schedule_id: UUID,
        request: ReportScheduleUpdate,
    ) -> ReportScheduleResponse:
        if not self.reports.email_sender.configured:
            raise AppError(
                503,
                "REPORT_DELIVERY_UNAVAILABLE",
                "Email report delivery is not configured.",
            )
        now = datetime.now(UTC)
        async with self.reports.factory() as session, session.begin():
            schedule = await ReportRepository(session).schedule(
                schedule_id, project_id, user_id, lock=True
            )
            if schedule is None:
                raise AppError(404, "REPORT_SCHEDULE_NOT_FOUND", "Schedule not found.")
            values = request.model_dump(exclude_unset=True, mode="json")
            filters = dict(schedule.filters)
            for key in (
                "tracked_site_id",
                "keyword_group_id",
                "keyword_tag_ids",
                "tag_match",
                "include_keyword_details",
            ):
                if key in values:
                    filters[key] = values.pop(key)
            frequency = str(values.get("frequency", schedule.frequency))
            weekday = values.get("weekday", schedule.weekday)
            month_day = values.get("month_day", schedule.month_day)
            if frequency == "weekly":
                if weekday is None:
                    raise AppError(
                        422, "INVALID_REPORT_SCHEDULE", "Weekday is required."
                    )
                month_day = None
            else:
                if month_day is None:
                    raise AppError(
                        422, "INVALID_REPORT_SCHEDULE", "Month day is required."
                    )
                weekday = None
            definition = ReportDefinition.model_validate({"period": "30d", **filters})
            await self.reports._resolve(
                session, project_id, user_id, definition, now=now
            )
            schedule.filters = filters
            schedule.frequency = frequency
            schedule.weekday = cast(int | None, weekday)
            schedule.month_day = cast(int | None, month_day)
            if "name" in values:
                schedule.name = str(values["name"]).strip()
            if "scheduled_hour" in values:
                schedule.scheduled_hour = int(values["scheduled_hour"])
            if "active" in values:
                schedule.active = bool(values["active"])
            schedule.next_run_at_utc = next_schedule_run(
                schedule.frequency,
                schedule.scheduled_hour,
                schedule.weekday,
                schedule.month_day,
                after=now,
            )
            await session.flush()
            await session.refresh(schedule)
            return self._response(schedule)

    async def delete(self, project_id: UUID, user_id: UUID, schedule_id: UUID) -> None:
        async with self.reports.factory() as session, session.begin():
            schedule = await ReportRepository(session).schedule(
                schedule_id, project_id, user_id, lock=True
            )
            if schedule is None:
                raise AppError(404, "REPORT_SCHEDULE_NOT_FOUND", "Schedule not found.")
            await session.delete(schedule)
