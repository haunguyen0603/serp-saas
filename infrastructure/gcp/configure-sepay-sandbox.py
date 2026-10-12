#!/usr/bin/env python3
"""Configure the existing production API for SePay Sandbox using pinned secrets."""

import argparse
import getpass
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import UUID

CHECKOUT_URL = "https://pay-sandbox.sepay.vn/v1/checkout/init"
SECRETS = {
    "SEPAY_SECRET_KEY": "serp-sepay-sandbox-key",
    "SEPAY_IPN_SECRET_KEY": "serp-sepay-sandbox-ipn-key",
}


def gcloud(*args: str, value: str | None = None) -> str:
    result = subprocess.run(
        ["gcloud", *args], input=value, text=True, capture_output=True, check=False
    )
    if result.returncode:
        # Never echo subprocess output: deployment errors can include environment values.
        raise RuntimeError(
            f"gcloud {' '.join(args[:3])} failed; inspect IAM/authentication in Cloud Console."
        )
    return result.stdout.strip()


def load_env(path: str | None) -> dict[str, str]:
    values = {}
    if path:
        for line in Path(path).read_text().splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ")
            if key.startswith("SEPAY_"):
                parts = shlex.split(value, comments=True)
                values[key] = parts[0] if parts else ""
    return values


def nonsecret_config(values: dict[str, str], merchant: str) -> dict[str, str]:
    checkout = values.get("SEPAY_CHECKOUT_URL") or CHECKOUT_URL
    if checkout != CHECKOUT_URL:
        raise ValueError(
            "Use the documented Sandbox checkout URL; production/other hosts are rejected."
        )
    if values.get("SEPAY_ENV", "sandbox") != "sandbox":
        raise ValueError("This helper only configures sandbox.")
    if not merchant or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", merchant):
        raise ValueError("Enter a valid Sandbox Merchant ID.")
    config = {
        "SEPAY_ENABLED": "true",
        "SEPAY_ENV": "sandbox",
        "SEPAY_MERCHANT_ID": merchant,
        "SEPAY_CHECKOUT_URL": checkout,
        "SEPAY_PENDING_MINUTES": "45",
    }
    for name in ("success", "error", "cancel"):
        key = f"SEPAY_{name.upper()}_URL"
        value = (
            values.get(key)
            or f"https://app.serpsaas.com/app/change-plan/payment/{name}"
        )
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or url.hostname != "app.serpsaas.com"
            or url.path != f"/app/change-plan/payment/{name}"
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError(f"{key} must be the application HTTPS payment route.")
        config[key] = value
    return config


def add_secret(project: str, name: str, value: str, identity: str) -> str:
    # Describe failures do not imply nonexistence; list avoids accidentally treating denied access as missing.
    existing = json.loads(
        gcloud("secrets", "list", f"--project={project}", "--format=json(name)")
    )
    if not any(item["name"].rsplit("/", 1)[-1] == name for item in existing):
        gcloud(
            "secrets",
            "create",
            name,
            f"--project={project}",
            "--replication-policy=automatic",
            "--quiet",
        )
    version = gcloud(
        "secrets",
        "versions",
        "add",
        name,
        f"--project={project}",
        "--data-file=-",
        "--format=value(name)",
        value=value,
    )
    number = version.rsplit("/", 1)[-1]
    if not number.isdigit():
        raise RuntimeError("Secret Manager did not return a numeric version.")
    gcloud(
        "secrets",
        "add-iam-policy-binding",
        name,
        f"--project={project}",
        f"--member=serviceAccount:{identity}",
        "--role=roles/secretmanager.secretAccessor",
        "--quiet",
    )
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="serp-saas")
    parser.add_argument("--region", default="asia-southeast1")
    parser.add_argument("--service", default="serp-api")
    parser.add_argument("--merchant-id")
    parser.add_argument(
        "--sandbox-user-id",
        action="append",
        type=UUID,
        default=[],
        help="Allow a specific QA user UUID in addition to platform admins.",
    )
    parser.add_argument(
        "--env-file", help="Optional ignored local .env; values are never printed."
    )
    args = parser.parse_args()
    if not shutil.which("gcloud"):
        sys.exit("Run in an authenticated Google Cloud Shell.")
    values = load_env(args.env_file)
    merchant = args.merchant_id or values.get("SEPAY_MERCHANT_ID")
    if not merchant:
        merchant = input("Sandbox Merchant ID: ").strip()
    config = nonsecret_config(values, merchant)
    config["SEPAY_SANDBOX_ALLOWED_USER_IDS"] = json.dumps(
        [str(uid) for uid in args.sandbox_user_id]
    )
    # Readiness preflight before any secrets/IAM/service mutation.
    with urlopen("https://api.serpsaas.com/openapi.json", timeout=30) as response:
        paths = json.load(response).get("paths", {})
    if "/api/v1/billing/payments/sepay/ipn" not in paths:
        sys.exit(
            "M7K API is not deployed yet. Wait for the backend pipeline before configuring Sandbox."
        )
    service = json.loads(
        gcloud(
            "run",
            "services",
            "describe",
            args.service,
            f"--project={args.project}",
            f"--region={args.region}",
            "--format=json",
        )
    )
    spec = service["spec"]["template"]["spec"]
    identity = spec.get("serviceAccountName")
    if not identity or len(spec.get("containers", [])) != 1:
        sys.exit("Expected one API container and an explicit runtime service account.")
    before = service.get("status", {}).get("latestReadyRevisionName")
    keys = {}
    for key in SECRETS:
        value = values.get(key)
        if not value:
            if not sys.stdin.isatty():
                sys.exit("Run interactively to enter keys without echo.")
            value = getpass.getpass(f"{key} (Sandbox; hidden): ")
        if not value or value.isspace():
            sys.exit(f"{key} must be nonempty.")
        keys[key] = value
    versions = {
        key: add_secret(args.project, name, keys[key], identity)
        for key, name in SECRETS.items()
    }
    keys.clear()
    # Partial update preserves image, other secrets/env, Cloud SQL, IAM, scaling and worker.
    environment = "^|^" + "|".join(f"{key}={value}" for key, value in config.items())
    bindings = ",".join(
        f"{key}={SECRETS[key]}:{version}" for key, version in versions.items()
    )
    gcloud(
        "run",
        "services",
        "update",
        args.service,
        f"--project={args.project}",
        f"--region={args.region}",
        f"--update-env-vars={environment}",
        f"--update-secrets={bindings}",
        "--quiet",
    )
    gcloud(
        "run",
        "services",
        "update-traffic",
        args.service,
        f"--project={args.project}",
        f"--region={args.region}",
        "--to-latest",
        "--quiet",
    )
    after = json.loads(
        gcloud(
            "run",
            "services",
            "describe",
            args.service,
            f"--project={args.project}",
            f"--region={args.region}",
            "--format=json",
        )
    )
    revision = after.get("status", {}).get("latestReadyRevisionName")
    environment_after = {
        item["name"]: item
        for item in after["spec"]["template"]["spec"]["containers"][0].get("env", [])
    }
    for key, value in config.items():
        if environment_after.get(key, {}).get("value") != value:
            raise RuntimeError(f"Cloud Run configuration verification failed: {key}")
    for key, version in versions.items():
        reference = (
            environment_after.get(key, {}).get("valueFrom", {}).get("secretKeyRef", {})
        )
        if reference.get("key") != version or reference.get("name") != SECRETS[key]:
            raise RuntimeError(f"Cloud Run secret reference verification failed: {key}")
    print(
        json.dumps(
            {
                "service": args.service,
                "project": args.project,
                "region": args.region,
                "environment": "sandbox",
                "checkout_access": "platform admins plus configured QA user UUIDs",
                "checkout_url": CHECKOUT_URL,
                "previous_revision": before,
                "ready_revision": revision,
                "secret_versions": versions,
                "ipn_url": "https://api.serpsaas.com/api/v1/billing/payments/sepay/ipn",
            },
            indent=2,
        )
    )
    print(
        "In SePay Sandbox, configure IPN auth SECRET_KEY using the same SEPAY_IPN_SECRET_KEY."
    )
    print(
        "Use a dedicated QA account: Sandbox IPNs update subscriptions in the application database."
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError):
        sys.exit(
            "Sandbox configuration did not complete. Check Cloud Console/authentication; no secret values were printed."
        )
