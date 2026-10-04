#!/usr/bin/env python3
"""Read API SMTP settings; optionally check TLS/login without sending mail."""

import argparse
import json
import os
import shutil
import smtplib
import ssl
import subprocess
import sys

PUBLIC_FIELDS = (
    "APP_ENV",
    "AUTH_EMAIL_PROVIDER",
    "AUTH_EMAIL_FROM",
    "AUTH_SMTP_HOST",
    "AUTH_SMTP_PORT",
    "AUTH_SMTP_USERNAME",
    "AUTH_SMTP_SSL",
    "AUTH_SMTP_STARTTLS",
    "AUTH_SITE_URL",
)


def read_json(arguments: list[str], label: str) -> dict:
    result = subprocess.run(
        ["gcloud", *arguments, "--format=json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        sys.exit(
            f"Could not read {label}. Check gcloud authentication and permissions."
        )
    try:
        return json.loads(result.stdout)
    except ValueError:
        sys.exit(f"Unexpected JSON response for {label}.")


def read_password(binding: dict, project: str, annotations: dict) -> str:
    name = binding.get("name", "")
    version = binding.get("key", "")
    if not name or not str(version).isdigit():
        sys.exit("SMTP login check requires a pinned numeric password secret version.")
    # Cloud Run may use an alias for a fully qualified Secret Manager resource.
    for entry in annotations.get("run.googleapis.com/secrets", "").split(","):
        alias, separator, resource = entry.partition(":")
        if separator and alias == name:
            name = resource
            break
    try:
        result = subprocess.run(
            [
                "gcloud",
                "secrets",
                "versions",
                "access",
                str(version),
                f"--secret={name}",
                f"--project={project}",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except UnicodeError:
        sys.exit("SMTP password secret must contain valid UTF-8 text.")
    if result.returncode or not result.stdout:
        sys.exit(
            "Could not read SMTP password. Check secret version and access permissions."
        )
    return result.stdout


def check_smtp(values: dict[str, str], password: str | None = None) -> bool:
    host = values.get("AUTH_SMTP_HOST", "")
    implicit_tls = values.get("AUTH_SMTP_SSL", "false").lower() == "true"
    starttls = values.get("AUTH_SMTP_STARTTLS", "true").lower() == "true"
    if not host or host.isdecimal() or host == "mailpit" or host.startswith("<"):
        print("SMTP check: provide the real outgoing server hostname.")
        return False
    try:
        port = int(values.get("AUTH_SMTP_PORT", "587"))
        if not 1 <= port <= 65535 or implicit_tls == starttls:
            raise ValueError
    except ValueError:
        print(
            "SMTP check: select one TLS mode and a valid port (465 SSL, 587 STARTTLS)."
        )
        return False
    username = values.get("AUTH_SMTP_USERNAME", "")
    if password is not None and (not username or username.startswith("<")):
        print(
            "SMTP login check: a plaintext mailbox username is required in the API settings."
        )
        return False
    try:
        context = ssl.create_default_context()
        client: smtplib.SMTP
        if implicit_tls:
            client = smtplib.SMTP_SSL(host, port, timeout=10, context=context)
        else:
            client = smtplib.SMTP(host, port, timeout=10)
        with client:
            code, _ = client.ehlo()
            if code != 250:
                raise smtplib.SMTPHeloError(code, b"EHLO failed")
            if starttls:
                client.starttls(context=context)
                code, _ = client.ehlo()
                if code != 250:
                    raise smtplib.SMTPHeloError(code, b"EHLO after TLS failed")
            if password is not None:
                client.login(username, password)
        print("SMTP check: connection, certificate verification and EHLO passed.")
        if password is None:
            print("Password/login and recipient delivery were not tested.")
        else:
            print("SMTP login passed using the configured API credential.")
            print("Recipient delivery was not tested; no email was sent.")
        return True
    except (OSError, smtplib.SMTPException, UnicodeError) as error:
        # SMTP response text/exception strings can contain private information.
        code = getattr(error, "smtp_code", None)
        suffix = f" (SMTP status {code})" if isinstance(code, int) else ""
        print(f"SMTP check failed: {type(error).__name__}{suffix}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", default=os.environ.get("GCP_PROJECT_ID", "serp-saas")
    )
    parser.add_argument(
        "--region", default=os.environ.get("GCP_LOCATION", "asia-southeast1")
    )
    parser.add_argument("--check-smtp", action="store_true")
    parser.add_argument(
        "--check-login",
        action="store_true",
        help="Read the pinned SMTP password and test login over TLS; never print it or send mail.",
    )
    args = parser.parse_args()
    if not shutil.which("gcloud"):
        sys.exit("Run in authenticated Cloud Shell with gcloud installed.")
    service = read_json(
        [
            "run",
            "services",
            "describe",
            "serp-api",
            f"--project={args.project}",
            f"--region={args.region}",
        ],
        "API service",
    )
    status = service.get("status", {})
    ready = status.get("latestReadyRevisionName", "")
    traffic = status.get("traffic", [])
    revisions = {
        entry.get("revisionName") or ready
        for entry in traffic
        if entry.get("percent", 0) > 0
    } or {ready}
    if "" in revisions:
        sys.exit(
            "No serving API revision was found. Check Cloud Run service readiness."
        )
    success = True
    for name in sorted(revisions):
        revision = read_json(
            [
                "run",
                "revisions",
                "describe",
                name,
                f"--project={args.project}",
                f"--region={args.region}",
            ],
            "serving API revision",
        )
        containers = revision.get("spec", {}).get("containers", [])
        if not containers:
            sys.exit("No API container was found in the serving revision.")
        environment = {
            entry["name"]: entry
            for entry in containers[0].get("env", [])
            if "name" in entry
        }
        values = {
            field: environment[field].get("value", "<secret reference>")
            for field in PUBLIC_FIELDS
            if field in environment
        }
        password = environment.get("AUTH_SMTP_PASSWORD", {})
        binding = password.get("valueFrom", {}).get("secretKeyRef", {})
        annotations = revision.get("metadata", {}).get("annotations", {})
        cpu = annotations.get("run.googleapis.com/cpu-throttling", "true (default)")
        print(f"Serving API revision: {name}")
        print(f"CPU throttling: {cpu}; background email expects false.")
        for field in PUBLIC_FIELDS:
            print(f"{field}: {values.get(field, '<setting absent>')}")
        if binding:
            print(
                "AUTH_SMTP_PASSWORD binding: "
                f"{binding.get('name', '<unknown>')}:{binding.get('key', '<unknown>')}"
            )
        else:
            configured = bool(password.get("value"))
            print(
                f"AUTH_SMTP_PASSWORD inline value present: {configured} (value hidden)"
            )
        if args.check_smtp or args.check_login:
            credential = None
            if args.check_login:
                credential = (
                    read_password(binding, args.project, annotations)
                    if binding
                    else password.get("value")
                )
                if not credential:
                    sys.exit("SMTP login check requires a configured password.")
            success = check_smtp(values, credential) and success
    if args.check_smtp or args.check_login:
        print("This connection test runs from Cloud Shell, not from Cloud Run.")
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
