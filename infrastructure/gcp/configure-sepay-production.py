#!/usr/bin/env python3
"""Enable the real SePay gateway on the existing API using Production secrets."""

import argparse
import getpass
import json
import re
import shutil
import subprocess
import sys
from urllib.request import urlopen

CHECKOUT_URL = "https://pay.sepay.vn/v1/checkout/init"
VOID_URL = "https://pgapi.sepay.vn/v1/order/voidTransaction"
IPN_URL = "https://api.serpsaas.com/api/v1/billing/payments/sepay/ipn"
SECRETS = {
    "SEPAY_SECRET_KEY": "serp-sepay-production-key",
    "SEPAY_IPN_SECRET_KEY": "serp-sepay-production-ipn-key",
}


def gcloud(*args: str, value: str | None = None) -> str:
    result = subprocess.run(
        ["gcloud", *args], input=value, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"gcloud {' '.join(args[:3])} failed; inspect Cloud Console."
        )
    return result.stdout.strip()


def nonsecret_config(merchant: str) -> dict[str, str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", merchant):
        raise ValueError("Enter a valid Production Merchant ID.")
    if merchant.upper().startswith("SP-TEST-"):
        raise ValueError("Use a Production Merchant ID, not an SP-TEST merchant.")
    return {
        "SEPAY_ENABLED": "true",
        "SEPAY_ENV": "production",
        "SEPAY_MERCHANT_ID": merchant,
        "SEPAY_CHECKOUT_URL": CHECKOUT_URL,
        "SEPAY_VOID_URL": VOID_URL,
        "SEPAY_SANDBOX_ALLOWED_USER_IDS": "[]",
        "SEPAY_PENDING_MINUTES": "45",
        **{
            f"SEPAY_{name.upper()}_URL": f"https://app.serpsaas.com/app/change-plan/payment/{name}"
            for name in ("success", "error", "cancel")
        },
    }


def add_secret(project: str, name: str, value: str, identity: str) -> str:
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
    ).rsplit("/", 1)[-1]
    if not version.isdigit():
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
    return version


def describe(args: argparse.Namespace) -> dict:
    return json.loads(
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


def runtime(service: dict) -> tuple[dict, dict]:
    spec = service["spec"]["template"]["spec"]
    if not spec.get("serviceAccountName") or len(spec.get("containers", [])) != 1:
        raise RuntimeError(
            "Expected one API container and an explicit runtime identity."
        )
    environment = {item["name"]: item for item in spec["containers"][0].get("env", [])}
    if environment.get("APP_ENV", {}).get("value") != "production":
        raise RuntimeError("The existing API must have APP_ENV=production.")
    return spec, environment


def verify(
    service: dict, config: dict[str, str], versions: dict[str, str] | None = None
) -> str:
    _, environment = runtime(service)
    for key, value in config.items():
        if environment.get(key, {}).get("value") != value:
            raise RuntimeError(f"Cloud Run configuration verification failed: {key}")
    for key, name in SECRETS.items():
        reference = (
            environment.get(key, {}).get("valueFrom", {}).get("secretKeyRef", {})
        )
        version = str(reference.get("key", ""))
        if reference.get("name") != name or not version.isdigit():
            raise RuntimeError(f"Expected a pinned Production secret: {key}")
        if versions and version != versions[key]:
            raise RuntimeError(f"Cloud Run secret version verification failed: {key}")
    status = service.get("status", {})
    revision = status.get("latestReadyRevisionName")
    if not revision or revision != status.get("latestCreatedRevisionName"):
        raise RuntimeError("The configured Production revision is not ready.")
    if not any(
        c.get("type") == "Ready" and c.get("status") == "True"
        for c in status.get("conditions", [])
    ):
        raise RuntimeError("The Cloud Run API is not ready.")
    return revision


def verify_traffic(service: dict, revision: str) -> None:
    targets = service.get("status", {}).get("traffic", [])
    if (
        sum(
            int(t.get("percent", 0))
            for t in targets
            if t.get("revisionName") == revision
        )
        != 100
    ):
        raise RuntimeError(
            "Expected all API traffic on the verified Production revision."
        )


def preflight() -> None:
    with urlopen("https://api.serpsaas.com/openapi.json", timeout=30) as response:
        paths = json.load(response).get("paths", {})
    required = (
        "/api/v1/billing/payments/sepay/checkout",
        "/api/v1/billing/payments/sepay/options",
        "/api/v1/billing/payments/sepay/ipn",
    )
    if any(path not in paths for path in required):
        raise RuntimeError("Deploy the SePay backend before configuring Production.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="serp-saas")
    parser.add_argument("--region", default="asia-southeast1")
    parser.add_argument("--service", default="serp-api")
    parser.add_argument("--merchant-id")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only verification; no key prompts or changes.",
    )
    args = parser.parse_args()
    if not shutil.which("gcloud"):
        sys.exit("Run in an authenticated Google Cloud Shell.")
    preflight()
    before = describe(args)
    spec, environment = runtime(before)
    previous_traffic = [
        {
            "revision": target.get("revisionName"),
            "percent": int(target.get("percent") or 0),
        }
        for target in before.get("status", {}).get("traffic", [])
        if int(target.get("percent") or 0) > 0
    ]
    if args.check:
        merchant = environment.get("SEPAY_MERCHANT_ID", {}).get("value", "")
        revision = verify(before, nonsecret_config(merchant))
        verify_traffic(before, revision)
        print(
            json.dumps(
                {
                    "service": args.service,
                    "environment": "production",
                    "ready_revision": revision,
                    "checkout_url": CHECKOUT_URL,
                    "verified": True,
                },
                indent=2,
            )
        )
        return
    if not sys.stdin.isatty():
        sys.exit("Run interactively to enter Production keys without echo.")
    merchant = args.merchant_id or input("Production Merchant ID: ").strip()
    config = nonsecret_config(merchant)
    keys = {key: getpass.getpass(f"{key} (Production; hidden): ") for key in SECRETS}
    if any(
        not value or value != value.strip() or "\n" in value or "\r" in value
        for value in keys.values()
    ):
        sys.exit("Enter nonempty Production keys without whitespace or line breaks.")
    if keys["SEPAY_SECRET_KEY"].startswith("spsk_test_"):
        sys.exit("Use the Production merchant signing key.")
    if keys["SEPAY_SECRET_KEY"] == keys["SEPAY_IPN_SECRET_KEY"]:
        sys.exit("Use an independent Production IPN key.")
    identity = spec["serviceAccountName"]
    image = spec["containers"][0]["image"]
    versions = {
        key: add_secret(args.project, name, keys[key], identity)
        for key, name in SECRETS.items()
    }
    keys.clear()
    environment_flag = "^|^" + "|".join(
        f"{key}={value}" for key, value in config.items()
    )
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
        f"--update-env-vars={environment_flag}",
        f"--update-secrets={bindings}",
        "--no-traffic",
        "--quiet",
    )
    staged = describe(args)
    revision = verify(staged, config, versions)
    staged_spec, _ = runtime(staged)
    if (
        staged_spec["serviceAccountName"] != identity
        or staged_spec["containers"][0]["image"] != image
    ):
        raise RuntimeError(
            "API identity/image changed during setup; no traffic was promoted."
        )
    gcloud(
        "run",
        "services",
        "update-traffic",
        args.service,
        f"--project={args.project}",
        f"--region={args.region}",
        f"--to-revisions={revision}=100",
        "--quiet",
    )
    after = describe(args)
    verify(after, config, versions)
    verify_traffic(after, revision)
    print(
        json.dumps(
            {
                "service": args.service,
                "project": args.project,
                "region": args.region,
                "environment": "production",
                "checkout_access": "eligible verified customers",
                "checkout_url": CHECKOUT_URL,
                "ipn_url": IPN_URL,
                "previous_revision": previous_traffic[0]["revision"]
                if len(previous_traffic) == 1 and previous_traffic[0]["percent"] == 100
                else None,
                "previous_traffic": previous_traffic,
                "ready_revision": revision,
                "secret_versions": versions,
                "verified": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, EOFError):
        sys.exit(
            "Production configuration did not complete. "
            "Inspect Cloud Console revision/IAM status; secret values were not printed."
        )
