import csv
import io
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.keyword import Keyword
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_job import RankCheckJob
from app.models.ranking import Ranking
from app.models.report import GeneratedReport, ReportDeliveryAttempt, ReportSchedule
from app.models.tracked_site import TrackedSite
from app.models.user import User
from app.services.report_email import (
    FakeReportEmailSender,
    ReportEmail,
    ReportEmailError,
)
from app.services.report_renderers import render_csv
from app.services.report_worker import ReportWorker
from app.services.reports import ReportService, next_schedule_run
from app.services.task_queue.base import TaskEnqueueResult
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


class TransientOnceEmailSender(FakeReportEmailSender):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def send(self, message: ReportEmail) -> str:
        self.calls += 1
        if self.calls == 1:
            raise ReportEmailError("REPORT_DELIVERY_FAILED", transient=True)
        return await super().send(message)


class RecordingReportQueue:
    def __init__(self) -> None:
        self.report_attempts: list[int] = []

    async def enqueue_rank_check_job(self, job_id, *, schedule_time=None):
        return TaskEnqueueResult(f"unused/{job_id}")

    async def enqueue_report_job(
        self, report_id, *, schedule_time=None, attempt: int = 0
    ) -> TaskEnqueueResult:
        self.report_attempts.append(attempt)
        return TaskEnqueueResult(f"recording/{report_id}/{attempt}")


async def seed_reports(
    client: AsyncClient, app: FastAPI, label: str = "reports"
) -> tuple[dict[str, str], UUID, UUID, UUID]:
    account = await register(client, label)
    headers = authorization(account)
    site_response = await client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={"name": "Cửa hàng chính", "primary_domain": "reports.example"},
    )
    assert site_response.status_code == 201
    project = project_body(
        await create_project(
            client,
            headers,
            name="Báo cáo Việt Nam",
            keywords=["cà phê ngon", "=SUM(1,1)", "never checked"],
        )
    )
    project_id = UUID(str(project["id"]))
    user_id = UUID(account.json()["user"]["id"])
    site = site_response.json()
    site_id = UUID(site["id"])
    domain_id = UUID(site["domains"][0]["id"])
    now = datetime.now(UTC).replace(microsecond=0)
    previous = now - timedelta(days=31)
    current = now - timedelta(minutes=2)
    async with app.state.session_factory() as session, session.begin():
        stored_site = await session.get(TrackedSite, site_id)
        assert stored_site is not None
        stored_site.created_at = previous - timedelta(days=1)
        keywords = {
            row.keyword: row.id
            for row in await session.scalars(
                select(Keyword).where(Keyword.project_id == project_id)
            )
        }

        def add(name: str, when: datetime, position: int | None, *, failed=False):
            check_id = uuid4()
            session.add(
                RankCheck(
                    id=check_id,
                    user_id=user_id,
                    project_id=project_id,
                    keyword_id=keywords[name],
                    provider="fake",
                    status=(
                        RankCheckStatus.FAILED if failed else RankCheckStatus.SUCCEEDED
                    ),
                    query_snapshot=name,
                    search_engine_snapshot="google",
                    country_code_snapshot="VN",
                    language_code_snapshot="vi",
                    device_snapshot="desktop",
                    result_limit=10,
                    provider_request_count=0 if failed else 1,
                    requested_at=when,
                    completed_at=when,
                    created_at=when,
                )
            )
            if position is not None and not failed:
                session.add(
                    Ranking(
                        rank_check_id=check_id,
                        tracked_site_id=site_id,
                        tracked_domain_id=domain_id,
                        tracked_site_name_snapshot="Cửa hàng chính",
                        matched_domain_snapshot="reports.example",
                        position=position,
                        result_url="https://reports.example/page",
                        result_hostname="reports.example",
                        title=name,
                        created_at=when,
                    )
                )

        add("cà phê ngon", previous, 8)
        add("cà phê ngon", current, 2)
        add("=SUM(1,1)", previous, None)
        add("=SUM(1,1)", now - timedelta(days=10), None)
        add("=SUM(1,1)", current, 5)
        add("never checked", current, 1, failed=True)
    return headers, project_id, user_id, site_id


def report_worker(app: FastAPI) -> ReportWorker:
    return ReportWorker(
        ReportService(
            app.state.session_factory,
            app.state.settings,
            app.state.task_queue,
            app.state.report_storage,
            app.state.report_email_sender,
        )
    )


async def generate(
    client: AsyncClient,
    app: FastAPI,
    headers: dict[str, str],
    project_id: UUID,
    report_type: str,
    key: str,
) -> tuple[dict[str, object], bytes]:
    response = await client.post(
        f"/api/v1/projects/{project_id}/reports",
        headers=headers,
        json={
            "report_type": report_type,
            "period": "30d",
            "tag_match": "any",
            "include_keyword_details": True,
            "idempotency_key": key,
        },
    )
    assert response.status_code == 202, response.text
    report_id = UUID(response.json()["id"])
    assert await report_worker(app).execute(report_id)
    detail = await client.get(
        f"/api/v1/projects/{project_id}/reports/{report_id}", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"
    download = await client.get(
        f"/api/v1/projects/{project_id}/reports/{report_id}/download",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.headers["cache-control"] == "private, no-store"
    return detail.json(), download.content


async def test_preview_csv_pdf_and_no_rank_usage(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, _, site_id = await seed_reports(auth_client, auth_app)
    preview = await auth_client.get(
        f"/api/v1/projects/{project_id}/reports/preview?period=30d"
        f"&tracked_site_id={site_id}",
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    metrics = preview.json()["metrics"]
    assert metrics["distinct_keywords"] == 3
    assert metrics["keyword_site_pairs"] == 3
    assert metrics["observed_pairs"] == 2
    assert metrics["never_checked"] == 1
    assert metrics["effective_depth"] == 10
    assert metrics["movements"]["improved"] == 1
    assert metrics["movements"]["entered_checked_depth"] == 1
    assert metrics["comparison_basis"] == "range_boundary"

    async with auth_app.state.session_factory() as session:
        rank_jobs_before = int(
            await session.scalar(select(func.count(RankCheckJob.id))) or 0
        )

    comparison, comparison_bytes = await generate(
        auth_client,
        auth_app,
        headers,
        project_id,
        "comparison_csv",
        "comparison-1",
    )
    rows = list(csv.DictReader(io.StringIO(comparison_bytes.decode("utf-8"))))
    assert list(rows[0]) == [
        "project_name",
        "device",
        "keyword",
        "keyword_id",
        "tracked_site_name",
        "tracked_site_id",
        "report_start_utc",
        "report_end_utc",
        "comparison_checked_at_utc",
        "comparison_position",
        "comparison_depth",
        "current_checked_at_utc",
        "current_position",
        "current_depth",
        "current_status",
        "movement_type",
        "numeric_change",
        "comparison_basis",
        "keyword_group",
        "keyword_tags",
    ]
    assert len(rows) == 3
    by_keyword = {row["keyword"].lstrip("'"): row for row in rows}
    assert by_keyword["cà phê ngon"]["numeric_change"] == "6"
    assert by_keyword["=SUM(1,1)"]["keyword"].startswith("'=")
    assert by_keyword["never checked"]["current_status"] == "never_checked"
    assert comparison["byte_size"] == len(comparison_bytes)

    _, history_bytes = await generate(
        auth_client,
        auth_app,
        headers,
        project_id,
        "history_csv",
        "history-1",
    )
    history = list(csv.DictReader(io.StringIO(history_bytes.decode("utf-8"))))
    assert {row["status"] for row in history} == {"ranked", "not_found_in_depth"}
    assert all(row["rank_check_id"] for row in history)

    pdf, pdf_bytes = await generate(
        auth_client,
        auth_app,
        headers,
        project_id,
        "project_pdf",
        "pdf-1",
    )
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 4000
    assert pdf["mime_type"] == "application/pdf"

    async with auth_app.state.session_factory() as session:
        rank_jobs_after = int(
            await session.scalar(select(func.count(RankCheckJob.id))) or 0
        )
    assert rank_jobs_after == rank_jobs_before


async def test_idempotency_tenant_isolation_and_expired_download(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, _, _ = await seed_reports(auth_client, auth_app, "owner")
    payload = {
        "report_type": "comparison_csv",
        "period": "7d",
        "idempotency_key": "same-click",
    }
    first = await auth_client.post(
        f"/api/v1/projects/{project_id}/reports", headers=headers, json=payload
    )
    second = await auth_client.post(
        f"/api/v1/projects/{project_id}/reports", headers=headers, json=payload
    )
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]

    foreign_headers = authorization(await register(auth_client, "foreign"))
    hidden = await auth_client.get(
        f"/api/v1/projects/{project_id}/reports/{first.json()['id']}",
        headers=foreign_headers,
    )
    assert hidden.status_code == 404
    hidden_download = await auth_client.get(
        f"/api/v1/projects/{project_id}/reports/{first.json()['id']}/download",
        headers=foreign_headers,
    )
    assert hidden_download.status_code == 404

    report_id = UUID(first.json()["id"])
    assert await report_worker(auth_app).execute(report_id)
    async with auth_app.state.session_factory() as session, session.begin():
        report = await session.get(GeneratedReport, report_id)
        assert report is not None
        report.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    expired = await auth_client.get(
        f"/api/v1/projects/{project_id}/reports/{report_id}/download",
        headers=headers,
    )
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "REPORT_EXPIRED"


async def test_preview_distinguishes_unobserved_pairs_and_enforces_csv_limit(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    account = await register(auth_client, "unobserved")
    headers = authorization(account)
    site = await auth_client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={"name": "No observations", "primary_domain": "empty.example"},
    )
    assert site.status_code == 201
    project_id = UUID(
        str(
            project_body(
                await create_project(auth_client, headers, keywords=["no observation"])
            )["id"]
        )
    )
    preview = await auth_client.get(
        f"/api/v1/projects/{project_id}/reports/preview?period=30d",
        headers=headers,
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["no_matching_keywords"] is False
    assert body["matching_keywords_without_observations"] is True
    assert body["metrics"]["keyword_site_pairs"] == 1
    assert body["metrics"]["observed_pairs"] == 0
    assert body["metrics"]["comparison_basis"] == "none"

    original = auth_app.state.settings
    auth_app.state.settings = original.model_copy(update={"report_max_csv_rows": 1})
    try:
        legal = await auth_client.post(
            f"/api/v1/projects/{project_id}/reports",
            headers=headers,
            json={"report_type": "comparison_csv", "period": "30d"},
        )
        assert legal.status_code == 202
        # Exactly one row remains legal; adding a second active site exceeds the cap.
        second = await auth_client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={"name": "Second", "primary_domain": "second-empty.example"},
        )
        assert second.status_code == 201
        too_large = await auth_client.post(
            f"/api/v1/projects/{project_id}/reports",
            headers=headers,
            json={"report_type": "comparison_csv", "period": "30d"},
        )
        assert too_large.status_code == 413
        assert too_large.json()["error"]["code"] == "REPORT_TOO_LARGE"
    finally:
        auth_app.state.settings = original


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_neutralizes_every_spreadsheet_formula_prefix(prefix: str) -> None:
    rendered = render_csv(("value",), [{"value": prefix + "unsafe"}]).decode()
    assert "'" + prefix + "unsafe" in rendered


def test_report_filename_is_safe_predictable_and_transliterated() -> None:
    assert (
        ReportService.safe_filename(
            "Báo cáo Đẹp / 2026",
            datetime(2026, 9, 1, tzinfo=UTC),
            datetime(2026, 10, 1, tzinfo=UTC),
            "pdf",
        )
        == "bao-cao-dep-2026-ranking-report-2026-09-01_2026-09-30.pdf"
    )


async def test_schedule_dispatch_and_fake_verified_email(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, user_id, _ = await seed_reports(
        auth_client, auth_app, "schedule"
    )
    fake = TransientOnceEmailSender()
    auth_app.state.report_email_sender = fake
    async with auth_app.state.session_factory() as session, session.begin():
        user = await session.get(User, user_id)
        assert user is not None
        user.email_verified_at = datetime.now(UTC)
    created = await auth_client.post(
        f"/api/v1/projects/{project_id}/report-schedules",
        headers=headers,
        json={
            "name": "Thứ hai hàng tuần",
            "frequency": "weekly",
            "scheduled_hour": 9,
            "weekday": 0,
            "active": True,
            "period": "30d",
        },
    )
    assert created.status_code == 201, created.text
    schedule_id = UUID(created.json()["id"])
    async with auth_app.state.session_factory() as session, session.begin():
        schedule = await session.get(ReportSchedule, schedule_id)
        assert schedule is not None
        schedule.next_run_at_utc = datetime.now(UTC) - timedelta(seconds=1)
    worker = report_worker(auth_app)
    assert await worker.dispatch_schedules() == 1
    async with auth_app.state.session_factory() as session:
        report_id = await session.scalar(
            select(GeneratedReport.id).where(
                GeneratedReport.report_schedule_id == schedule_id
            )
        )
    assert report_id is not None
    assert await worker.execute(report_id)
    assert fake.calls == 1
    assert len(fake.messages) == 0
    # The first transient failure is not retried in a tight worker loop.
    assert not await worker.deliver(report_id)
    assert fake.calls == 1
    async with auth_app.state.session_factory() as session, session.begin():
        first_attempt = await session.scalar(
            select(ReportDeliveryAttempt).where(
                ReportDeliveryAttempt.generated_report_id == report_id
            )
        )
        assert first_attempt is not None
        first_attempt.completed_at = datetime.now(UTC) - timedelta(seconds=31)
    assert await worker.deliver(report_id)
    assert fake.calls == 2
    assert len(fake.messages) == 1
    assert fake.messages[0].recipient.endswith("@example.com")
    async with auth_app.state.session_factory() as session:
        attempts = list(
            await session.scalars(
                select(ReportDeliveryAttempt)
                .where(ReportDeliveryAttempt.generated_report_id == report_id)
                .order_by(ReportDeliveryAttempt.attempt_number)
            )
        )
        assert [attempt.status for attempt in attempts] == ["failed", "sent"]
        assert all("@" not in attempt.recipient_digest for attempt in attempts)
    paused = await auth_client.patch(
        f"/api/v1/projects/{project_id}/report-schedules/{schedule_id}",
        headers=headers,
        json={"active": False},
    )
    assert paused.status_code == 200
    assert paused.json()["active"] is False
    deleted = await auth_client.delete(
        f"/api/v1/projects/{project_id}/report-schedules/{schedule_id}",
        headers=headers,
    )
    assert deleted.status_code == 204


def test_schedule_boundaries_and_month_end() -> None:
    after = datetime(2026, 1, 31, 10, tzinfo=UTC)
    assert next_schedule_run("monthly", 9, None, 31, after=after) == datetime(
        2026, 2, 28, 9, tzinfo=UTC
    )
    assert next_schedule_run(
        "weekly", 9, 0, None, after=datetime(2026, 9, 21, 9, tzinfo=UTC)
    ) == datetime(2026, 9, 28, 9, tzinfo=UTC)


async def test_cloud_recovery_requeues_expired_report_lease_with_new_attempt(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, _, _ = await seed_reports(auth_client, auth_app, "recovery")
    created = await auth_client.post(
        f"/api/v1/projects/{project_id}/reports",
        headers=headers,
        json={"report_type": "comparison_csv", "period": "7d"},
    )
    assert created.status_code == 202
    report_id = UUID(created.json()["id"])
    async with auth_app.state.session_factory() as session, session.begin():
        report = await session.get(GeneratedReport, report_id)
        assert report is not None
        report.status = "running"
        report.attempt_count = 1
        report.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        report.worker_execution_id = uuid4()
    queue = RecordingReportQueue()
    service = ReportService(
        auth_app.state.session_factory,
        auth_app.state.settings,
        queue,
        auth_app.state.report_storage,
        auth_app.state.report_email_sender,
    )
    assert await ReportWorker(service).recover(local=False) == 1
    assert queue.report_attempts == [1]
    async with auth_app.state.session_factory() as session:
        report = await session.get(GeneratedReport, report_id)
        assert report is not None
        assert report.status == "queued"
        assert report.lease_expires_at is None
        assert report.task_name.endswith("/1")
