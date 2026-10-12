"""Production configuration, pinned secrets and promotion without cloud access."""

import importlib.util
import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
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


class ProductionSetupTests(unittest.TestCase):
    def run_main(self, services, *, check=False, keys=None, cloud_extra=None):
        calls = []
        self.cloud_calls = calls
        descriptions = iter(services)

        def cloud(*args, value=None):
            calls.append((args, value))
            if args[:3] == ("run", "services", "describe"):
                return json.dumps(next(descriptions))
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
            [args[:3] for args, _ in calls], [("run", "services", "describe")]
        )
        prompt.assert_not_called()
        self.assertTrue(json.loads(output)["verified"])

    def test_mismatched_secret_and_unready_revision_rejected(self):
        for mutation in ("secret", "not_ready", "condition", "endpoint"):
            staged = service(production=True)
            if mutation == "secret":
                staged["spec"]["template"]["spec"]["containers"][0]["env"][-1][
                    "valueFrom"
                ]["secretKeyRef"]["name"] = "serp-sepay-sandbox-ipn-key"
            elif mutation == "not_ready":
                staged["status"]["latestReadyRevisionName"] = "api-before"
            elif mutation == "condition":
                staged["status"]["conditions"][0]["status"] = "False"
            else:
                env = staged["spec"]["template"]["spec"]["containers"][0]["env"]
                next(e for e in env if e["name"] == "SEPAY_CHECKOUT_URL")["value"] = (
                    "https://pay-sandbox.sepay.vn/v1/checkout/init"
                )
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                setup.verify(staged, EXPECTED)

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


if __name__ == "__main__":
    unittest.main()
