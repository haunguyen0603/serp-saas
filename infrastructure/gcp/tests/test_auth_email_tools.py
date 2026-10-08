"""Verify SMTP identity in diagnostics without GCP access or sending mail."""

import importlib.util
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

DIRECTORY = Path(__file__).resolve().parents[1]


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename, DIRECTORY / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuthEmailToolTests(unittest.TestCase):
    def test_diagnostic_passes_identity_in_both_tls_modes(self):
        script = load_script("diagnose-auth-email.py")
        for ssl_mode in (False, True):
            for hostname in ("app.serpsaas.com", "mail.client.example"):
                with self.subTest(ssl_mode=ssl_mode, hostname=hostname):
                    connection = MagicMock()
                    connection.__enter__.return_value = connection
                    connection.ehlo.return_value = (250, b"OK")
                    values = {
                        "AUTH_SMTP_HOST": "smtp.example.com",
                        "AUTH_SMTP_LOCAL_HOSTNAME": hostname,
                        "AUTH_SMTP_PORT": "465" if ssl_mode else "587",
                        "AUTH_SMTP_SSL": str(ssl_mode).lower(),
                        "AUTH_SMTP_STARTTLS": str(not ssl_mode).lower(),
                    }
                    constructor = "SMTP_SSL" if ssl_mode else "SMTP"
                    with (
                        patch.object(
                            script.smtplib, constructor, return_value=connection
                        ) as smtp,
                        redirect_stdout(io.StringIO()),
                    ):
                        self.assertTrue(script.check_smtp(values))
                    self.assertEqual(smtp.call_args.kwargs["local_hostname"], hostname)
                    connection.login.assert_not_called()
                    connection.send_message.assert_not_called()

    def test_cloud_run_probe_uses_identity_and_never_sends_without_recipient(self):
        script = load_script("probe-auth-email-cloudrun.py")
        for ssl_mode in (False, True):
            for hostname in (None, "mail.client.example"):
                with self.subTest(ssl_mode=ssl_mode, hostname=hostname):
                    environment = {
                        "AUTH_SMTP_HOST": "smtp.example.com",
                        "AUTH_SMTP_PORT": "465" if ssl_mode else "587",
                        "AUTH_SMTP_SSL": str(ssl_mode).lower(),
                        "AUTH_SMTP_STARTTLS": str(not ssl_mode).lower(),
                        "AUTH_SMTP_USERNAME": "test-user",
                        "AUTH_SMTP_PASSWORD": "test-password",
                    }
                    if hostname:
                        environment["AUTH_SMTP_LOCAL_HOSTNAME"] = hostname
                    connection = MagicMock()
                    connection.__enter__.return_value = connection
                    output = io.StringIO()
                    with (
                        patch.dict(os.environ, environment, clear=True),
                        patch(
                            "smtplib.SMTP_SSL" if ssl_mode else "smtplib.SMTP",
                            return_value=connection,
                        ) as smtp,
                        redirect_stdout(output),
                    ):
                        # Execute only our checked-in probe with mocked SMTP/env.
                        exec(compile(script.PROBE, "smtp-probe", "exec"), {})  # noqa: S102
                    self.assertEqual(
                        smtp.call_args.kwargs["local_hostname"],
                        hostname or "app.serpsaas.com",
                    )
                    connection.login.assert_called_once_with(
                        "test-user", "test-password"
                    )
                    connection.send_message.assert_not_called()
                    self.assertNotIn("test-password", output.getvalue())
                    self.assertEqual(
                        json.loads(output.getvalue().splitlines()[-1])["outcome"],
                        "passed",
                    )

    def test_cloud_run_job_preserves_explicit_identity_and_secret_reference(self):
        script = load_script("probe-auth-email-cloudrun.py")
        revision = {
            "status": {"imageDigest": "example/backend@sha256:test"},
            "spec": {
                "serviceAccountName": "api@example.iam.gserviceaccount.com",
                "containers": [
                    {
                        "env": [
                            {"name": "AUTH_EMAIL_FROM", "value": "noreply@example.com"},
                            {"name": "AUTH_SMTP_HOST", "value": "smtp.example.com"},
                            {"name": "AUTH_SMTP_USERNAME", "value": "test-user"},
                            {
                                "name": "AUTH_SMTP_LOCAL_HOSTNAME",
                                "value": "mail.client.example",
                            },
                            {
                                "name": "AUTH_SMTP_PASSWORD",
                                "valueFrom": {
                                    "secretKeyRef": {
                                        "name": "smtp-password",
                                        "key": "1",
                                    }
                                },
                            },
                        ]
                    }
                ],
            },
        }
        job = script.make_job(revision, "test-project", "test-region", "test-job", "")
        container = job["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]
        environment = {item["name"]: item for item in container["env"]}
        self.assertEqual(
            environment["AUTH_SMTP_LOCAL_HOSTNAME"]["value"], "mail.client.example"
        )
        self.assertEqual(
            environment["AUTH_SMTP_PASSWORD"]["valueFrom"]["secretKeyRef"],
            {"name": "smtp-password", "key": "1"},
        )
        self.assertNotIn("PROBE_RECIPIENT", environment)

    def test_config_generator_emits_default_and_override_identity(self):
        script = load_script("create-cloud-run-config.py")
        for hostname in (None, "mail.client.example"):
            with self.subTest(hostname=hostname):
                environment = {"PROJECT_NUMBER": "123456789"}
                if hostname:
                    environment["AUTH_SMTP_LOCAL_HOSTNAME"] = hostname
                file = mock_open()
                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch.object(script.sys.stdin, "isatty", return_value=True),
                    patch(
                        "builtins.input",
                        side_effect=[
                            "smtp.example.com",
                            "465",
                            "noreply@example.com",
                            "user",
                        ],
                    ),
                    patch.object(script.os, "open", return_value=3),
                    patch.object(script.os, "fdopen", file),
                    redirect_stdout(io.StringIO()),
                ):
                    script.main()
                config = json.loads(file().write.call_args.args[0])
                self.assertEqual(
                    config["AUTH_SMTP_LOCAL_HOSTNAME"], hostname or "app.serpsaas.com"
                )
                self.assertNotIn("AUTH_SMTP_PASSWORD", config)


if __name__ == "__main__":
    unittest.main()
