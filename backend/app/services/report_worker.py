import hashlib
import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.errors import AppError
from app.models.report import GeneratedReport, ReportDeliveryAttempt, ReportSchedule
from app.models.user import User
from app.repositories.analytics import AnalyticsRepository, ExplorerRow
from app.repositories.report import ReportRepository
from app.schemas.report import ReportDefinition
from app.services.report_email import ReportEmail, ReportEmailError
from app.services.report_renderers import (
    COMPARISON_CSV_COLUMNS,
    HISTORY_CSV_COLUMNS,
    iso_utc,
    render_csv,
    render_project_pdf,
)
from app.services.reports import (
    ReportService,
    ResolvedReport,
    next_schedule_run,
)

_RETRYABLE = {
    "REPORT_STORAGE_FAILED",
    "REPORT_GENERATION_FAILED",
    "REPORT_DELIVERY_FAILED",
}
_RETRYABLE_DELIVERY = {"REPORT_DELIVERY_FAILED", "REPORT_DELIVERY_INTERRUPTED"}
logger = logging.getLogger(__name__)


class ReportWorker:
    def __init__(self, reports: ReportService) -> None:
        self.reports = reports

    @staticmethod
    def _definition(report: GeneratedReport) -> ReportDefinition:
        snapshot = report.filters_snapshot
        period = str(snapshot.get("period", "30d"))
        if period.startswith("scheduled_"):
            period = "30d"
        site = snapshot.get("tracked_site")
        group = snapshot.get("keyword_group")
        raw_tags = snapshot.get("keyword_tags")
        tags = raw_tags if isinstance(raw_tags, list) else []
        values: dict[str, Any] = {
            "tracked_site_id": (site.get("id") if isinstance(site, dict) else None),
            "keyword_group_id": (group.get("id") if isinstance(group, dict) else None),
            "keyword_tag_ids": [
                tag.get("id") for tag in tags if isinstance(tag, dict) and tag.get("id")
            ],
            "tag_match": snapshot.get("tag_match", "any"),
            "include_keyword_details": snapshot.get("include_keyword_details", True),
        }
        if period == "custom":
            values.update(
                {
                    "period": "custom",
                    "start_date": report.period_start_utc.date(),
                    "end_date": (
                        report.period_end_utc - timedelta(microseconds=1)
                    ).date(),
                }
            )
        else:
            values["period"] = period
        return ReportDefinition.model_validate(values)

    async def _resolved(self, session: Any, report: GeneratedReport) -> ResolvedReport:
        definition = self._definition(report)
        resolved = await self.reports._resolve(
            session,
            report.project_id,
            report.user_id,
            definition,
            now=report.period_end_utc,
        )
        if str(report.filters_snapshot.get("period", "")).startswith("scheduled_"):
            resolved = replace(
                resolved,
                period_start=report.period_start_utc,
                period_end=report.period_end_utc,
                query=replace(
                    resolved.query,
                    boundary=report.period_start_utc,
                    current_before=report.period_end_utc,
                    comparison_before=None,
                    custom_dates=False,
                ),
            )
        if (
            resolved.period_start != report.period_start_utc
            or resolved.period_end != report.period_end_utc
        ):
            raise AppError(
                500,
                "REPORT_DEFINITION_INVALID",
                "Persisted report boundaries are invalid.",
            )
        return resolved

    @staticmethod
    def _row_basis(resolved: ResolvedReport, row: ExplorerRow) -> str:
        if row.comparison_check_id is None:
            return "none"
        if resolved.definition.period == "custom":
            return "custom_dates"
        return (
            "range_boundary" if row.comparison_before_boundary else "earliest_in_range"
        )

    @staticmethod
    def _tag_string(names: list[str]) -> str:
        return ";".join(sorted(names, key=str.casefold))

    async def _comparison_rows(
        self, session: Any, resolved: ResolvedReport
    ) -> tuple[list[ExplorerRow], dict[UUID, tuple[str | None, list[str]]]]:
        query = replace(
            resolved.query,
            limit=self.reports.settings.report_max_csv_rows + 1,
            offset=0,
            sort="keyword",
            order="asc",
        )
        rows = await AnalyticsRepository(session).explorer_page(query)
        if len(rows) > self.reports.settings.report_max_csv_rows:
            raise AppError(
                413,
                "REPORT_TOO_LARGE",
                "Narrow the report filters or reporting period.",
            )
        metadata = await ReportRepository(session).keyword_metadata(
            resolved.project.id, {row.keyword_id for row in rows}
        )
        return rows, metadata

    def _comparison_csv(
        self,
        report: GeneratedReport,
        resolved: ResolvedReport,
        rows: list[ExplorerRow],
        metadata: dict[UUID, tuple[str | None, list[str]]],
    ) -> bytes:
        snapshot = report.filters_snapshot
        project_name = str(snapshot.get("project_name", resolved.project.name))
        values = []
        for row in rows:
            group, tags = metadata.get(row.keyword_id, (None, []))
            values.append(
                {
                    "project_name": project_name,
                    "device": resolved.project.device,
                    "keyword": row.keyword,
                    "keyword_id": str(row.keyword_id),
                    "tracked_site_name": row.tracked_site_name,
                    "tracked_site_id": str(row.tracked_site_id),
                    "report_start_utc": iso_utc(report.period_start_utc),
                    "report_end_utc": iso_utc(report.period_end_utc),
                    "comparison_checked_at_utc": iso_utc(row.comparison_checked_at),
                    "comparison_position": row.comparison_position or "",
                    "comparison_depth": row.comparison_depth or "",
                    "current_checked_at_utc": iso_utc(row.current_checked_at),
                    "current_position": row.current_position or "",
                    "current_depth": row.current_depth or "",
                    "current_status": (
                        "never_checked"
                        if row.current_check_id is None
                        else "ranked"
                        if row.current_position is not None
                        else "not_found_in_depth"
                    ),
                    "movement_type": row.movement,
                    "numeric_change": (row.change if row.change is not None else ""),
                    "comparison_basis": self._row_basis(resolved, row),
                    "keyword_group": group or "",
                    "keyword_tags": self._tag_string(tags),
                }
            )
        return render_csv(COMPARISON_CSV_COLUMNS, values)

    async def _history_csv(
        self, session: Any, report: GeneratedReport, resolved: ResolvedReport
    ) -> bytes:
        repository = ReportRepository(session)
        rows = await repository.history_rows(
            resolved.query,
            report.period_start_utc,
            report.period_end_utc,
            self.reports.settings.report_max_csv_rows + 1,
        )
        if len(rows) > self.reports.settings.report_max_csv_rows:
            raise AppError(
                413,
                "REPORT_TOO_LARGE",
                "Narrow the report filters or reporting period.",
            )
        metadata = await repository.keyword_metadata(
            report.project_id, {row.keyword_id for row in rows}
        )
        project_name = str(
            report.filters_snapshot.get("project_name", resolved.project.name)
        )
        values = []
        for row in rows:
            group, tags = metadata.get(row.keyword_id, (None, []))
            values.append(
                {
                    "project_name": project_name,
                    "device": resolved.project.device,
                    "keyword": row.keyword,
                    "keyword_id": str(row.keyword_id),
                    "tracked_site_name": row.tracked_site_name,
                    "tracked_site_id": str(row.tracked_site_id),
                    "checked_at_utc": iso_utc(row.checked_at),
                    "position": row.position or "",
                    "checked_depth": row.checked_depth,
                    "status": (
                        "ranked" if row.position is not None else "not_found_in_depth"
                    ),
                    "rank_check_id": str(row.rank_check_id),
                    "keyword_group": group or "",
                    "keyword_tags": self._tag_string(tags),
                }
            )
        return render_csv(HISTORY_CSV_COLUMNS, values)

    @staticmethod
    def _labels(depth: int) -> tuple[dict[str, str], dict[str, str]]:
        distribution = {
            "top_3": "Top 3",
            "positions_4_10": "Positions 4–10",
            "positions_11_20": "Positions 11–20",
            "positions_21_50": "Positions 21–50",
            "positions_51_100": "Positions 51–100",
            "not_found_in_depth": f"Not found in Top {depth}",
        }
        movements = {
            "improved": "Improved",
            "declined": "Declined",
            "unchanged": "Unchanged",
            "entered_checked_depth": f"Entered Top {depth}",
            "left_checked_depth": f"Left Top {depth}",
            "no_previous_data": "No previous data",
            "never_checked": "Never checked",
        }
        return distribution, movements

    @staticmethod
    def _filter_label(snapshot: dict[str, object]) -> str:
        parts = ["Active Keywords and active Tracked Sites"]
        for key, label in (
            ("tracked_site", "Tracked Site"),
            ("keyword_group", "Group"),
        ):
            value = snapshot.get(key)
            if isinstance(value, dict):
                parts.append(f"{label}: {value.get('name', '')}")
        tags = snapshot.get("keyword_tags")
        if isinstance(tags, list) and tags:
            parts.append(
                "Tags "
                + str(snapshot.get("tag_match", "any")).upper()
                + ": "
                + ", ".join(
                    str(tag.get("name", "")) for tag in tags if isinstance(tag, dict)
                )
            )
        return " · ".join(parts)

    async def _pdf(
        self,
        session: Any,
        report: GeneratedReport,
        resolved: ResolvedReport,
        rows: list[ExplorerRow],
    ) -> bytes:
        metrics, _ = await self.reports._metrics(session, resolved)
        cap = self.reports.settings.report_max_pdf_detail_rows
        details = [
            {
                "keyword": row.keyword,
                "tracked_site_name": row.tracked_site_name,
                "comparison_position": row.comparison_position,
                "current_position": row.current_position,
                "movement_type": row.movement,
            }
            for row in rows[:cap]
        ]
        winners = [
            {
                "keyword": item.keyword,
                "tracked_site_name": item.tracked_site_name,
                "comparison_position": item.comparison.position
                if item.comparison
                else None,
                "current_position": item.current.position if item.current else None,
                "numeric_change": item.numeric_change,
            }
            for item in metrics.biggest_winners
        ]
        losers = [
            {
                "keyword": item.keyword,
                "tracked_site_name": item.tracked_site_name,
                "comparison_position": item.comparison.position
                if item.comparison
                else None,
                "current_position": item.current.position if item.current else None,
                "numeric_change": item.numeric_change,
            }
            for item in metrics.biggest_losers
        ]
        distribution_labels, movement_labels = self._labels(metrics.effective_depth)
        basis_note = {
            "earliest_in_range": (
                "Some baselines use the earliest successful observation in the range "
                "because no observation existed at the range boundary."
            ),
            "custom_dates": (
                "Custom date comparison uses the latest successful observation on or "
                "before the selected start date and the latest before the end boundary."
            ),
            "range_boundary": (
                "Baseline is the latest successful comparable observation at or before "
                "the range boundary."
            ),
            "none": "No comparable baseline is available.",
        }[metrics.comparison_basis]
        methodology = (
            "Row grain is one active Keyword × selected active Tracked Site. Only "
            "successful persisted RankChecks are used; failed checks are excluded. "
            f"Positions are depth-aware at Top {metrics.effective_depth}; an observed "
            f"absence means Not found in Top {metrics.effective_depth}, not a global "
            f"lost ranking. Timezone is UTC. {basis_note} No rank check was run for "
            "this report."
        )
        context = {
            "project_name": report.filters_snapshot.get(
                "project_name", resolved.project.name
            ),
            "device": resolved.project.device,
            "period_start": iso_utc(report.period_start_utc),
            "period_end": iso_utc(report.period_end_utc),
            "generated_at": iso_utc(datetime.now(UTC)),
            "data_as_of": iso_utc(metrics.latest_successful_check_at),
            "filter_label": self._filter_label(report.filters_snapshot),
            "metrics": metrics.model_dump(mode="json"),
            "distribution_rows": [
                (distribution_labels[key], value)
                for key, value in metrics.distribution.items()
            ],
            "movement_rows": [
                (movement_labels[key], value)
                for key, value in metrics.movements.items()
            ],
            "winners": winners,
            "losers": losers,
            "include_details": resolved.definition.include_keyword_details,
            "details": details,
            "details_truncated": len(rows) > cap,
            "methodology": methodology,
        }
        return render_project_pdf(context)

    async def _generate(
        self, report_id: UUID
    ) -> tuple[bytes, str, str, dict[str, object]]:
        async with self.reports.factory() as session:
            report = await session.get(GeneratedReport, report_id)
            if report is None:
                raise AppError(404, "REPORT_NOT_FOUND", "Report not found.")
            resolved = await self._resolved(session, report)
            metrics, _ = await self.reports._metrics(session, resolved)
            if report.report_type == "history_csv":
                data = await self._history_csv(session, report, resolved)
                mime, extension = "text/csv; charset=utf-8", "csv"
            else:
                rows, metadata = await self._comparison_rows(session, resolved)
                if report.report_type == "comparison_csv":
                    data = self._comparison_csv(report, resolved, rows, metadata)
                    mime, extension = "text/csv; charset=utf-8", "csv"
                else:
                    data = await self._pdf(session, report, resolved, rows)
                    mime, extension = "application/pdf", "pdf"
            filename = self.reports.safe_filename(
                str(report.filters_snapshot.get("project_name", resolved.project.name)),
                report.period_start_utc,
                report.period_end_utc,
                extension,
            )
            return data, mime, filename, metrics.model_dump(mode="json")

    async def execute(self, report_id: UUID) -> bool:
        now = datetime.now(UTC)
        execution_id = uuid4()
        async with self.reports.factory() as session, session.begin():
            report = await ReportRepository(session).locked(report_id)
            if report is None or report.status in {"ready", "expired"}:
                return True
            if (
                report.status == "running"
                and report.lease_expires_at
                and report.lease_expires_at > now
            ):
                return True
            if report.status not in {"queued", "running"}:
                return False
            if report.next_retry_at and report.next_retry_at > now:
                return False
            if report.attempt_count >= report.max_attempts:
                report.status = "failed"
                report.error_code = "REPORT_RETRY_EXHAUSTED"
                report.completed_at = now
                return True
            report.status = "running"
            report.attempt_count += 1
            report.started_at = report.started_at or now
            report.worker_execution_id = execution_id
            report.lease_expires_at = now + timedelta(
                seconds=self.reports.settings.report_job_lease_seconds
            )
            report.next_retry_at = None
            user_id = report.user_id
        error: str | None = None
        try:
            data, mime, filename, metrics = await self._generate(report_id)
            extension = "pdf" if mime == "application/pdf" else "csv"
            storage_key = f"{user_id.hex}/{report_id.hex}.{extension}"
            await self.reports.storage.write(storage_key, data)
        except AppError as exc:
            error = exc.code
        except Exception:
            logger.exception(
                "report_generation_failed",
                extra={
                    "report_id": str(report_id),
                    "safe_error_code": "REPORT_GENERATION_FAILED",
                },
            )
            error = "REPORT_GENERATION_FAILED"
        retry = False
        async with self.reports.factory() as session, session.begin():
            report = await ReportRepository(session).locked(report_id)
            if (
                report is None
                or report.status != "running"
                or report.worker_execution_id != execution_id
            ):
                return False
            report.lease_expires_at = None
            report.worker_execution_id = None
            if error:
                retry = (
                    error in _RETRYABLE and report.attempt_count < report.max_attempts
                )
                if retry:
                    report.status = "queued"
                    report.next_retry_at = datetime.now(UTC) + timedelta(
                        seconds=min(300, 30 * 2 ** (report.attempt_count - 1))
                    )
                else:
                    report.status = "failed"
                    report.error_code = error
                    report.completed_at = datetime.now(UTC)
            else:
                report.status = "ready"
                report.storage_key = storage_key
                report.mime_type = mime
                report.byte_size = len(data)
                report.filename = filename
                report.metrics_snapshot = metrics
                report.error_code = None
                report.completed_at = datetime.now(UTC)
                schedule_id = report.report_schedule_id
        if not error and schedule_id:
            await self.deliver(report_id)
        return not retry

    async def deliver(self, report_id: UUID) -> bool:
        async with self.reports.factory() as session, session.begin():
            report = await ReportRepository(session).locked(report_id)
            if (
                report is None
                or report.status != "ready"
                or not report.report_schedule_id
            ):
                return False
            schedule = await session.get(ReportSchedule, report.report_schedule_id)
            user = await session.get(User, report.user_id)
            if schedule is None or user is None or user.email_verified_at is None:
                return False
            digest = hashlib.sha256(user.email.encode()).hexdigest()
            attempts = await ReportRepository(session).attempts(report.id)
            if any(
                item.status == "sent" and item.recipient_digest == digest
                for item in attempts
            ):
                return True
            if attempts:
                previous = attempts[-1]
                if (
                    previous.status == "failed"
                    and previous.error_code in _RETRYABLE_DELIVERY
                    and previous.completed_at is not None
                ):
                    delay = min(300, 30 * 2 ** (len(attempts) - 1))
                    if previous.completed_at + timedelta(seconds=delay) > datetime.now(
                        UTC
                    ):
                        return False
            pending = [item for item in attempts if item.status == "pending"]
            cutoff = datetime.now(UTC) - timedelta(
                seconds=self.reports.settings.report_job_lease_seconds
            )
            if any(item.created_at > cutoff for item in pending):
                return False
            for item in pending:
                item.status = "failed"
                item.error_code = "REPORT_DELIVERY_INTERRUPTED"
                item.completed_at = datetime.now(UTC)
            if len(attempts) >= report.max_attempts:
                schedule.last_delivery_status = "failed"
                schedule.last_error_code = "REPORT_DELIVERY_RETRY_EXHAUSTED"
                return False
            attempt = ReportDeliveryAttempt(
                generated_report_id=report.id,
                report_schedule_id=schedule.id,
                recipient_digest=digest,
                status="pending",
                attempt_number=len(attempts) + 1,
            )
            session.add(attempt)
            await session.flush()
            attempt_id = attempt.id
            storage_key = report.storage_key
            filename = report.filename
            mime_type = report.mime_type
            recipient = user.email
            project_name = str(report.filters_snapshot.get("project_name", "Project"))
        assert storage_key and filename and mime_type
        attachment = await self.reports.storage.read(storage_key)
        error: ReportEmailError | None = None
        provider_id: str | None = None
        if attachment is None:
            error = ReportEmailError("REPORT_ARTIFACT_MISSING", transient=False)
        elif len(attachment) > self.reports.settings.report_email_attachment_max_bytes:
            error = ReportEmailError("REPORT_ATTACHMENT_TOO_LARGE", transient=False)
        else:
            try:
                provider_id = await self.reports.email_sender.send(
                    ReportEmail(
                        recipient=recipient,
                        subject=f"{project_name} ranking report",
                        body=(
                            "Your scheduled ranking report is attached. It uses "
                            "existing ranking data and did not run a new rank check."
                        ),
                        filename=filename,
                        mime_type=mime_type,
                        attachment=attachment,
                    )
                )
            except ReportEmailError as exc:
                error = exc
        async with self.reports.factory() as session, session.begin():
            stored_attempt = await session.get(ReportDeliveryAttempt, attempt_id)
            report = await session.get(GeneratedReport, report_id)
            schedule = (
                await session.get(ReportSchedule, report.report_schedule_id)
                if report and report.report_schedule_id
                else None
            )
            if stored_attempt is None:
                return False
            stored_attempt.completed_at = datetime.now(UTC)
            stored_attempt.provider_delivery_id = provider_id
            stored_attempt.status = "failed" if error else "sent"
            stored_attempt.error_code = error.code if error else None
            if schedule:
                schedule.last_delivery_status = stored_attempt.status
                schedule.last_error_code = stored_attempt.error_code
        return error is None

    async def recover(self, *, local: bool, limit: int = 20) -> int:
        now = datetime.now(UTC)
        async with self.reports.factory() as session:
            ids = list(
                await session.scalars(
                    select(GeneratedReport.id)
                    .where(
                        (
                            (GeneratedReport.status == "queued")
                            & (
                                GeneratedReport.next_retry_at.is_(None)
                                | (GeneratedReport.next_retry_at <= now)
                            )
                        )
                        | (
                            (GeneratedReport.status == "running")
                            & (GeneratedReport.lease_expires_at <= now)
                        )
                    )
                    .order_by(GeneratedReport.created_at)
                    .limit(limit)
                )
            )
        if local:
            for report_id in ids:
                await self.execute(report_id)
        else:
            for report_id in ids:
                await self.reports.enqueue(report_id, recovery=True)
        async with self.reports.factory() as session:
            delivery_ids = list(
                await session.scalars(
                    select(GeneratedReport.id)
                    .join(
                        ReportSchedule,
                        ReportSchedule.id == GeneratedReport.report_schedule_id,
                    )
                    .where(
                        GeneratedReport.status == "ready",
                        ReportSchedule.last_delivery_status == "failed",
                        ReportSchedule.last_error_code.in_(list(_RETRYABLE_DELIVERY)),
                    )
                    .order_by(GeneratedReport.completed_at)
                    .limit(limit)
                )
            )
        for report_id in delivery_ids:
            await self.deliver(report_id)
        await self.expire()
        return len(ids) + len(delivery_ids)

    async def expire(self, limit: int = 100) -> int:
        now = datetime.now(UTC)
        async with self.reports.factory() as session:
            rows = list(
                await session.scalars(
                    select(GeneratedReport)
                    .where(
                        GeneratedReport.status == "ready",
                        GeneratedReport.expires_at <= now,
                    )
                    .limit(limit)
                )
            )
        for report in rows:
            if report.storage_key:
                await self.reports.storage.delete(report.storage_key)
            async with self.reports.factory() as session, session.begin():
                current = await ReportRepository(session).locked(report.id)
                if current and current.status == "ready" and current.expires_at <= now:
                    current.status = "expired"
                    current.error_code = "REPORT_EXPIRED"
                    current.storage_key = None
        return len(rows)

    @staticmethod
    def _scheduled_window(schedule: ReportSchedule) -> tuple[datetime, datetime]:
        end = schedule.next_run_at_utc.astimezone(UTC)
        if schedule.frequency == "weekly":
            return end - timedelta(days=7), end
        month_start = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_end = month_start
        previous_start = (month_start - timedelta(days=1)).replace(day=1)
        return previous_start, previous_end

    async def dispatch_schedules(self, limit: int = 20) -> int:
        now = datetime.now(UTC)
        created: list[UUID] = []
        async with self.reports.factory() as session, session.begin():
            repo = ReportRepository(session)
            schedules = await repo.due_schedules(now, limit)
            for schedule in schedules:
                start, end = self._scheduled_window(schedule)
                key = f"schedule:{schedule.id}:{start.isoformat()}:{end.isoformat()}"
                existing = await repo.by_idempotency(
                    schedule.project_id, schedule.user_id, key
                )
                if existing is None:
                    definition = ReportDefinition.model_validate(
                        {"period": "30d", **schedule.filters}
                    )
                    resolved = await self.reports._resolve(
                        session,
                        schedule.project_id,
                        schedule.user_id,
                        definition,
                        now=end,
                    )
                    resolved = replace(
                        resolved,
                        period_start=start,
                        period_end=end,
                        comparison_before=None,
                        query=replace(
                            resolved.query,
                            boundary=start,
                            current_before=end,
                            comparison_before=None,
                            custom_dates=False,
                        ),
                        filters_snapshot={
                            **resolved.filters_snapshot,
                            "period": f"scheduled_{schedule.frequency}",
                            "resolved_start_utc": start.isoformat(),
                            "resolved_end_utc": end.isoformat(),
                        },
                    )
                    metrics, _ = await self.reports._metrics(session, resolved)
                    report = GeneratedReport(
                        user_id=schedule.user_id,
                        project_id=schedule.project_id,
                        report_schedule_id=schedule.id,
                        report_type="project_pdf",
                        status="pending",
                        period_start_utc=start,
                        period_end_utc=end,
                        filters_snapshot=resolved.filters_snapshot,
                        metrics_snapshot=metrics.model_dump(mode="json"),
                        expires_at=now
                        + timedelta(
                            days=self.reports.settings.report_artifact_retention_days
                        ),
                        max_attempts=self.reports.settings.report_job_max_attempts,
                        idempotency_key=key,
                    )
                    session.add(report)
                    await session.flush()
                    created.append(report.id)
                schedule.last_run_at_utc = schedule.next_run_at_utc
                schedule.next_run_at_utc = next_schedule_run(
                    schedule.frequency,
                    schedule.scheduled_hour,
                    schedule.weekday,
                    schedule.month_day,
                    after=schedule.next_run_at_utc,
                )
        for report_id in created:
            await self.reports.enqueue(report_id)
        return len(created)
