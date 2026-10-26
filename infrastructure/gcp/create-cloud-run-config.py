#!/usr/bin/env python3
"""Create the nonsecret Cloud Run environment file after SMTP is available."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit


def main() -> None:
    project = os.environ.get("GCP_PROJECT_ID") or "serp-saas"
    region = os.environ.get("GCP_LOCATION") or "asia-southeast1"
    number = os.environ.get("PROJECT_NUMBER", "")
    if not number.isdigit():
        sys.exit("Set PROJECT_NUMBER from gcloud projects describe before this step.")
    if not sys.stdin.isatty():
        sys.exit("Run interactively to configure the actual SMTP relay.")
    host = input("SMTP host (from your provider): ").strip()
    port = input("SMTP port [587; use 465 for implicit TLS]: ").strip() or "587"
    sender = input("Authorized sender email (or Name <email>): ").strip()
    username = input("SMTP username: ").strip()
    if not host or not sender or not username or port not in {"587", "465"}:
        sys.exit("Provide real SMTP host, sender, username, and TLS port 587 or 465.")
    if any("\n" in item or "\r" in item for item in (host, sender, username)):
        sys.exit("SMTP fields must not contain newlines.")
    site_origin = (
        os.environ.get("FRONTEND_ORIGIN")
        or f"https://serp-web-{number}.{region}.run.app"
    )
    origin = os.environ.get("FRONTEND_APP_ORIGIN") or site_origin
    origins = list(dict.fromkeys([site_origin, origin]))
    for item in origins:
        url = urlsplit(item)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.path
            or url.query
            or url.fragment
            or url.username
            or url.password
            or any(char in item for char in ",|\r\n")
        ):
            sys.exit(
                "FRONTEND_ORIGIN and FRONTEND_APP_ORIGIN must be HTTPS origins without a trailing slash."
            )
    config = {
        "APP_ENV": "production",
        "APP_NAME": "serp-saas",
        "APP_VERSION": "0.1.0",
        "DEBUG": "false",
        "BACKEND_HOST": "0.0.0.0",
        "BACKEND_PORT": "8080",
        # Redis is currently used only by /health/redis, not business workflows.
        "REDIS_URL": os.environ.get("REDIS_URL") or "redis://127.0.0.1:6379/0",
        "CORS_ORIGINS": json.dumps(origins),
        "AUTH_COOKIE_SECURE": "true",
        "AUTH_COOKIE_SAMESITE": "none",
        "AUTH_REQUIRE_VERIFIED_EMAIL": "true",
        "AUTH_SITE_URL": origin,
        "AUTH_EMAIL_PROVIDER": "smtp",
        "AUTH_EMAIL_FROM": sender,
        "AUTH_SMTP_HOST": host,
        "AUTH_SMTP_LOCAL_HOSTNAME": (
            os.environ.get("AUTH_SMTP_LOCAL_HOSTNAME") or "app.serpsaas.com"
        ),
        "AUTH_SMTP_PORT": port,
        "AUTH_SMTP_USERNAME": username,
        "AUTH_SMTP_STARTTLS": "true" if port == "587" else "false",
        "AUTH_SMTP_SSL": "true" if port == "465" else "false",
        "SERP_ENABLED_PROVIDERS": "serper",
        "SERP_PROVIDER_STRATEGY": "fixed",
        "SERP_FIXED_PROVIDER": "serper",
        "SERP_PROVIDER_PRIORITY": "serper",
        "TASK_QUEUE_PROVIDER": "cloud_tasks",
        "GCP_PROJECT_ID": project,
        "GCP_LOCATION": region,
        "CLOUD_TASKS_QUEUE": "rank-checks",
        "CLOUD_TASKS_WORKER_URL": f"https://serp-worker-{number}.{region}.run.app",
        "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL": f"serp-task-invoker@{project}.iam.gserviceaccount.com",
        "SCHEDULER_SERVICE_ACCOUNT_EMAIL": f"serp-scheduler-invoker@{project}.iam.gserviceaccount.com",
        "WORKER_DB_POOL_SIZE": "2",
        "WORKER_DB_MAX_OVERFLOW": "0",
        "REPORT_STORAGE_PROVIDER": "gcs",
        "REPORT_STORAGE_BUCKET": f"{project}-reports-{number}",
        "REPORT_STORAGE_PREFIX": "reports",
        "REPORT_EMAIL_PROVIDER": "disabled",
        "RANKING_ALERTS_ENABLED": "true",
        "RANKING_ALERT_EMAIL_ENABLED": "false",
        "RANKING_ALERT_EMAIL_HOURLY_CAP": "20",
    }
    output = Path(__file__).resolve().parents[2] / ".env.cloud-run.yaml"
    # JSON is valid YAML. All values are strings as required by Cloud Run env vars.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(json.dumps(config, indent=2) + "\n")
    print(f"Created {output} (passwords/API keys are injected from Secret Manager).")


if __name__ == "__main__":
    main()
