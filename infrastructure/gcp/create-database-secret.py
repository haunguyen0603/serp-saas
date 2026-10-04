#!/usr/bin/env python3
"""Prompt for the existing DB password and add an encoded URL to Secret Manager."""

import getpass
import os
import shutil
import subprocess
import sys
from urllib.parse import quote


def main() -> None:
    if not shutil.which("gcloud"):
        sys.exit(
            "gcloud is required. Use an authenticated Google Cloud Shell checkout."
        )
    if not sys.stdin.isatty():
        sys.exit(
            "Run interactively so the database password can be entered without echo."
        )
    project = os.environ.get("GCP_PROJECT_ID") or "serp-saas"
    region = os.environ.get("GCP_LOCATION") or "asia-southeast1"
    instance = os.environ.get("CLOUD_SQL_INSTANCE") or "serp-saas"
    secret = os.environ.get("DATABASE_SECRET_NAME") or "serp-database-url"
    user = os.environ.get("DATABASE_USER") or "serp_app"
    database = os.environ.get("DATABASE_NAME") or "serp_saas"
    password = getpass.getpass(f"Existing PostgreSQL password for {user}: ")
    if not password:
        sys.exit("A nonempty database password is required.")
    socket = quote(f"/cloudsql/{project}:{region}:{instance}", safe="/:")
    url = (
        f"postgresql+asyncpg://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@/{quote(database, safe='')}?host={socket}&ssl=disable"
    )
    # The password/URL never enter command arguments, stdout, or a disk file.
    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "add",
            secret,
            f"--project={project}",
            "--data-file=-",
            "--format=value(name)",
        ],
        input=url,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        sys.exit(
            "Could not create the secret version. "
            "Check gcloud authentication and Secret Manager permissions."
        )
    print(f"Created secret version: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
