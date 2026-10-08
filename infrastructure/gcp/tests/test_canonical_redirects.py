import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "canonical", Path(__file__).resolve().parents[1] / "canonical-redirects.py"
)
canonical = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canonical)


class CanonicalRedirectTests(unittest.TestCase):
    def test_public_dns_verification_does_not_pin_the_load_balancer_ip(self):
        result = subprocess.CompletedProcess(
            [], 0, stdout="HTTP/2 301\nLocation: https://serpsaas.com/\n\n", stderr=""
        )
        with patch.object(canonical.subprocess, "run", return_value=result):
            row = canonical.check(
                "https://www.serpsaas.com/",
                expected_status=301,
                expected_location="https://serpsaas.com/",
                doh_url="https://dns.google/dns-query",
            )
        self.assertTrue(row["passed"])
        self.assertIn("--doh-url", row["command"])
        self.assertIn("https://dns.google/dns-query", row["command"])
        self.assertNotIn("--resolve", row["command"])
        self.assertNotIn("--insecure", row["command"])
        self.assertNotIn("--doh-insecure", row["command"])

    def test_default_https_port_passes_and_raw_location_is_recorded(self):
        location = "https://serpsaas.com:443/pricing?next=%2Fapp%3Fx%3D1&tag=a&tag=b"
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout=f"HTTP/1.1 301 Moved Permanently\nLocation: {location}\n\n",
            stderr="",
        )
        with patch.object(canonical.subprocess, "run", return_value=result):
            row = canonical.check(
                "http://serpsaas.com/pricing?next=%2Fapp%3Fx%3D1&tag=a&tag=b",
                expected_status=301,
                expected_location="https://serpsaas.com/pricing?next=%2Fapp%3Fx%3D1&tag=a&tag=b",
            )
        self.assertTrue(row["passed"])
        self.assertEqual(row["location"], location)
        self.assertEqual(row["normalized_location"], row["expected_location"])

    def test_port_normalization_does_not_accept_wrong_host_port_path_or_query(self):
        for location in (
            "https://serpsaas.com:8443/pricing?tag=a&tag=b",
            "https://www.serpsaas.com:443/pricing?tag=a&tag=b",
            "https://serpsaas.com:443@evil.test/pricing?tag=a&tag=b",
            "https://serpsaas.com:443/pricing?tag=b&tag=a",
            "https://serpsaas.com:443/about?tag=a&tag=b",
            "http://serpsaas.com:443/pricing?tag=a&tag=b",
        ):
            result = subprocess.CompletedProcess(
                [],
                0,
                stdout=f"HTTP/1.1 301 Moved Permanently\nLocation: {location}\n\n",
                stderr="",
            )
            with (
                self.subTest(location=location),
                patch.object(canonical.subprocess, "run", return_value=result),
            ):
                row = canonical.check(
                    "http://serpsaas.com/pricing?tag=a&tag=b",
                    expected_status=301,
                    expected_location="https://serpsaas.com/pricing?tag=a&tag=b",
                )
                self.assertFalse(row["passed"])

    def test_final_canonical_destination_accepts_only_the_default_port(self):
        for final, expected_pass in (
            ("https://serpsaas.com:443/", True),
            ("https://serpsaas.com/", True),
            ("https://www.serpsaas.com/", False),
            ("https://serpsaas.com:8443/", False),
            ("https://serpsaas.com/?source=added", False),
        ):
            result = subprocess.CompletedProcess(
                [], 0, stdout=f"HTTP/2 200\n\nFINAL_URL={final}\n", stderr=""
            )
            with (
                self.subTest(final=final),
                patch.object(canonical.subprocess, "run", return_value=result),
            ):
                row = canonical.check(
                    "http://serpsaas.com/", expected_status=200, follow=True
                )
                self.assertEqual(row["passed"], expected_pass)

    def test_cloud_shell_placeholder_stops_before_credentials_or_infrastructure(self):
        with (
            patch.object(
                canonical,
                "command",
                return_value="Follow the instructions to install terraform",
            ) as cmd,
            patch.object(canonical, "terraform") as tf,
            patch.object(canonical, "gcloud") as gc,
        ):
            with self.assertRaisesRegex(RuntimeError, "Cloud Shell placeholder"):
                canonical.infrastructure("prepare", "prepare")
            cmd.assert_called_once_with(["terraform", "version", "-json"], capture=True)
            tf.assert_not_called()
            gc.assert_not_called()

    def test_missing_terraform_has_installation_guidance(self):
        with (
            patch.object(
                canonical, "command", side_effect=FileNotFoundError("terraform")
            ),
            self.assertRaisesRegex(RuntimeError, "Install the real Terraform CLI"),
        ):
            canonical.require_terraform()

    def test_real_supported_version_passes_and_unsupported_versions_fail(self):
        with patch.object(
            canonical,
            "command",
            return_value=json.dumps({"terraform_version": "1.13.5"}),
        ):
            canonical.require_terraform()
        for version in ("1.6.6", "2.0.0", "", "not-a-version"):
            with (
                self.subTest(version=version),
                patch.object(
                    canonical,
                    "command",
                    return_value=json.dumps({"terraform_version": version}),
                ),
                self.assertRaisesRegex(RuntimeError, "Unsupported Terraform version"),
            ):
                canonical.require_terraform()

    def test_proxy_connect_header_cannot_hide_a_temporary_redirect(self):
        raw = "HTTP/1.1 200 Connection established\r\n\r\nHTTP/2 302\r\nLocation: https://serpsaas.com/pricing\r\n\r\n"
        result = subprocess.CompletedProcess([], 0, stdout=raw, stderr="")
        with patch.object(canonical.subprocess, "run", return_value=result):
            row = canonical.check(
                "http://serpsaas.com/pricing",
                expected_status=301,
                expected_location="https://serpsaas.com/pricing",
            )
        self.assertEqual(row["status"], 302)
        self.assertFalse(row["passed"])

    def test_correct_code_but_lost_or_changed_query_fails(self):
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout="HTTP/1.1 301 Moved Permanently\nLocation: https://serpsaas.com/pricing\n\n",
            stderr="",
        )
        with patch.object(canonical.subprocess, "run", return_value=result):
            row = canonical.check(
                "http://serpsaas.com/pricing?tag=a&tag=b",
                expected_status=301,
                expected_location="https://serpsaas.com/pricing?tag=a&tag=b",
            )
        self.assertFalse(row["passed"])

    def test_valid_permanent_redirect_and_preflight_uses_original_host_with_tls(self):
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout="HTTP/2 301\nlocation: https://serpsaas.com/pricing?tag=a&tag=b\n\n",
            stderr="",
        )
        with patch.object(canonical.subprocess, "run", return_value=result):
            row = canonical.check(
                "https://www.serpsaas.com/pricing?tag=a&tag=b",
                expected_status=301,
                expected_location="https://serpsaas.com/pricing?tag=a&tag=b",
                ip="203.0.113.10",
            )
        self.assertTrue(row["passed"])
        self.assertIn("www.serpsaas.com:443:203.0.113.10", row["command"])
        self.assertIn("--noproxy", row["command"])
        self.assertNotIn("--insecure", row["command"])

    def test_dns_failure_is_not_an_http_status(self):
        result = subprocess.CompletedProcess(
            [], 6, stdout="", stderr="Could not resolve host"
        )
        with patch.object(canonical.subprocess, "run", return_value=result):
            row = canonical.check("http://www.serpsaas.com/", expected_status=301)
        self.assertFalse(row["passed"])
        self.assertEqual(row["status"], 0)
        self.assertEqual(row["exit_code"], 6)

    def test_deploy_waits_for_certificate(self):
        with (
            patch.object(canonical, "require_terraform"),
            patch.object(
                canonical,
                "gcloud",
                return_value=json.dumps({"managed": {"state": "PROVISIONING"}}),
            ),
            patch.object(canonical, "terraform") as terraform,
        ):
            with self.assertRaisesRegex(RuntimeError, "not ACTIVE"):
                canonical.infrastructure("deploy", "deploy")
            terraform.assert_not_called()

    def test_deploy_also_waits_for_each_map_entry(self):
        responses = [
            json.dumps({"managed": {"state": "ACTIVE"}}),
            json.dumps({"state": "ACTIVE"}),
            json.dumps({"state": "PENDING"}),
        ]
        with (
            patch.object(canonical, "require_terraform"),
            patch.object(canonical, "gcloud", side_effect=responses),
            patch.object(canonical, "terraform") as terraform,
        ):
            with self.assertRaisesRegex(RuntimeError, "www is not ACTIVE"):
                canonical.infrastructure("deploy", "prepare")
            terraform.assert_not_called()

    def test_prepare_cannot_disable_an_existing_load_balancer(self):
        def terraform(args, **kwargs):
            return (
                json.dumps(
                    {
                        "values": {
                            "root_module": {
                                "resources": [
                                    {"type": "google_compute_global_forwarding_rule"}
                                ]
                            }
                        }
                    }
                )
                if args == ["show", "-json"]
                else ""
            )

        with (
            patch.object(canonical, "require_terraform"),
            patch.object(canonical, "command", return_value="token"),
            patch.object(canonical, "terraform", side_effect=terraform) as tf,
        ):
            with self.assertRaisesRegex(RuntimeError, "already deployed"):
                canonical.infrastructure("prepare", "deploy")
            self.assertFalse(
                any(call.args[0][0] in {"plan", "apply"} for call in tf.call_args_list)
            )

    def test_plan_replacements_are_never_applied(self):
        def terraform(args, **kwargs):
            if args == ["show", "-json"]:
                return json.dumps({"format_version": "1.0"})
            if args[0] == "show":
                return json.dumps(
                    {
                        "resource_changes": [
                            {
                                "address": "google_compute_global_address.web",
                                "change": {"actions": ["delete", "create"]},
                            }
                        ]
                    }
                )
            return ""

        with (
            patch.object(canonical, "require_terraform"),
            patch.object(canonical, "command", return_value="token"),
            patch.object(canonical, "terraform", side_effect=terraform) as tf,
        ):
            with self.assertRaisesRegex(RuntimeError, "Refusing deletions"):
                canonical.infrastructure("prepare", "prepare")
            self.assertFalse(
                any(call.args[0][0] == "apply" for call in tf.call_args_list)
            )

    def test_non_json_plan_output_does_not_apply(self):
        def terraform(args, **kwargs):
            if args == ["show", "-json"]:
                return json.dumps({"format_version": "1.0"})
            return (
                "Follow the instructions to install terraform"
                if args[0] == "show"
                else ""
            )

        with (
            patch.object(canonical, "require_terraform"),
            patch.object(canonical, "command", return_value="token"),
            patch.object(canonical, "terraform", side_effect=terraform) as tf,
        ):
            with self.assertRaisesRegex(RuntimeError, "no apply was attempted"):
                canonical.infrastructure("prepare", "prepare")
            self.assertFalse(
                any(call.args[0][0] == "apply" for call in tf.call_args_list)
            )

    def test_first_prepare_without_state_reaches_apply(self):
        def terraform(args, **kwargs):
            if args == ["show", "-json"]:
                return json.dumps({"format_version": "1.0"})
            if args[0] == "show":
                return json.dumps(
                    {
                        "resource_changes": [
                            {
                                "address": "google_compute_global_address.web",
                                "change": {"actions": ["create"]},
                            }
                        ]
                    }
                )
            return ""

        with (
            patch.object(canonical, "require_terraform"),
            patch.object(canonical, "command", return_value="token"),
            patch.object(canonical, "terraform", side_effect=terraform) as tf,
        ):
            canonical.infrastructure("prepare", "prepare")
            self.assertTrue(
                any(call.args[0][0] == "apply" for call in tf.call_args_list)
            )
            self.assertFalse(
                any(call.args[0][0] == "state" for call in tf.call_args_list)
            )

    def test_existing_certificate_stage_allows_prepare_retry(self):
        state = {
            "values": {
                "root_module": {
                    "resources": [{"type": "google_compute_global_address"}]
                }
            }
        }
        with patch.object(canonical, "terraform", return_value=json.dumps(state)):
            canonical.require_prepare_state({})

    def test_nested_load_balancer_is_also_protected(self):
        state = {
            "values": {
                "root_module": {
                    "child_modules": [
                        {
                            "resources": [
                                {"type": "google_compute_global_forwarding_rule"}
                            ]
                        }
                    ]
                }
            }
        }
        with (
            patch.object(canonical, "terraform", return_value=json.dumps(state)),
            self.assertRaisesRegex(RuntimeError, "already deployed"),
        ):
            canonical.require_prepare_state({})

    def test_current_state_backend_error_is_not_treated_as_first_run(self):
        with (
            patch.object(canonical, "require_terraform"),
            patch.object(canonical, "command", return_value="token"),
            patch.object(
                canonical,
                "terraform",
                side_effect=[
                    "",
                    subprocess.CalledProcessError(1, ["terraform", "show", "-json"]),
                ],
            ) as tf,
            self.assertRaises(subprocess.CalledProcessError),
        ):
            canonical.infrastructure("prepare", "prepare")
        self.assertFalse(
            any(call.args[0][0] in {"plan", "apply"} for call in tf.call_args_list)
        )

    def test_current_state_malformed_json_is_not_treated_as_first_run(self):
        with (
            patch.object(canonical, "terraform", return_value="not-json"),
            self.assertRaisesRegex(RuntimeError, "no plan or apply"),
        ):
            canonical.require_prepare_state({})


if __name__ == "__main__":
    unittest.main()
