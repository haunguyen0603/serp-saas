#!/usr/bin/env python3
"""Stage the commercial-domain LB and verify exact canonical responses."""

import argparse
import datetime
import ipaddress
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "canonical-redirects"
PROJECT = "serp-saas"
PREFIX = "serp-canonical"


def command(args, *, capture=False, env=None):
    return subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        env=env,
    ).stdout


def gcloud(*args):
    return command(
        ["gcloud", *args, f"--project={PROJECT}", "--format=json"], capture=True
    )


def require_active_certificate():
    cert = json.loads(
        gcloud("certificate-manager", "certificates", "describe", f"{PREFIX}-cert")
    )
    if cert.get("managed", {}).get("state") != "ACTIVE":
        raise RuntimeError(
            "Certificate is not ACTIVE. Add both authorization CNAMEs and run status again."
        )
    for key in ("apex", "www"):
        entry = json.loads(
            gcloud(
                "certificate-manager",
                "maps",
                "entries",
                "describe",
                f"{PREFIX}-{key}",
                f"--map={PREFIX}-certmap",
            )
        )
        if entry.get("state") != "ACTIVE":
            raise RuntimeError(f"Certificate map entry {key} is not ACTIVE yet.")


def terraform(args, *, capture=False, env=None):
    return command(["terraform", f"-chdir={ROOT}", *args], capture=capture, env=env)


def require_terraform():
    hint = (
        "Install the real Terraform CLI (>= 1.7, < 2.0) using the Cloud Shell "
        "installation steps in docs/architecture/cloud-run-canonical-redirects.md. "
        "The Cloud Shell placeholder prints installation instructions instead of JSON."
    )
    try:
        raw = command(["terraform", "version", "-json"], capture=True)
        info = json.loads(raw)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise RuntimeError(hint) from error
    version = info.get("terraform_version", "") if isinstance(info, dict) else ""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", str(version))
    if not match or not (1, 7, 0) <= tuple(map(int, match.groups())) < (2, 0, 0):
        raise RuntimeError(f"Unsupported Terraform version {version!r}. {hint}")


def require_prepare_state(env):
    # Unlike `state list`, `show -json` succeeds before the first apply and
    # returns only format_version. Real backend/state errors still propagate.
    try:
        state = json.loads(terraform(["show", "-json"], capture=True, env=env))
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Terraform current state did not return JSON; no plan or apply was attempted."
        ) from error
    if not isinstance(state, dict):
        raise RuntimeError(  # noqa: TRY004 - malformed external CLI data, not a caller type error.
            "Invalid Terraform current state; no plan or apply was attempted."
        )

    def has_load_balancer(module):
        return any(
            resource.get("type") == "google_compute_global_forwarding_rule"
            for resource in module.get("resources", [])
        ) or any(has_load_balancer(child) for child in module.get("child_modules", []))

    if has_load_balancer(state.get("values", {}).get("root_module", {})):
        raise RuntimeError(
            "LB is already deployed. Use plan --phase=deploy or deploy, never prepare again."
        )


def infrastructure(action, phase):
    if action == "prepare":
        phase = "prepare"
    if action == "status":
        print(
            gcloud("certificate-manager", "certificates", "describe", f"{PREFIX}-cert")
        )
        require_active_certificate()
        print("Certificate and both map entries are ACTIVE; ready for deploy.")
        return
    require_terraform()
    if action == "deploy":
        phase = "deploy"
        require_active_certificate()
        service = json.loads(
            gcloud(
                "run", "services", "describe", "serp-web", "--region=asia-southeast1"
            )
        )
        ingress = (
            service.get("metadata", {})
            .get("annotations", {})
            .get("run.googleapis.com/ingress", "all")
        )
        if ingress not in {"all", "internal-and-cloud-load-balancing"}:
            raise RuntimeError(
                f"serp-web ingress {ingress!r} does not allow this load balancer."
            )
    token = command(["gcloud", "auth", "print-access-token"], capture=True).strip()
    if not token:
        raise RuntimeError(
            "No GCP access token. Run this helper in authenticated Cloud Shell."
        )
    env = dict(os.environ, GOOGLE_OAUTH_ACCESS_TOKEN=token)
    terraform(["init", "-input=false"], env=env)
    if phase == "prepare":
        require_prepare_state(env)
    plan = ROOT / "canonical.tfplan"
    terraform(
        [
            "plan",
            "-input=false",
            f"-var=enable_load_balancer={str(phase == 'deploy').lower()}",
            f"-out={plan}",
        ],
        env=env,
    )
    try:
        rendered = json.loads(
            terraform(["show", "-json", str(plan)], capture=True, env=env)
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "terraform show -json did not return JSON; no apply was attempted. "
            "Check terraform version -json and rerun the plan."
        ) from error
    destructive = [
        r["address"]
        for r in rendered.get("resource_changes", [])
        if "delete" in r["change"]["actions"]
    ]
    if destructive:
        raise RuntimeError(
            f"Refusing deletions/replacements: {destructive}. Review state/config first."
        )
    if action != "plan":
        terraform(["apply", "-input=false", str(plan)], env=env)
        terraform(["output"], env=env)


def last_response(raw):
    """Ignore a CONNECT proxy header and parse the actual final response block."""
    blocks = re.split(r"\r?\n\r?\n", raw)
    responses = [block for block in blocks if block.startswith("HTTP/")]
    if not responses:
        return 0, {}
    lines = responses[-1].splitlines()
    status = int(lines[0].split()[1])
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.lower()] = value.strip()
    return status, headers


def canonical_url(url):
    # GCP's HTTP-to-HTTPS redirect may include the default HTTPS port. Normalize
    # only that exact apex authority, leaving path/query bytes untouched.
    prefix = "https://serpsaas.com:443/"
    if isinstance(url, str) and url.startswith(prefix):
        return "https://serpsaas.com/" + url[len(prefix) :]
    return url


def check(
    url,
    *,
    expected_status,
    expected_location=None,
    ip=None,
    method="HEAD",
    follow=False,
    ua=None,
    doh_url=None,
):
    args = [
        "curl",
        "--silent",
        "--show-error",
        "--connect-timeout",
        "10",
        "--max-time",
        "30",
    ]
    args += (
        ["--head"]
        if method == "HEAD"
        else ["--dump-header", "-", "--output", os.devnull]
    )
    if ip:
        # The migration check must connect directly to the new IP, not a proxy
        # that resolves the old DNS. Keep TLS verification, original Host and SNI.
        args += ["--noproxy", "*"]
        for host in ("serpsaas.com", "www.serpsaas.com"):
            for port in (80, 443):
                args += ["--resolve", f"{host}:{port}:{ip}"]
    elif doh_url:
        # Resolve live production records with the chosen public resolver,
        # avoiding stale system DNS without pinning the destination IP.
        args += ["--doh-url", doh_url, "--noproxy", "*"]
    if follow:
        args += ["--location", "--max-redirs", "3"]
    if ua:
        args += ["--user-agent", ua]
    args += [
        "--write-out",
        "\nFINAL_URL=%{url_effective}\nREMOTE_IP=%{remote_ip}\n",
        url,
    ]
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    status, headers = last_response(result.stdout)
    passed = result.returncode == 0 and status == expected_status
    final_match = re.search(r"^FINAL_URL=(.*)$", result.stdout, flags=re.MULTILINE)
    final_url = final_match.group(1) if final_match else None
    if expected_location is not None:
        passed = passed and canonical_url(headers.get("location")) == expected_location
    if follow:
        passed = passed and canonical_url(final_url) == "https://serpsaas.com/"
    return {
        "url": url,
        "method": method,
        "command": args,
        "status": status,
        "location": headers.get("location"),
        "normalized_location": canonical_url(headers.get("location")),
        "final_url": final_url,
        "normalized_final_url": canonical_url(final_url),
        "expected_status": expected_status,
        "expected_location": expected_location,
        "passed": passed,
        "exit_code": result.returncode,
        "output": result.stdout,
        "error": result.stderr,
    }


def verify(ip, output, doh_url=None):
    if ip:
        ipaddress.IPv4Address(ip)
    rows = []
    # Every alias and both methods; preserve exact path/query while allowing only
    # the equivalent default HTTPS port on the canonical apex authority.
    paths = (
        "/",
        "/pricing",
        "/pricing?utm_source=canonical-check&probe=1",
        "/pricing?next=%2Fapp%3Fx%3D1&tag=a&tag=b",
    )
    origins = (
        "http://serpsaas.com",
        "http://www.serpsaas.com",
        "https://www.serpsaas.com",
    )
    for origin in origins:
        for path in paths:
            for method in ("HEAD", "GET"):
                rows.append(
                    check(
                        origin + path,
                        expected_status=301,
                        expected_location="https://serpsaas.com" + path,
                        ip=ip,
                        doh_url=doh_url,
                        method=method,
                    )
                )
    for path in ("/", "/pricing"):
        rows.append(
            check(
                "https://serpsaas.com" + path,
                expected_status=200,
                ip=ip,
                doh_url=doh_url,
            )
        )
    rows.append(
        check(
            "http://serpsaas.com/",
            expected_status=200,
            ip=ip,
            follow=True,
            doh_url=doh_url,
        )
    )
    rows.append(
        check(
            "http://serpsaas.com/",
            expected_status=301,
            expected_location="https://serpsaas.com/",
            ip=ip,
            doh_url=doh_url,
            method="GET",
            ua="Googlebot",
        )
    )
    report = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": "preflight" if ip else "production-dns",
        "load_balancer_ip": ip,
        "dns_over_https_resolver": doh_url,
        "passed": all(row["passed"] for row in rows),
        "results": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    for row in rows:
        print(
            f"{'PASS' if row['passed'] else 'FAIL'} {row['method']} {row['url']} -> {row['status']} {row['location'] or ''}"
        )
    print(f"Evidence: {output}")
    return report["passed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("plan", "prepare", "status", "deploy", "preflight", "verify")
    )
    parser.add_argument("--phase", choices=("prepare", "deploy"), default="prepare")
    parser.add_argument("--ip", help="New LB IPv4 address, required for preflight.")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--doh-url", help="Optional HTTPS DNS resolver for production verification."
    )
    args = parser.parse_args()
    if args.action in {"preflight", "verify"}:
        if args.action == "preflight" and not args.ip:
            parser.error(
                "preflight requires --ip from terraform output -raw load_balancer_ip"
            )
        if args.action == "verify" and args.ip:
            parser.error("verify checks production DNS; use preflight for --ip")
        if args.doh_url and (
            args.action != "verify" or not args.doh_url.startswith("https://")
        ):
            parser.error("--doh-url requires verify and an HTTPS resolver URL")
        output = args.output or Path(f"canonical-{args.action}.json")
        return 0 if verify(args.ip, output, args.doh_url) else 1
    infrastructure(args.action, args.phase)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
