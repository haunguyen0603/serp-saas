#!/usr/bin/env python3
"""Package current source, including uncommitted files, for Cloud Shell upload."""

import argparse
import subprocess
import tarfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--domains",
        action="store_true",
        help="Package full source for the commercial/application domain rollout.",
    )
    group.add_argument(
        "--runtime-guide",
        action="store_true",
        help="Package only API/worker helpers and docs for an existing checkout.",
    )
    group.add_argument(
        "--frontend-guide",
        action="store_true",
        help="Package API/worker and frontend helpers/docs for an existing checkout.",
    )
    group.add_argument(
        "--ci-guide",
        action="store_true",
        help="Package CI/CD helpers, build configs and docs for Cloud Shell setup.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.ci_guide:
        filename = "serp-saas-cloudrun-ci.tar.gz"
    elif args.domains:
        filename = "serp-saas-domains.tar.gz"
    elif args.frontend_guide:
        filename = "serp-saas-cloudrun-frontend.tar.gz"
    elif args.runtime_guide:
        filename = "serp-saas-cloudrun-guide.tar.gz"
    else:
        filename = "serp-saas-cloudshell.tar.gz"
    destination = root / "dist" / filename
    if args.ci_guide:
        files = [
            "docs/architecture/cloud-run-ci-cd.md",
            "infrastructure/gcp/cloud-run-ci.sh",
            "infrastructure/gcp/cloud-run-release.sh",
            "infrastructure/gcp/cloudbuild-frontend-cd.yaml",
            "infrastructure/gcp/cloudbuild-backend-cd.yaml",
            "infrastructure/gcp/cloud-run-frontend.sh",
            "infrastructure/gcp/cloudbuild-frontend.yaml",
            "infrastructure/gcp/package-cloudshell.py",
            "infrastructure/gcp/tests/test_cloud_run_ci.py",
        ]
    elif args.runtime_guide or args.frontend_guide:
        files = [
            "README.md",
            "docs/architecture/cloud-run-deployment.md",
            "docs/architecture/cloud-sql-deployment.md",
            "docs/architecture/cloud-tasks-deployment.md",
            "docs/architecture/email-verification.md",
            "infrastructure/configure-rank-queue.sh",
            "infrastructure/gcp/cloud-run-services.sh",
            "infrastructure/gcp/create-cloud-run-config.py",
            "infrastructure/gcp/create-runtime-secret.py",
            "infrastructure/gcp/diagnose-auth-email.py",
            "infrastructure/gcp/probe-auth-email-cloudrun.py",
            "infrastructure/gcp/package-cloudshell.py",
        ]
        if args.frontend_guide:
            files.extend(
                [
                    "docs/architecture/cloud-run-frontend-deployment.md",
                    "infrastructure/gcp/cloudbuild-frontend.yaml",
                    "infrastructure/gcp/cloud-run-frontend.sh",
                ]
            )
    else:
        files = (
            subprocess.check_output(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                cwd=root,
            )
            .decode()
            .split("\0")
        )
    excluded = {
        ".git",
        ".codex",
        ".agents",
        ".aws",
        ".secrets",
        ".venv",
        ".tools",
        "node_modules",
        ".next",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "test-results",
        "playwright-report",
    }
    destination.parent.mkdir(exist_ok=True)
    count = 0
    with tarfile.open(destination, "w:gz") as archive:
        for name in sorted(set(files)):
            if not name:
                continue
            relative = Path(name)
            source = root / relative
            if (
                any(part in excluded for part in relative.parts)
                or any(
                    part.startswith(".env") and part != ".env.example"
                    for part in relative.parts
                )
                or source.suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
                or "credentials" in source.name.lower()
                or "service-account" in source.name.lower()
                or source.is_symlink()
                or not source.is_file()
            ):
                continue
            archive.add(
                source,
                arcname=f"serp-saas-cloudshell/{relative.as_posix()}",
                recursive=False,
            )
            count += 1
    print(
        f"Created {destination} ({count} files, {destination.stat().st_size:,} bytes)"
    )


if __name__ == "__main__":
    main()
