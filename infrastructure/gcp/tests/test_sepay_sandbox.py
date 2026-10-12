"""Sandbox setup security and partial Cloud Run updates, without cloud access."""

import importlib.util
import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "configure-sepay-sandbox.py"
spec = importlib.util.spec_from_file_location("sepay_setup", PATH)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SandboxSetupTests(unittest.TestCase):
    def test_only_sandbox_and_actual_app_callback_routes(self):
        config = setup.nonsecret_config({}, "TEST-MERCHANT")
        self.assertEqual(config["SEPAY_ENV"], "sandbox")
        self.assertEqual(config["SEPAY_CHECKOUT_URL"], setup.CHECKOUT_URL)
        for override in (
            {"SEPAY_ENV": "production"},
            {"SEPAY_CHECKOUT_URL": "https://pay.sepay.vn/v1/checkout/init"},
            {"SEPAY_SUCCESS_URL": "https://app.serpsaas.com/unrelated"},
        ):
            with self.assertRaises(ValueError):
                setup.nonsecret_config(override, "TEST-MERCHANT")

    def test_secret_is_only_piped_to_version_creation(self):
        calls = []

        def cloud(*args, value=None):
            calls.append((args, value))
            if args[:2] == ("secrets", "list"):
                return "[]"
            if args[:3] == ("secrets", "versions", "add"):
                return "projects/test/secrets/key/versions/7"
            return ""

        with patch.object(setup, "gcloud", side_effect=cloud):
            version = setup.add_secret(
                "test-project",
                "sandbox-key",
                "synthetic-secret",
                "api@test.iam.gserviceaccount.com",
            )
        self.assertEqual(version, "7")
        self.assertTrue(
            all("synthetic-secret" not in " ".join(args) for args, _ in calls)
        )
        self.assertEqual([value for _, value in calls if value], ["synthetic-secret"])
        self.assertTrue(
            any(
                "--role=roles/secretmanager.secretAccessor" in args for args, _ in calls
            )
        )

    def test_failed_gcloud_never_exposes_environment_or_stderr(self):
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="sensitive-value")
        with (
            patch.object(setup.subprocess, "run", return_value=failed),
            self.assertRaises(RuntimeError) as caught,
        ):
            setup.gcloud("run", "services", "update", "api", value="sensitive-value")
        self.assertNotIn("sensitive-value", str(caught.exception))

    def test_update_preserves_image_and_existing_configuration(self):
        cloud_calls = []
        configured = setup.nonsecret_config({}, "TEST-MERCHANT")
        configured["SEPAY_SANDBOX_ALLOWED_USER_IDS"] = "[]"
        before = {
            "spec": {
                "template": {
                    "spec": {
                        "serviceAccountName": "api@test.iam.gserviceaccount.com",
                        "containers": [{"image": "current-image"}],
                    }
                }
            },
            "status": {"latestReadyRevisionName": "api-before"},
        }
        env = [{"name": key, "value": value} for key, value in configured.items()]
        env += [
            {"name": key, "valueFrom": {"secretKeyRef": {"name": name, "key": "7"}}}
            for key, name in setup.SECRETS.items()
        ]
        after = {
            "spec": {
                "template": {
                    "spec": {"containers": [{"image": "current-image", "env": env}]}
                }
            },
            "status": {"latestReadyRevisionName": "api-after"},
        }

        def cloud(*args, value=None):
            cloud_calls.append(args)
            if args[:3] == ("run", "services", "describe"):
                return json.dumps(before if len(cloud_calls) == 1 else after)
            return ""

        response = io.BytesIO(
            json.dumps({"paths": {"/api/v1/billing/payments/sepay/ipn": {}}}).encode()
        )
        output = io.StringIO()
        with (
            patch.object(
                setup.sys, "argv", [str(PATH), "--merchant-id", "TEST-MERCHANT"]
            ),
            patch.object(setup.shutil, "which", return_value="gcloud"),
            patch.object(setup, "urlopen", return_value=response),
            patch.object(setup, "gcloud", side_effect=cloud),
            patch.object(setup.sys.stdin, "isatty", return_value=True),
            patch.object(
                setup.getpass,
                "getpass",
                side_effect=["synthetic-signing", "synthetic-ipn"],
            ),
            patch.object(setup, "add_secret", return_value="7"),
            redirect_stdout(output),
        ):
            setup.main()
        update = next(
            args for args in cloud_calls if args[:3] == ("run", "services", "update")
        )
        self.assertTrue(any(arg.startswith("--update-env-vars=") for arg in update))
        self.assertTrue(any(arg.startswith("--update-secrets=") for arg in update))
        self.assertFalse(
            any(
                arg.startswith(("--image", "--set-env-vars", "--set-secrets"))
                for arg in update
            )
        )
        self.assertNotIn("synthetic-signing", output.getvalue())
        self.assertNotIn("synthetic-ipn", output.getvalue())
        self.assertIn("api-after", output.getvalue())


if __name__ == "__main__":
    unittest.main()
