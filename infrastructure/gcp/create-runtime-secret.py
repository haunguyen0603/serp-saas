#!/usr/bin/env python3
"""Add one runtime secret version without putting its value in shell history."""

import argparse
import getpass
import os
import secrets
import shutil
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "name",
        choices=(
            "serp-jwt-key",
            "serp-serper-key",
            "serp-serpapi-key",
            "serp-auth-smtp-password",
        ),
    )
    parser.add_argument("--generate-jwt", action="store_true")
    args = parser.parse_args()
    if not shutil.which("gcloud"):
        sys.exit("Use an authenticated Cloud Shell checkout with gcloud installed.")
    if args.generate_jwt and args.name != "serp-jwt-key":
        parser.error("--generate-jwt is only valid for serp-jwt-key")
    if args.generate_jwt:
        value = secrets.token_urlsafe(48)
    else:
        if not sys.stdin.isatty():
            sys.exit("Run interactively to enter the secret without echo.")
        value = getpass.getpass(f"Value for {args.name}: ")
    if not value:
        sys.exit("A nonempty secret value is required.")
    project = os.environ.get("GCP_PROJECT_ID") or "serp-saas"
    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "add",
            args.name,
            f"--project={project}",
            "--data-file=-",
            "--format=value(name)",
        ],
        input=value,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        sys.exit(
            "Secret version creation failed. Check authentication and permissions."
        )
    print(f"Created secret version: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
