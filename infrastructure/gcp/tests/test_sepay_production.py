"""Production configuration, pinned secrets and promotion without cloud access."""

import importlib.util
import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "configure-sepay-production.py"
spec = importlib.util.spec_from_file_location("sepay_production", PATH)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

EXPECTED = {
    "SEPAY_ENABLED": "true",
    "SEPAY_ENV": "production",
    "SEPAY_MERCHANT_ID": "LIVE-MERCHANT",
    "SEPAY_CHECKOUT_URL": "https://pay.sepay.vn/v1/checkout/init",
    "SEPAY_VOID_URL": "https://pgapi.sepay.vn/v1/order/voidTransaction",
    "SEPAY_SANDBOX_ALLOWED_USER_IDS": "[]",
    "SEPAY_PENDING_MINUTES": "45",
    "SEPAY_SUCCESS_URL": "https://app.serpsaas.com/app/change-plan/payment/success",
    "SEPAY_ERROR_URL": "https://app.serpsaas.com/app/change-plan/payment/error",
    "SEPAY_CANCEL_URL": "https://app.serpsaas.com/app/change-plan/payment/cancel",
}


def service(*, production=False, promoted=False):
    env = [
        {"name": "APP_ENV", "value": "production"},
        {
            "name": "JWT_SECRET_KEY",
            "valueFrom": {"secretKeyRef": {"name": "serp-jwt-key", "key": "3"}},
        },
        {
            "name": "DATABASE_URL",
            "valueFrom": {"secretKeyRef": {"name": "serp-database-url", "key": "4"}},
        },
    ]
    if production:
        env += [{"name": key, "value": value} for key, value in EXPECTED.items()]
        env += [
            {
                "name": "SEPAY_SECRET_KEY",
                "valueFrom": {
                    "secretKeyRef": {"name": "serp-sepay-production-key", "key": "7"}
                },
            },
            {
                "name": "SEPAY_IPN_SECRET_KEY",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "serp-sepay-production-ipn-key",
                        "key": "7",
                    }
                },
            },
        ]
    else:
        env += [{"name": "SEPAY_ENV", "value": "sandbox"}]
    revision = "api-production" if production else "api-before"
    return {
        "spec": {
            "template": {
                "spec": {
                    "serviceAccountName": "api@test.iam.gserviceaccount.com",
                    "containers": [{"image": "current-image", "env": env}],
                }
            }
        },
        "status": {
            "latestReadyRevisionName": revision,
            "latestCreatedRevisionName": revision,
            "conditions": [{"type": "Ready", "status": "True"}],
            "traffic": [
                {"revisionName": revision if promoted else "api-before", "percent": 100}
            ],
        },
    }


def revision(current, *, ready=True):
    return {
        "metadata": {
            "name": current["status"]["latestCreatedRevisionName"],
            "labels": {"serving.knative.dev/service": "serp-api"},
        },
        "spec": deepcopy(current["spec"]["template"]["spec"]),
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True" if ready else "False",
                    "reason": "Retired",
                },
                {"type": "Active", "status": "False", "reason": "Retired"},
                {"type": "ContainerReady", "status": "True"},
                {
                    "type": "ResourcesAvailable",
                    "status": "Unknown",
                    "reason": "Retired",
                },
            ]
        },
    }


class ProductionSetupTests(unittest.TestCase):
    def run_main(
        self,
        services,
        *,
        check=False,
        resume=None,
        keys=None,
        cloud_extra=None,
        candidate=None,
    ):
        calls = []
        self.cloud_calls = calls
        descriptions = iter(services)
        current = None

        def cloud(*args, value=None):
            nonlocal current
            calls.append((args, value))
            if args[:3] == ("run", "services", "describe"):
                current = next(descriptions)
                return json.dumps(current)
            if args[:3] == ("run", "revisions", "describe"):
                return json.dumps(candidate or revision(current))
            if cloud_extra:
                return cloud_extra(args)
            if args[:2] == ("secrets", "list"):
                return "[]"
            if args[:3] == ("secrets", "versions", "add"):
                return f"projects/test/secrets/{args[3]}/versions/7"
            return ""

        output = io.StringIO()
        schema = io.BytesIO(
            json.dumps(
                {
                    "paths": {
                        "/api/v1/billing/payments/sepay/checkout": {},
                        "/api/v1/billing/payments/sepay/options": {},
                        "/api/v1/billing/payments/sepay/ipn": {},
                    }
                }
            ).encode()
        )
        with (
            patch.object(
                setup.sys,
                "argv",
                [str(PATH), "--check"]
                if check
                else [str(PATH), "--resume-revision", resume]
                if resume
                else [str(PATH), "--merchant-id", "LIVE-MERCHANT"],
            ),
            patch.object(setup.shutil, "which", return_value="gcloud"),
            patch.object(setup, "urlopen", return_value=schema),
            patch.object(setup, "gcloud", side_effect=cloud),
            patch.object(setup.sys.stdin, "isatty", return_value=True),
            patch.object(
                setup.getpass,
                "getpass",
                side_effect=keys
                or ["synthetic-production-signing", "synthetic-production-ipn"],
            ) as prompt,
            redirect_stdout(output),
        ):
            setup.main()
        return calls, output.getvalue(), prompt

    def test_live_endpoints_and_sandbox_credentials_rejected(self):
        self.assertEqual(setup.nonsecret_config("LIVE-MERCHANT"), EXPECTED)
        for merchant in ("", "SP-TEST-123", "bad|SEPAY_ENV=sandbox"):
            with self.assertRaises(ValueError):
                setup.nonsecret_config(merchant)
        for keys in (
            ["spsk_test_wrong", "independent-ipn"],
            ["same-key", "same-key"],
            ["synthetic-signing", ""],
            ["synthetic-signing", "key\n"],
        ):
            with self.assertRaises(SystemExit):
                self.run_main([service()], keys=keys)

    def test_pinned_production_keys_and_verified_revision_promoted(self):
        calls, output, _ = self.run_main(
            [
                service(),
                service(production=True),
                service(production=True, promoted=True),
            ]
        )
        mutations = [
            args for args, _ in calls if args[:3] == ("run", "services", "update")
        ]
        self.assertEqual(len(mutations), 1)
        update = mutations[0]
        self.assertIn("--no-traffic", update)
        self.assertFalse(
            any(
                arg.startswith(
                    (
                        "--image",
                        "--set-env-vars",
                        "--set-secrets",
                        "--service-account",
                        "--clear",
                    )
                )
                for arg in update
            )
        )
        flag = next(
            arg.removeprefix("--update-env-vars=^|^")
            for arg in update
            if arg.startswith("--update-env-vars=")
        )
        self.assertEqual(dict(part.split("=", 1) for part in flag.split("|")), EXPECTED)
        self.assertIn(
            "--update-secrets=SEPAY_SECRET_KEY=serp-sepay-production-key:7,SEPAY_IPN_SECRET_KEY=serp-sepay-production-ipn-key:7",
            update,
        )
        promotion = next(
            args
            for args, _ in calls
            if args[:3] == ("run", "services", "update-traffic")
        )
        self.assertIn("--to-revisions=api-production=100", promotion)
        self.assertNotIn("--to-latest", promotion)
        for key in ("synthetic-production-signing", "synthetic-production-ipn"):
            self.assertNotIn(key, output)
            self.assertTrue(all(key not in " ".join(args) for args, _ in calls))
        self.assertEqual(
            [value for _, value in calls if value],
            ["synthetic-production-signing", "synthetic-production-ipn"],
        )
        granted = [
            args
            for args, _ in calls
            if args[:2] == ("secrets", "add-iam-policy-binding")
        ]
        self.assertEqual(len(granted), 2)
        self.assertTrue(
            all(
                "--member=serviceAccount:api@test.iam.gserviceaccount.com" in args
                for args in granted
            )
        )
        self.assertTrue(
            all("--role=roles/secretmanager.secretAccessor" in args for args in granted)
        )
        report = json.loads(output)
        self.assertEqual(report["environment"], "production")
        self.assertEqual(report["ready_revision"], "api-production")
        self.assertEqual(report["previous_revision"], "api-before")
        self.assertTrue(report["verified"])

    def test_check_is_read_only_and_never_prompts(self):
        calls, output, prompt = self.run_main(
            [service(production=True, promoted=True)], check=True
        )
        self.assertEqual(
            [args[:3] for args, _ in calls],
            [("run", "services", "describe"), ("run", "revisions", "describe")],
        )
        prompt.assert_not_called()
        self.assertTrue(json.loads(output)["verified"])

    def test_mismatched_configuration_rejected(self):
        for mutation in ("secret", "endpoint"):
            staged = service(production=True)
            if mutation == "secret":
                staged["spec"]["template"]["spec"]["containers"][0]["env"][-1][
                    "valueFrom"
                ]["secretKeyRef"]["name"] = "serp-sepay-sandbox-ipn-key"
            else:
                env = staged["spec"]["template"]["spec"]["containers"][0]["env"]
                next(e for e in env if e["name"] == "SEPAY_CHECKOUT_URL")["value"] = (
                    "https://pay-sandbox.sepay.vn/v1/checkout/init"
                )
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                setup.verify_configuration(staged, EXPECTED)

    def test_ready_retired_candidate_promoted_despite_old_latest_ready(self):
        staged = service(production=True)
        staged["status"]["latestReadyRevisionName"] = "api-before"
        calls, output, _ = self.run_main(
            [service(), staged, service(production=True, promoted=True)]
        )
        self.assertTrue(json.loads(output)["verified"])
        self.assertTrue(
            any(args[:3] == ("run", "services", "update-traffic") for args, _ in calls)
        )

    def test_unready_candidate_not_promoted_despite_ready_service(self):
        current = service(production=True)
        with self.assertRaisesRegex(RuntimeError, "own Ready condition"):
            self.run_main(
                [service(), current], candidate=revision(current, ready=False)
            )
        self.assertFalse(
            any(
                args[:3] == ("run", "services", "update-traffic")
                for args, _ in self.cloud_calls
            )
        )

    def test_candidate_snapshot_and_requested_revision_must_match(self):
        current = service(production=True)
        for mutation in ("owner", "identity", "pin", "endpoint", "metadata"):
            artifact = revision(current)
            if mutation == "owner":
                artifact["metadata"]["labels"]["serving.knative.dev/service"] = "other"
            elif mutation == "metadata":
                artifact["metadata"]["name"] = "other"
            elif mutation == "identity":
                artifact["spec"]["serviceAccountName"] = (
                    "other@test.iam.gserviceaccount.com"
                )
            elif mutation == "pin":
                artifact["spec"]["containers"][0]["env"][-1]["valueFrom"][
                    "secretKeyRef"
                ]["key"] = "8"
            else:
                env = artifact["spec"]["containers"][0]["env"]
                next(e for e in env if e["name"] == "SEPAY_CHECKOUT_URL")["value"] = (
                    "https://wrong.example"
                )
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.run_main([current], resume="api-production", candidate=artifact)
            self.assertFalse(
                any(
                    args[:3] == ("run", "services", "update-traffic")
                    for args, _ in self.cloud_calls
                )
            )
        with self.assertRaisesRegex(RuntimeError, "candidate changed"):
            self.run_main([current], resume="api-older")

    def test_resume_uses_existing_secrets_without_prompts_or_service_update(self):
        staged = service(production=True)
        staged["status"]["latestReadyRevisionName"] = "api-before"
        calls, output, prompt = self.run_main(
            [staged, service(production=True, promoted=True)], resume="api-production"
        )
        prompt.assert_not_called()
        self.assertEqual(
            [args[:3] for args, _ in calls],
            [
                ("run", "services", "describe"),
                ("run", "revisions", "describe"),
                ("run", "services", "update-traffic"),
                ("run", "services", "describe"),
                ("run", "revisions", "describe"),
            ],
        )
        self.assertTrue(all(value is None for _, value in calls))
        self.assertTrue(json.loads(output)["resumed"])
        self.assertTrue(json.loads(output)["verified"])

    def test_no_promotion_after_staged_validation_failure(self):
        staged = service(production=True)
        staged["spec"]["template"]["spec"]["containers"][0]["image"] = (
            "concurrent-deployment"
        )
        with self.assertRaises(RuntimeError):
            self.run_main([service(), staged])
        self.assertFalse(
            any(
                args[:3] == ("run", "services", "update-traffic")
                for args, _ in self.cloud_calls
            )
        )

    def test_traffic_must_reach_the_verified_revision(self):
        with self.assertRaises(RuntimeError):
            setup.verify_traffic(service(production=True), "api-production")
        setup.verify_traffic(service(production=True, promoted=True), "api-production")

    def test_subprocess_error_never_prints_key_output(self):
        failed = subprocess.CompletedProcess(
            [], 1, stdout="synthetic-sensitive", stderr="synthetic-sensitive"
        )
        with (
            patch.object(setup.subprocess, "run", return_value=failed),
            self.assertRaises(RuntimeError) as caught,
        ):
            setup.gcloud(
                "run",
                "services",
                "update",
                "api",
                "--update-env-vars=TEST=synthetic-sensitive",
            )
        self.assertNotIn("synthetic-sensitive", str(caught.exception))

    def test_no_cloud_mutation_when_preflight_fails(self):
        with (
            patch.object(setup, "urlopen", return_value=io.BytesIO(b'{"paths": {}}')),
            patch.object(setup, "gcloud") as cloud,
            patch.object(setup.shutil, "which", return_value="gcloud"),
            patch.object(
                setup.sys, "argv", [str(PATH), "--merchant-id", "LIVE-MERCHANT"]
            ),
            patch.object(setup.getpass, "getpass") as prompt,
        ):
            with self.assertRaises(RuntimeError):
                setup.main()
            cloud.assert_not_called()
            prompt.assert_not_called()

    def test_command_failure_reports_code_without_echoing_cloud_output(self):
        failed = subprocess.CompletedProcess(
            [],
            1,
            stdout="synthetic-signing-value",
            stderr="PERMISSION_DENIED: input=synthetic-signing-value",
        )
        with (
            patch.object(setup.subprocess, "run", return_value=failed),
            self.assertRaises(setup.SetupError) as caught,
        ):
            setup.gcloud(
                "secrets", "versions", "add", "key", value="synthetic-signing-value"
            )
        message = str(caught.exception)
        self.assertIn("secrets versions add", message)
        self.assertIn("PERMISSION_DENIED", message)
        self.assertNotIn("synthetic-signing-value", message)

    def test_failure_handler_reports_stage_and_controlled_error_only(self):
        def fail():
            setup.stage("verify_staged_production_revision")
            raise setup.SetupError(
                "Expected a pinned Production secret: SEPAY_IPN_SECRET_KEY"
            )

        with (
            patch.object(setup, "main", side_effect=fail),
            self.assertRaises(SystemExit) as caught,
        ):
            setup.run()
        self.assertIn("verify_staged_production_revision", str(caught.exception))
        self.assertIn("SEPAY_IPN_SECRET_KEY", str(caught.exception))
        with (
            patch.object(
                setup, "main", side_effect=ValueError("synthetic-private-value")
            ),
            self.assertRaises(SystemExit) as caught,
        ):
            setup.run()
        self.assertNotIn("synthetic-private-value", str(caught.exception))

    def test_diagnosis_only_reads_metadata_and_filters_sensitive_fields(self):
        current = service(production=True)
        current["status"]["latestReadyRevisionName"] = "api-before"
        current["status"]["conditions"][0] = {
            "type": "Ready",
            "status": "False",
            "message": "synthetic-private-signing-value",
        }
        env = current["spec"]["template"]["spec"]["containers"][0]["env"]
        next(e for e in env if e["name"] == "SEPAY_IPN_SECRET_KEY").clear()
        env[-1].update(
            {"name": "SEPAY_IPN_SECRET_KEY", "value": "synthetic-private-ipn-value"}
        )
        calls = []

        def cloud(*args, value=None):
            calls.append((args, value))
            if args[:3] == ("run", "services", "describe"):
                return json.dumps(current)
            if args[:2] == ("secrets", "list"):
                return json.dumps(
                    [
                        {"name": f"projects/test/secrets/{name}"}
                        for name in setup.SECRETS.values()
                    ]
                )
            if args[:3] == ("secrets", "versions", "list"):
                return json.dumps(
                    [
                        {
                            "name": f"projects/test/secrets/{args[3]}/versions/7",
                            "state": "ENABLED",
                        }
                    ]
                )
            raise AssertionError(f"Unexpected cloud operation: {args[:3]}")

        output = io.StringIO()
        with (
            patch.object(setup.sys, "argv", [str(PATH), "--diagnose"]),
            patch.object(setup.shutil, "which", return_value="gcloud"),
            patch.object(setup, "gcloud", side_effect=cloud),
            patch.object(setup.getpass, "getpass") as prompt,
            patch.object(setup, "urlopen") as network,
            redirect_stdout(output),
        ):
            setup.main()
        prompt.assert_not_called()
        network.assert_not_called()
        text = output.getvalue()
        self.assertNotIn("synthetic-private", text)
        report = json.loads(text)
        self.assertEqual(report["mode"], "read_only_diagnosis")
        self.assertEqual(report["latest_ready_revision"], "api-before")
        self.assertEqual(report["latest_created_revision"], "api-production")
        self.assertEqual(
            report["secret_bindings"]["SEPAY_IPN_SECRET_KEY"]["type"], "literal_value"
        )
        self.assertEqual(
            report["production_secret_versions"]["serp-sepay-production-key"][
                "versions"
            ],
            [{"version": "7", "state": "ENABLED"}],
        )
        self.assertTrue(all(value is None for _, value in calls))

    def test_environment_type_conflict_is_reported_without_raw_env_values(self):
        message = (
            "Cannot update environment variable synthetic-private-value "
            "because it has already been set with a different type."
        )
        self.assertEqual(
            setup.cloud_error_code(message), "ENVIRONMENT_VARIABLE_TYPE_CONFLICT"
        )


if __name__ == "__main__":
    unittest.main()
