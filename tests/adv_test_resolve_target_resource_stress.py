#!/usr/bin/env python3
"""
Adversarial Stress Testing Harness for resolve_target_resource.

Evaluates edge cases, malformed payloads, type corruption, boundary conditions,
and environment isolation guarantees according to the solution-stress-testing playbook.
"""

import json
import os
import tempfile
import unittest
try:
    from infra.agent_engine.verify_agent_engine import resolve_target_resource
except ImportError:
    from infra.agent_engine.archive_python.verify_agent_engine import resolve_target_resource


class TestResolveTargetResourceAdversarialStress(unittest.TestCase):
    """Stress tests for target resource resolution logic."""

    def setUp(self):
        self.dev_resource = "projects/105792947502/locations/us-central1/reasoningEngines/6138588261280382976"
        self.staging_resource = "projects/105792947502/locations/us-central1/reasoningEngines/99261160976547840"
        self.prod_resource = "projects/105792947502/locations/us-central1/reasoningEngines/1252182665583394816"

    # =========================================================================
    # Edge Case 1: Missing and Special Files
    # =========================================================================
    def test_missing_file_returns_none(self):
        """Confirms missing file path gracefully returns None for dynamic lookup."""
        non_existent_path = "/tmp/non_existent_metadata_file_9876543210.json"
        self.assertFalse(os.path.exists(non_existent_path))
        self.assertIsNone(resolve_target_resource(None, "dev", non_existent_path))
        self.assertIsNone(resolve_target_resource(None, "staging", non_existent_path))
        self.assertIsNone(resolve_target_resource(None, "prod", non_existent_path))

    def test_empty_string_path_returns_none(self):
        """Confirms empty string path gracefully returns None."""
        self.assertIsNone(resolve_target_resource(None, "dev", ""))

    def test_dev_null_metadata_path_returns_none(self):
        """Confirms /dev/null (used in Skaffold verify) triggers clean fallback to None."""
        self.assertTrue(os.path.exists("/dev/null"))
        self.assertIsNone(resolve_target_resource(None, "dev", "/dev/null"))
        self.assertIsNone(resolve_target_resource(None, "staging", "/dev/null"))
        self.assertIsNone(resolve_target_resource(None, "prod", "/dev/null"))

    # =========================================================================
    # Edge Case 2: Malformed JSON and Corrupted File Data
    # =========================================================================
    def test_truncated_json_returns_none(self):
        """Tests truncated JSON payload handles JSONDecodeError cleanly."""
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            f.write('{"status": "OPERATIONAL", "tiers": {"dev": "projects/123')
            f.flush()
            self.assertIsNone(resolve_target_resource(None, "dev", f.name))

    def test_non_json_arbitrary_string_returns_none(self):
        """Tests arbitrary text content returns None without unhandled crash."""
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            f.write("PLAIN_TEXT_NOT_JSON\nINVALID_SYNTAX")
            f.flush()
            self.assertIsNone(resolve_target_resource(None, "prod", f.name))

    def test_binary_garbage_returns_none(self):
        """Tests binary garbage handles decoding errors gracefully."""
        with tempfile.NamedTemporaryFile("wb", suffix=".json") as f:
            f.write(b"\x00\xff\xfe\x01\x80\x99\xaa\xbb\xcc\xdd")
            f.flush()
            self.assertIsNone(resolve_target_resource(None, "dev", f.name))

    def test_json_primitive_types_handled_gracefully(self):
        """
        Adversarial fuzzing: Root JSON element is not an object (dict),
        e.g., list, int, boolean, null. data.get() raises AttributeError
        which must be caught by Exception block and return None.
        """
        primitives = [
            [],
            ["dev", "staging"],
            12345,
            True,
            None,
            "just a string",
        ]
        for val in primitives:
            with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
                json.dump(val, f)
                f.flush()
                result = resolve_target_resource(None, "dev", f.name)
                self.assertIsNone(
                    result,
                    f"Expected None for JSON primitive {val!r}, got {result!r}",
                )

    def test_corrupted_tiers_field_type_handled_gracefully(self):
        """Tests non-dict 'tiers' field (e.g. list or string) caught gracefully."""
        corrupted_tiers_payloads = [
            {"tiers": ["dev", "staging"]},
            {"tiers": "invalid_string"},
            {"tiers": 123},
            {"tiers": None},
        ]
        for payload in corrupted_tiers_payloads:
            with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
                json.dump(payload, f)
                f.flush()
                self.assertIsNone(resolve_target_resource(None, "dev", f.name))

    # =========================================================================
    # Edge Case 3: Mismatched Environment and Isolation Guarantees
    # =========================================================================
    def test_single_tier_mismatched_env_returns_none(self):
        """
        CRITICAL VULNERABILITY REGRESSION TEST:
        When metadata contains prod single-tier info, dev and staging MUST return None.
        """
        prod_single_tier = {
            "status": "OPERATIONAL",
            "resource_name": self.prod_resource,
            "env": "prod",
            "display_name": "Analyst Response Agent (Agent Engine Prod)",
        }
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            json.dump(prod_single_tier, f)
            f.flush()

            # Dev probe MUST NOT see prod resource
            dev_result = resolve_target_resource(None, "dev", f.name)
            self.assertIsNone(dev_result)

            # Staging probe MUST NOT see prod resource
            staging_result = resolve_target_resource(None, "staging", f.name)
            self.assertIsNone(staging_result)

            # Prod probe MUST resolve prod resource
            prod_result = resolve_target_resource(None, "prod", f.name)
            self.assertEqual(prod_result, self.prod_resource)

    def test_single_tier_missing_or_empty_env_returns_none(self):
        """Metadata missing 'env' or having empty 'env' does not leak resource_name."""
        payloads = [
            {"resource_name": self.prod_resource},
            {"resource_name": self.prod_resource, "env": ""},
            {"resource_name": self.prod_resource, "env": None},
            {"resource_name": self.prod_resource, "env": "unknown_env"},
        ]
        for p in payloads:
            with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
                json.dump(p, f)
                f.flush()
                self.assertIsNone(resolve_target_resource(None, "dev", f.name))
                self.assertIsNone(resolve_target_resource(None, "staging", f.name))
                self.assertIsNone(resolve_target_resource(None, "prod", f.name))

    def test_case_sensitivity_of_env(self):
        """Confirms strict lowercase matching for env tier string."""
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            json.dump({"resource_name": self.prod_resource, "env": "PROD"}, f)
            f.flush()
            # If env in JSON is uppercase PROD and env_tier is 'prod', returns None
            self.assertIsNone(resolve_target_resource(None, "prod", f.name))

    # =========================================================================
    # Edge Case 4: Valid Multi-Tier Metadata
    # =========================================================================
    def test_valid_multi_tier_resolution(self):
        """Valid multi-tier metadata resolves each tier strictly and independently."""
        multi_tier_payload = {
            "status": "OPERATIONAL",
            "tiers": {
                "dev": self.dev_resource,
                "staging": self.staging_resource,
                "prod": self.prod_resource,
            },
            "resource_name": self.prod_resource,  # Top-level prod metadata
            "env": "prod",
        }
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            json.dump(multi_tier_payload, f)
            f.flush()

            # Dev resolves to dev
            dev_res = resolve_target_resource(None, "dev", f.name)
            self.assertEqual(dev_res, self.dev_resource)
            self.assertNotEqual(dev_res, self.prod_resource)

            # Staging resolves to staging
            stg_res = resolve_target_resource(None, "staging", f.name)
            self.assertEqual(stg_res, self.staging_resource)
            self.assertNotEqual(stg_res, self.prod_resource)

            # Prod resolves to prod
            prd_res = resolve_target_resource(None, "prod", f.name)
            self.assertEqual(prd_res, self.prod_resource)

    def test_partial_multi_tier_fallback(self):
        """
        If 'tiers' contains dev and staging, but not prod,
        and single-tier fallback matches prod, prod resolves via fallback.
        """
        partial_payload = {
            "tiers": {
                "dev": self.dev_resource,
                "staging": self.staging_resource,
            },
            "resource_name": self.prod_resource,
            "env": "prod",
        }
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            json.dump(partial_payload, f)
            f.flush()

            self.assertEqual(resolve_target_resource(None, "dev", f.name), self.dev_resource)
            self.assertEqual(resolve_target_resource(None, "staging", f.name), self.staging_resource)
            self.assertEqual(resolve_target_resource(None, "prod", f.name), self.prod_resource)

    # =========================================================================
    # Edge Case 5: Explicit CLI Override Precedence
    # =========================================================================
    def test_cli_override_preempts_all_file_scenarios(self):
        """
        Explicit resource_name CLI parameter must preempt files completely,
        even if file is corrupted, missing, or points to different tier.
        """
        custom = "projects/test/locations/us-central1/reasoningEngines/custom-999"

        # Overrides corrupted file
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            f.write("CORRUPTED")
            f.flush()
            self.assertEqual(resolve_target_resource(custom, "dev", f.name), custom)

        # Overrides non-existent file
        self.assertEqual(
            resolve_target_resource(custom, "dev", "/tmp/does_not_exist.json"),
            custom,
        )

        # Overrides valid file pointing elsewhere
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            json.dump({"tiers": {"dev": self.dev_resource}}, f)
            f.flush()
            self.assertEqual(resolve_target_resource(custom, "dev", f.name), custom)

    def test_empty_string_resource_name_falls_through_to_metadata(self):
        """If resource_name is empty string (""), falsy check falls through to metadata."""
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
            json.dump({"tiers": {"dev": self.dev_resource}}, f)
            f.flush()
            self.assertEqual(resolve_target_resource("", "dev", f.name), self.dev_resource)


if __name__ == "__main__":
    unittest.main()
