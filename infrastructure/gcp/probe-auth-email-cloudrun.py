#!/usr/bin/env python3
"""Run a one-off SMTP probe on Cloud Run using the serving API configuration."""

import argparse
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SMTP_FIELDS = (
    "AUTH_EMAIL_FROM",
    "AUTH_SMTP_HOST",
    "AUTH_SMTP_LOCAL_HOSTNAME",
    "AUTH_SMTP_PORT",
    "AUTH_SMTP_USERNAME",
    "AUTH_SMTP_PASSWORD",
    "AUTH_SMTP_SSL",
    "AUTH_SMTP_STARTTLS",
)
NETWORK_FIELDS = (
    "run.googleapis.com/vpc-access-connector",
    "run.googleapis.com/vpc-access-egress",
    "run.googleapis.com/network-interfaces",
)

# Executed inside the existing backend image, without importing/starting the app.
PROBE = r"""
import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

def report(stage, outcome, error=None):
    event = {"probe": "auth-email", "stage": stage, "outcome": outcome}
    if error is not None:
        event["error_class"] = type(error).__name__
        code = getattr(error, "smtp_code", None)
        if isinstance(code, int):
            event["smtp_status"] = code
        if isinstance(error, smtplib.SMTPRecipientsRefused):
            event["smtp_statuses"] = sorted({
                value[0] for value in error.recipients.values()
                if isinstance(value[0], int)
            })
    print(json.dumps(event), flush=True)

stage = "configuration"
try:
    env = os.environ
    host = env["AUTH_SMTP_HOST"]
    local_hostname = env.get("AUTH_SMTP_LOCAL_HOSTNAME", "app.serpsaas.com")
    port = int(env.get("AUTH_SMTP_PORT", "587"))
    implicit_tls = env.get("AUTH_SMTP_SSL", "false").lower() == "true"
    starttls = env.get("AUTH_SMTP_STARTTLS", "true").lower() == "true"
    if not host or not 1 <= port <= 65535 or implicit_tls == starttls:
        raise ValueError("Invalid SMTP TLS settings")
    recipient = env.get("PROBE_RECIPIENT", "")
    message = EmailMessage()
    if recipient:
        message["From"] = env["AUTH_EMAIL_FROM"]
        message["To"] = recipient
        message["Subject"] = "SMTP delivery test | SERP SaaS"
        message.set_content(
            "This is a requested SMTP delivery test from SERP SaaS on Cloud Run.\n"
            "This message does not verify your account.\n"
            "Return to the website and use Resend verification email after the issue is fixed.\n"
        )
    stage = "connect"
    if implicit_tls:
        client = smtplib.SMTP_SSL(
            host, port, local_hostname=local_hostname,
            timeout=10, context=ssl.create_default_context()
        )
    else:
        client = smtplib.SMTP(host, port, local_hostname=local_hostname, timeout=10)
    with client:
        report(stage, "passed")
        if starttls:
            stage = "starttls"
            client.starttls(context=ssl.create_default_context())
            report(stage, "passed")
        stage = "login"
        client.login(env["AUTH_SMTP_USERNAME"], env["AUTH_SMTP_PASSWORD"])
        report(stage, "passed")
        if recipient:
            stage = "send"
            client.send_message(message)
            report(stage, "accepted")
        stage = "quit"
    report("complete", "passed")
except Exception as error:
    # Never log SMTP response text, credentials, recipients, or message contents.
    report(stage, "failed", error)
    sys.exit(1)
"""


def read_json(arguments: list[str], label: str) -> dict:
    result = subprocess.run(
        ["gcloud", *arguments, "--format=json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        sys.exit(f"Could not read {label}. Check gcloud permissions.")
    try:
        return json.loads(result.stdout)
    except ValueError:
        sys.exit(f"Unexpected JSON for {label}.")


def serving_revision(service: dict) -> str:
    status = service.get("status", {})
    ready = status.get("latestReadyRevisionName", "")
    revisions = {
        entry.get("revisionName") or ready
        for entry in status.get("traffic", [])
        if entry.get("percent", 0) > 0
    } or {ready}
    if len(revisions) != 1 or "" in revisions:
        sys.exit(
            "Expected exactly one serving API revision; check traffic configuration."
        )
    return revisions.pop()


def make_job(
    revision: dict, project: str, region: str, name: str, recipient: str
) -> dict:
    spec = revision.get("spec", {})
    containers = spec.get("containers", [])
    if len(containers) != 1:
        sys.exit("Probe requires an API with exactly one container.")
    image = revision.get("status", {}).get("imageDigest", "")
    if "@sha256:" not in image:
        sys.exit("Could not find the serving API's immutable image digest.")
    identity = spec.get("serviceAccountName", "")
    if not identity:
        sys.exit("Expected an explicitly configured API service account.")
    environment = {entry["name"]: entry for entry in containers[0].get("env", [])}
    required = (
        "AUTH_EMAIL_FROM",
        "AUTH_SMTP_HOST",
        "AUTH_SMTP_USERNAME",
        "AUTH_SMTP_PASSWORD",
    )
    if any(field not in environment for field in required):
        sys.exit("API is missing required SMTP settings.")
    password = (
        environment["AUTH_SMTP_PASSWORD"].get("valueFrom", {}).get("secretKeyRef", {})
    )
    if not password.get("name") or not str(password.get("key", "")).isdigit():
        sys.exit("Probe requires a pinned numeric SMTP password secret reference.")
    for field in SMTP_FIELDS:
        if (
            field in environment
            and field != "AUTH_SMTP_PASSWORD"
            and "value" not in environment[field]
        ):
            sys.exit("Probe expects non-password SMTP settings as plaintext values.")
    annotations = revision.get("metadata", {}).get("annotations", {})
    network = {
        field: annotations[field] for field in NETWORK_FIELDS if field in annotations
    }
    alias = password["name"]
    for entry in annotations.get("run.googleapis.com/secrets", "").split(","):
        if entry.partition(":")[0] == alias:
            network["run.googleapis.com/secrets"] = entry
    job_env = [environment[field] for field in SMTP_FIELDS if field in environment]
    if recipient:
        job_env.append({"name": "PROBE_RECIPIENT", "value": recipient})
    return {
        "apiVersion": "run.googleapis.com/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "namespace": revision.get("metadata", {}).get("namespace", project),
            "labels": {"cloud.googleapis.com/location": region},
        },
        "spec": {
            "template": {
                "metadata": {"annotations": network},
                "spec": {
                    "taskCount": 1,
                    "parallelism": 1,
                    "template": {
                        "spec": {
                            "serviceAccountName": identity,
                            "maxRetries": 0,
                            "timeoutSeconds": "180",
                            "containers": [
                                {
                                    "image": image,
                                    "command": ["python"],
                                    "args": ["-c", PROBE],
                                    "env": job_env,
                                    "resources": {
                                        "limits": {"cpu": "1", "memory": "512Mi"}
                                    },
                                }
                            ],
                        }
                    },
                },
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", default=os.environ.get("GCP_PROJECT_ID", "serp-saas")
    )
    parser.add_argument(
        "--region", default=os.environ.get("GCP_LOCATION", "asia-southeast1")
    )
    parser.add_argument(
        "--run", action="store_true", help="Create and execute one diagnostic job."
    )
    parser.add_argument(
        "--recipient",
        default="",
        help="Send one test email to your address; omit for login only.",
    )
    args = parser.parse_args()
    if args.recipient and not re.fullmatch(
        r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", args.recipient
    ):
        sys.exit("Provide a plain recipient email address.")
    if not shutil.which("gcloud"):
        sys.exit("Run in authenticated Cloud Shell with gcloud installed.")
    common = [f"--project={args.project}", f"--region={args.region}"]
    service = read_json(
        ["run", "services", "describe", "serp-api", *common], "API service"
    )
    revision_name = serving_revision(service)
    revision = read_json(
        ["run", "revisions", "describe", revision_name, *common], "API revision"
    )
    name = f"serp-auth-email-probe-{secrets.token_hex(4)}"
    job = make_job(revision, args.project, args.region, name, args.recipient)
    print(f"Source serving revision: {revision_name}", flush=True)
    print(
        "Probe uses the API image digest, service account, SMTP secret reference and VPC settings.",
        flush=True,
    )
    print("A separate Cloud Run instance may have a different outbound IP.", flush=True)
    smtp_environment = {
        entry["name"]: entry
        for entry in revision["spec"]["containers"][0].get("env", [])
    }
    hostname = smtp_environment.get("AUTH_SMTP_LOCAL_HOSTNAME", {}).get(
        "value", "app.serpsaas.com"
    )
    print(f"Probe HELO/EHLO: {hostname}", flush=True)
    if "AUTH_SMTP_LOCAL_HOSTNAME" not in smtp_environment:
        print(
            "Using the updated helper's default; an older API image may use a different HELO.",
            flush=True,
        )
    print(
        "Mode: one test email." if args.recipient else "Mode: TLS and SMTP login only.",
        flush=True,
    )
    if not args.run:
        print("Plan only. Add --run to create and execute the job.")
        return
    with tempfile.TemporaryDirectory(prefix="serp-smtp-probe-") as temporary:
        path = Path(temporary) / "job.json"
        path.write_text(
            json.dumps(job)
        )  # JSON is valid YAML; contains references only.
        path.chmod(0o600)
        subprocess.run(
            ["gcloud", "run", "jobs", "replace", str(path), *common], check=True
        )
    print(f"Diagnostic job: {name}", flush=True)
    result = subprocess.run(
        ["gcloud", "run", "jobs", "execute", name, *common, "--wait"], check=False
    )
    log_filter = (
        f'resource.type="cloud_run_job" AND resource.labels.job_name="{name}" '
        'AND jsonPayload.probe="auth-email"'
    )
    print("SMTP probe results (logs can take a few seconds to appear):", flush=True)
    logs = [
        "gcloud",
        "logging",
        "read",
        log_filter,
        f"--project={args.project}",
        "--freshness=1h",
        "--limit=20",
        "--order=asc",
        "--format=table(timestamp,jsonPayload.stage,jsonPayload.outcome,jsonPayload.error_class,jsonPayload.smtp_status,jsonPayload.smtp_statuses)",
    ]
    subprocess.run(logs, check=False)
    print("Read the results again if empty:", flush=True)
    # Display exact arguments safely for copy/paste, including the log filter.
    print(shlex.join(logs), flush=True)
    print("After diagnosis, remove the diagnostic job:", flush=True)
    print(shlex.join(["gcloud", "run", "jobs", "delete", name, *common]), flush=True)
    if result.returncode:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
