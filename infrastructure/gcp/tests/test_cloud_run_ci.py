"""Verify release failure boundaries without accessing a GCP project.

Run: python3 -m unittest discover -s infrastructure/gcp/tests -v
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAKE_CLI = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
tool = Path(sys.argv[0]).name
with open(os.environ["FAKE_LOG"], "a") as stream:
    stream.write(json.dumps([tool, args]) + "\\n")
if tool == "curl":
    sys.exit(int(os.environ.get("FAIL_SMOKE", "0")))
if args[:2] == ["storage", "cp"]:
    sys.exit(int(os.environ.get("FAIL_LOCK", "0")))
if args[:3] == ["storage", "objects", "describe"]:
    print("12345")
elif args[:3] == ["run", "jobs", "execute"]:
    sys.exit(int(os.environ.get("FAIL_MIGRATION", "0")))
elif args[:3] == ["run", "services", "describe"]:
    if "--format=value(spec.template.spec.serviceAccountName)" in args:
        print(args[3] + "@serp-saas.iam.gserviceaccount.com")
    elif "--format=value(status.url)" in args:
        print("https://api.example.com")
    else:
        print(args[3])
elif args[:3] == ["run", "jobs", "describe"]:
    print("serp-migrations@serp-saas.iam.gserviceaccount.com")
elif args[:3] == ["builds", "triggers", "list"]:
    print(os.environ.get("EXISTING_TRIGGERS", ""))
elif args[:3] == ["alpha", "builds", "triggers"]:
    print("trigger-id-123")
"""


class CloudRunCITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        self.log = directory / "calls.jsonl"
        for name in ("gcloud", "curl"):
            executable = directory / name
            executable.write_text(FAKE_CLI, newline="\n")
            executable.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{directory}{os.pathsep}{os.environ['PATH']}",
            "FAKE_LOG": str(self.log),
            "GCP_PROJECT_ID": "serp-saas",
            "GCP_LOCATION": "asia-southeast1",
            "RELEASE_IMAGE": (
                "asia-southeast1-docker.pkg.dev/serp-saas/serp-saas/backend:test-build"
            ),
            "RELEASE_BUILD_ID": "test-build",
            "RELEASE_LOCK_BUCKET": "serp-saas-ci-locks",
            "RELEASE_SITE_URL": "https://www.example.com",
            "RELEASE_APP_URL": "https://app.example.com",
            "FRONTEND_ORIGIN": "https://www.example.com",
            "FRONTEND_APP_ORIGIN": "https://app.example.com",
            "FRONTEND_API_URL": "https://api.example.com",
            "GIT_REPOSITORY_LINK": (
                "projects/serp-saas/locations/asia-southeast1/connections/github/"
                "gitRepositoryLinks/serp-saas"
            ),
        }

    def run_script(self, script, action, **overrides):
        return subprocess.run(
            ["sh", str(ROOT / "infrastructure/gcp" / script), action],
            env={**self.env, **overrides},
            capture_output=True,
            text=True,
            check=False,
        )

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def updates(self):
        return [
            args
            for tool, args in self.calls()
            if tool == "gcloud" and args[:3] == ["run", "services", "update"]
        ]

    def test_backend_waits_for_migration_before_updating_both_services(self):
        result = self.run_script("cloud-run-release.sh", "backend")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = [args for _, args in self.calls()]
        execute = next(a for a in args if a[:3] == ["run", "jobs", "execute"])
        self.assertIn("--wait", execute)
        self.assertEqual([a[3] for a in self.updates()], ["serp-worker", "serp-api"])
        self.assertLess(args.index(execute), args.index(self.updates()[0]))
        for update in self.updates():
            self.assertIn("--image=" + self.env["RELEASE_IMAGE"], update)
            self.assertFalse(
                any("secrets" in arg or "env-vars" in arg for arg in update)
            )
        self.assertIn("--if-generation-match=0", args[0])
        self.assertEqual(args[-1][:2], ["storage", "rm"])
        self.assertIn("--if-generation-match=12345", args[-1])

    def test_failed_migration_preserves_services_and_releases_lock(self):
        result = self.run_script("cloud-run-release.sh", "backend", FAIL_MIGRATION="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.updates(), [])
        self.assertEqual(self.calls()[-1][1][:2], ["storage", "rm"])

    def test_failed_lock_never_mutates_resources_or_deletes_other_lock(self):
        result = self.run_script("cloud-run-release.sh", "backend", FAIL_LOCK="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls()), 1)
        self.assertIn("Release lock unavailable", result.stderr)

    def test_frontend_checks_both_origins(self):
        result = self.run_script("cloud-run-release.sh", "frontend")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[3] for a in self.updates()], ["serp-web"])
        urls = [args[-1] for tool, args in self.calls() if tool == "curl"]
        self.assertEqual(
            urls, ["https://www.example.com/", "https://app.example.com/login"]
        )

    def test_failed_smoke_reports_failure_and_releases_lock(self):
        result = self.run_script("cloud-run-release.sh", "frontend", FAIL_SMOKE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls()[-1][1][:2], ["storage", "rm"])

    def test_trigger_creation_uses_main_yaml_paths_and_build_time_urls(self):
        result = self.run_script("cloud-run-ci.sh", "triggers")
        self.assertEqual(result.returncode, 0, result.stderr)
        triggers = [
            a for _, a in self.calls() if a[:3] == ["alpha", "builds", "triggers"]
        ]
        self.assertEqual(len(triggers), 2)
        for trigger in triggers:
            self.assertEqual(trigger[3:5], ["create", "developer-connect"])
            self.assertIn("--branch-pattern=^main$", trigger)
            self.assertTrue(any(a.startswith("--included-files=") for a in trigger))
        self.assertIn(
            "--build-config=infrastructure/gcp/cloudbuild-frontend-cd.yaml", triggers[0]
        )
        substitution = next(a for a in triggers[0] if a.startswith("--substitutions="))
        self.assertIn("_APP_URL=https://app.example.com", substitution)
        self.assertIn("_API_URL=https://api.example.com", substitution)
        self.assertEqual(
            [a[3] for a in self.updates()], ["serp-web", "serp-api", "serp-worker"]
        )

    def test_existing_triggers_are_updated_instead_of_duplicated(self):
        result = self.run_script(
            "cloud-run-ci.sh",
            "triggers",
            EXISTING_TRIGGERS="serp-web-main\nserp-backend-main",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        triggers = [
            a for _, a in self.calls() if a[:3] == ["alpha", "builds", "triggers"]
        ]
        for trigger in triggers:
            self.assertEqual(trigger[3:5], ["update", "developer-connect"])
            self.assertTrue(
                any(a.startswith("--update-substitutions=") for a in trigger)
            )

    def test_invalid_origins_fail_before_trigger_mutations(self):
        result = self.run_script(
            "cloud-run-ci.sh", "triggers", FRONTEND_ORIGIN="https://example.com/"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_connection_region_is_used_for_triggers_and_deploy_region_is_preserved(
        self,
    ):
        link = (
            "projects/serp-saas/locations/europe-west1/connections/connection-example/"
            "gitRepositoryLinks/haunguyen0603-serp-saas"
        )
        result = self.run_script(
            "cloud-run-ci.sh", "triggers", GIT_REPOSITORY_LINK=link
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [args for _, args in self.calls()]
        trigger_calls = [
            args
            for args in calls
            if args[:3] == ["alpha", "builds", "triggers"]
            or args[:3] == ["builds", "triggers", "list"]
        ]
        self.assertEqual(len(trigger_calls), 3)
        for args in trigger_calls:
            self.assertIn("--region=europe-west1", args)
        for args in trigger_calls[1:]:
            substitutions = next(
                arg for arg in args if arg.startswith("--substitutions=")
            )
            self.assertIn("_REGION=asia-southeast1", substitutions)
        for update in self.updates():
            self.assertIn("--region=asia-southeast1", update)

    def test_clone_url_appended_to_resource_fails_before_gcloud_calls(self):
        result = self.run_script(
            "cloud-run-ci.sh",
            "triggers",
            GIT_REPOSITORY_LINK=(
                "projects/serp-saas/locations/asia-southeast1/connections/github/"
                "gitRepositoryLinks/https://europe-west1-git.developerconnect.dev/"
                "833917440392/connection-example/haunguyen0603-serp-saas"
            ),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])
        self.assertIn("not a GitHub/clone/proxy URL", result.stderr)

    def test_prepare_scopes_deploy_permissions_and_uses_actual_runtime_identities(self):
        result = self.run_script("cloud-run-ci.sh", "prepare")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = [a for _, a in self.calls()]
        project_roles = [
            a for a in args if a[:2] == ["projects", "add-iam-policy-binding"]
        ]
        self.assertFalse(any("--role=roles/run.admin" in a for a in args))
        self.assertFalse(any("--role=roles/run.developer" in a for a in project_roles))
        self.assertFalse(
            any("--role=roles/secretmanager.secretAccessor" in a for a in args)
        )
        identities = [
            a[3]
            for a in args
            if a[:3] == ["iam", "service-accounts", "add-iam-policy-binding"]
        ]
        self.assertEqual(
            set(identities),
            {
                "serp-web@serp-saas.iam.gserviceaccount.com",
                "serp-api@serp-saas.iam.gserviceaccount.com",
                "serp-worker@serp-saas.iam.gserviceaccount.com",
                "serp-migrations@serp-saas.iam.gserviceaccount.com",
            },
        )


if __name__ == "__main__":
    unittest.main()
