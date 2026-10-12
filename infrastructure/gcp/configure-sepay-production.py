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
CURRENT_STEP = "startup"


class SetupError(RuntimeError):
    """Only messages constructed here, never raw cloud output or key values."""


def stage(name: str) -> None:
    global CURRENT_STEP
    CURRENT_STEP = name


def cloud_error_code(stderr: str) -> str:
    for code in (
        "PERMISSION_DENIED",
        "UNAUTHENTICATED",
        "NOT_FOUND",
        "ALREADY_EXISTS",
        "INVALID_ARGUMENT",
        "FAILED_PRECONDITION",
        "SERVICE_DISABLED",
        "RESOURCE_EXHAUSTED",
        "DEADLINE_EXCEEDED",
        "UNAVAILABLE",
    ):
        if re.search(rf"\b{code}\b", stderr):
            return code
    if "already been set with a different type" in stderr:
        return "ENVIRONMENT_VARIABLE_TYPE_CONFLICT"
    if "unrecognized arguments" in stderr:
        return "CLI_ARGUMENT_ERROR"
    if "permission" in stderr.lower() and "denied" in stderr.lower():
        return "PERMISSION_DENIED"
    return "COMMAND_FAILED"


def gcloud(*args: str, value: str | None = None) -> str:
    result = subprocess.run(
        ["gcloud", *args], input=value, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise SetupError(
            f"gcloud {' '.join(args[:3])} failed "
            f"({cloud_error_code(result.stderr)}); inspect Cloud Console."
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
        raise SetupError("Secret Manager did not return a numeric version.")
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
        raise SetupError("Expected one API container and an explicit runtime identity.")
    environment = {item["name"]: item for item in spec["containers"][0].get("env", [])}
    if environment.get("APP_ENV", {}).get("value") != "production":
        raise SetupError("The existing API must have APP_ENV=production.")
    return spec, environment


def verify(
    service: dict, config: dict[str, str], versions: dict[str, str] | None = None
) -> str:
    _, environment = runtime(service)
    for key, value in config.items():
        if environment.get(key, {}).get("value") != value:
            raise SetupError(f"Cloud Run configuration verification failed: {key}")
    for key, name in SECRETS.items():
        reference = (
            environment.get(key, {}).get("valueFrom", {}).get("secretKeyRef", {})
        )
        version = str(reference.get("key", ""))
        if reference.get("name") != name or not version.isdigit():
            raise SetupError(f"Expected a pinned Production secret: {key}")
        if versions and version != versions[key]:
            raise SetupError(f"Cloud Run secret version verification failed: {key}")
    status = service.get("status", {})
    revision = status.get("latestReadyRevisionName")
    if not revision or revision != status.get("latestCreatedRevisionName"):
        raise SetupError("The configured Production revision is not ready.")
    if not any(
        c.get("type") == "Ready" and c.get("status") == "True"
        for c in status.get("conditions", [])
    ):
        raise SetupError("The Cloud Run API is not ready.")
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
        raise SetupError(
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
        raise SetupError("Deploy the SePay backend before configuring Production.")


def diagnose(args: argparse.Namespace) -> None:
    """Read metadata without secret access, env dumps or traffic changes."""
    stage("diagnose_api_metadata")
    service = describe(args)
    spec = service.get("spec", {}).get("template", {}).get("spec", {})
    containers = spec.get("containers", [])
    environment = {
        item["name"]: item
        for item in (containers[0].get("env", []) if containers else [])
    }
    status = service.get("status", {})

    def enum(value: object, allowed: set[str]) -> str:
        return str(value) if value in allowed else "unexpected_or_missing"

    def revision(value: object) -> str | None:
        return (
            value
            if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,62}", value)
            else None
        )

    bindings = {}
    allowed_secrets = set(SECRETS.values()) | {
        "serp-sepay-sandbox-key",
        "serp-sepay-sandbox-ipn-key",
    }
    for key in SECRETS:
        entry = environment.get(key, {})
        ref = entry.get("valueFrom", {}).get("secretKeyRef", {})
        version = str(ref.get("key", ""))
        bindings[key] = {
            "type": "secret_reference"
            if ref
            else "literal_value"
            if "value" in entry
            else "missing",
            "secret_name": enum(ref.get("name"), allowed_secrets),
            "version": version if version.isdigit() or version == "latest" else None,
        }
    report = {
        "mode": "read_only_diagnosis",
        "service": args.service,
        "gateway_environment": enum(
            environment.get("SEPAY_ENV", {}).get("value"), {"sandbox", "production"}
        ),
        "checkout_enabled": enum(
            environment.get("SEPAY_ENABLED", {}).get("value"), {"true", "false"}
        ),
        "latest_created_revision": revision(status.get("latestCreatedRevisionName")),
        "latest_ready_revision": revision(status.get("latestReadyRevisionName")),
        "conditions": [
            {
                "type": enum(
                    c.get("type"), {"Ready", "ConfigurationsReady", "RoutesReady"}
                ),
                "status": enum(c.get("status"), {"True", "False", "Unknown"}),
            }
            for c in status.get("conditions", [])
        ],
        "traffic": [
            {
                "revision": revision(t.get("revisionName")),
                "percent": int(t.get("percent") or 0),
            }
            for t in status.get("traffic", [])
        ],
        "secret_bindings": bindings,
        "production_secret_versions": {},
    }
    stage("diagnose_production_secret_metadata")
    existing = json.loads(
        gcloud("secrets", "list", f"--project={args.project}", "--format=json(name)")
    )
    names = {item["name"].rsplit("/", 1)[-1] for item in existing}
    for name in SECRETS.values():
        if name not in names:
            report["production_secret_versions"][name] = {"exists": False}
            continue
        try:
            versions = json.loads(
                gcloud(
                    "secrets",
                    "versions",
                    "list",
                    name,
                    f"--project={args.project}",
                    "--limit=5",
                    "--sort-by=~createTime",
                    "--format=json(name,state)",
                )
            )
            report["production_secret_versions"][name] = {
                "exists": True,
                "versions": [
                    {
                        "version": v["name"].rsplit("/", 1)[-1]
                        if v["name"].rsplit("/", 1)[-1].isdigit()
                        else None,
                        "state": enum(
                            v.get("state"), {"ENABLED", "DISABLED", "DESTROYED"}
                        ),
                    }
                    for v in versions
                ],
            }
        except SetupError as error:
            report["production_secret_versions"][name] = {
                "exists": True,
                "error": str(error),
            }
    print(json.dumps(report, indent=2))


def main() -> None:
    stage("startup")
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
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Read-only metadata diagnosis; no key prompts or cloud mutations.",
    )
    args = parser.parse_args()
    if not shutil.which("gcloud"):
        sys.exit("Run in an authenticated Google Cloud Shell.")
    if args.diagnose:
        diagnose(args)
        return
    stage("public_api_preflight")
    preflight()
    stage("inspect_existing_api")
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
        stage("verify_current_production_configuration")
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
    stage("validate_production_input")
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
    versions = {}
    for key, name in SECRETS.items():
        stage(f"store_production_secret:{key}")
        versions[key] = add_secret(args.project, name, keys[key], identity)
    keys.clear()
    environment_flag = "^|^" + "|".join(
        f"{key}={value}" for key, value in config.items()
    )
    bindings = ",".join(
        f"{key}={SECRETS[key]}:{version}" for key, version in versions.items()
    )
    stage("deploy_production_revision_without_traffic")
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
    stage("verify_staged_production_revision")
    staged = describe(args)
    revision = verify(staged, config, versions)
    staged_spec, _ = runtime(staged)
    if (
        staged_spec["serviceAccountName"] != identity
        or staged_spec["containers"][0]["image"] != image
    ):
        raise SetupError(
            "API identity/image changed during setup; no traffic was promoted."
        )
    stage("promote_verified_production_revision")
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
    stage("verify_production_traffic")
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


def run() -> None:
    try:
        main()
    except SetupError as error:
        sys.exit(f"Production setup failed at [{CURRENT_STEP}]: {error}")
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, EOFError):
        sys.exit(
            f"Production setup failed at [{CURRENT_STEP}]. "
            "Unexpected response or connection/input error; "
            "no raw cloud output or secret values were printed."
        )


if __name__ == "__main__":
    run()
