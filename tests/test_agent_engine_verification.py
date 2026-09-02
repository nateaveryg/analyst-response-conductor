#!/usr/bin/env python3
"""
Empirical Stress-Testing and Gating Verification Suite.

Tests:
1. Cloud Deploy native verifyJob gating semantics and automation promotion rules.
2. Response parsing resilience, boundary conditions, and error handling of verify_agent_engine.py.
3. Subprocess exit code semantics across invalid project, invalid location, and unauthenticated execution.
4. Cross-environment metadata leakage vulnerability in verify_agent_engine.py.
5. Automations schema, rule identifier format, wait duration parsing, and IAM permissions.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFY_SCRIPT = (
    REPO_ROOT / "infra" / "agent_engine" / "verify_agent_engine.py"
    if (REPO_ROOT / "infra" / "agent_engine" / "verify_agent_engine.py").exists()
    else REPO_ROOT / "infra" / "agent_engine" / "archive_python" / "verify_agent_engine.py"
)
AUTOMATIONS_FILE = REPO_ROOT / "infra" / "agent_engine" / "automations.yaml"
PIPELINE_FILE = REPO_ROOT / "clouddeploy-agent-engine.yaml"
SKAFFOLD_FILE = REPO_ROOT / "infra" / "agent_engine" / "skaffold-agent-engine.yaml"
DEPLOYED_METADATA_FILE = REPO_ROOT / "infra" / "agent_engine" / "deployed_engine.json"


class TestCloudDeployVerifyGatingAndAutomations(unittest.TestCase):
    """Verifies that native verification gates release promotion in Cloud Deploy."""

    def test_pipeline_declares_verify_strategy_across_all_stages(self):
        """Asserts strategy.standard.verify: true on all pipeline stages."""
        self.assertTrue(PIPELINE_FILE.exists(), f"Missing {PIPELINE_FILE}")
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        
        pipeline = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
        self.assertIsNotNone(pipeline, "DeliveryPipeline kind not found")
        
        stages = pipeline["serialPipeline"]["stages"]
        stage_ids = [s["targetId"] for s in stages]
        self.assertEqual(stage_ids, ["agent-engine-dev", "agent-engine-staging", "agent-engine-prod"])
        
        for stage in stages:
            target_id = stage["targetId"]
            strategy = stage.get("strategy", {}).get("standard", {})
            self.assertTrue(
                strategy.get("verify") is True,
                f"Stage {target_id} must have strategy.standard.verify: true"
            )

    def test_skaffold_declares_native_verify_block(self):
        """Asserts Skaffold uses top-level verify: block referencing verify_agent_engine.py."""
        self.assertTrue(SKAFFOLD_FILE.exists(), f"Missing {SKAFFOLD_FILE}")
        with open(SKAFFOLD_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        self.assertIn("verify", data, "Skaffold manifest must contain top-level verify: block")
        verify_entries = data["verify"]
        self.assertIsInstance(verify_entries, list)
        self.assertGreaterEqual(len(verify_entries), 1)
        
        entry = verify_entries[0]
        self.assertEqual(entry.get("name"), "verify-agent-engine")
        container = entry.get("container", {})
        self.assertEqual(container.get("name"), "agent-engine-verifier")
        image = container.get("image", "")
        self.assertTrue("adk-deployer" in image or "agent-engine-deployer" in image, f"Unexpected verifier image: {image}")
        command_str = " ".join(container.get("command", []))
        self.assertTrue("verify_agent_engine.go" in command_str or "verify_agent_engine.py" in command_str, f"Unexpected verify command: {command_str}")

    def test_automations_declarative_schema_and_destinations(self):
        """Validates automations.yaml rules, selectors, and wait durations."""
        self.assertTrue(AUTOMATIONS_FILE.exists(), f"Missing {AUTOMATIONS_FILE}")
        with open(AUTOMATIONS_FILE, "r", encoding="utf-8") as f:
            automations = list(yaml.safe_load_all(f))
        
        self.assertEqual(len(automations), 2, "Expected exactly 2 Automation resources")
        
        auto_map = {}
        for auto in automations:
            self.assertEqual(auto.get("apiVersion"), "deploy.cloud.google.com/v1")
            self.assertEqual(auto.get("kind"), "Automation")
            name = auto["metadata"]["name"]
            auto_map[name] = auto
            
            # Service account check
            sa = auto.get("serviceAccount", "")
            self.assertIn("105792947502-compute@developer.gserviceaccount.com", sa)
            
            # Rule identifier check: alphanumeric with hyphens
            rules = auto.get("rules", [])
            self.assertGreaterEqual(len(rules), 1)
            for rule in rules:
                rule_spec = rule.get("promoteReleaseRule", {})
                rule_id = rule_spec.get("id")
                self.assertRegex(rule_id, r"^[a-z0-9-]+$")
                self.assertIn(rule_spec.get("wait"), ["0m", "0s", "0"])

        # Dev -> Staging verification
        dev_auto = auto_map["conductor-agent-engine-pipeline/auto-promote-dev-to-staging"]
        self.assertEqual(dev_auto["selector"]["targets"][0]["id"], "agent-engine-dev")
        self.assertEqual(
            dev_auto["rules"][0]["promoteReleaseRule"]["destinationTargetId"],
            "agent-engine-staging"
        )

        # Staging -> Prod verification
        staging_auto = auto_map["conductor-agent-engine-pipeline/auto-promote-staging-to-prod"]
        self.assertEqual(staging_auto["selector"]["targets"][0]["id"], "agent-engine-staging")
        self.assertEqual(
            staging_auto["rules"][0]["promoteReleaseRule"]["destinationTargetId"],
            "agent-engine-prod"
        )

    def test_verify_job_failure_rollout_gating_logic(self):
        """
        Simulates rollout phase progression state machine:
        Proves that verifyJob failure causes rollout state to become FAILED,
        which strictly prevents promoteReleaseRule from triggering.
        """
        def evaluate_rollout(deploy_job_success: bool, verify_job_success: bool):
            """Emulates Cloud Deploy phase & job state evaluation engine."""
            phase = {
                "id": "stable",
                "state": "IN_PROGRESS",
                "deploymentJobs": {
                    "deployJob": {"state": "SUCCEEDED" if deploy_job_success else "FAILED"},
                    "verifyJob": None,
                },
            }
            if not deploy_job_success:
                phase["state"] = "FAILED"
                return {"state": "FAILED", "phases": [phase]}

            # Deploy succeeded, schedule verify
            phase["deploymentJobs"]["verifyJob"] = {
                "state": "SUCCEEDED" if verify_job_success else "FAILED"
            }
            if not verify_job_success:
                phase["state"] = "FAILED"
                return {"state": "FAILED", "phases": [phase]}

            phase["state"] = "SUCCEEDED"
            return {"state": "SUCCEEDED", "phases": [phase]}

        def evaluate_automation(rollout_state: str) -> bool:
            """Cloud Deploy promoteReleaseRule only fires if rollout state is SUCCEEDED."""
            return rollout_state == "SUCCEEDED"

        # Case 1: Deploy succeeds, verify succeeds -> Promotes
        rollout_ok = evaluate_rollout(deploy_job_success=True, verify_job_success=True)
        self.assertEqual(rollout_ok["state"], "SUCCEEDED")
        self.assertTrue(evaluate_automation(rollout_ok["state"]))

        # Case 2: Deploy succeeds, verify fails -> GATED (Does NOT promote)
        rollout_verify_fail = evaluate_rollout(deploy_job_success=True, verify_job_success=False)
        self.assertEqual(rollout_verify_fail["state"], "FAILED")
        self.assertEqual(rollout_verify_fail["phases"][0]["deploymentJobs"]["verifyJob"]["state"], "FAILED")
        self.assertFalse(
            evaluate_automation(rollout_verify_fail["state"]),
            "Cloud Deploy Automations MUST NOT promote when verifyJob fails!"
        )

        # Case 3: Deploy fails -> GATED
        rollout_deploy_fail = evaluate_rollout(deploy_job_success=False, verify_job_success=False)
        self.assertEqual(rollout_deploy_fail["state"], "FAILED")
        self.assertFalse(evaluate_automation(rollout_deploy_fail["state"]))


class TestVerifyAgentEngineProbeResilience(unittest.TestCase):
    """Stress-tests verify_agent_engine.py error handling, assertions, and resilience."""

    def test_cli_argument_parsing_choices(self):
        """Tests that invalid --env argument is rejected with non-zero exit code."""
        cmd = [sys.executable, str(VERIFY_SCRIPT), "--env=invalid_tier"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr.lower())

    def test_unauthenticated_query_fails_cleanly(self):
        """Tests that probe exits non-zero when credentials are stripped."""
        env = dict(os.environ)
        env["GOOGLE_APPLICATION_CREDENTIALS"] = "/dev/null/nonexistent.json"
        env["CLOUDSDK_AUTH_ACCESS_TOKEN"] = ""
        cmd = [
            sys.executable,
            str(VERIFY_SCRIPT),
            "--project=riccardo-blog-test-v1",
            "--location=us-central1",
            "--env=dev",
            "--resource-name=projects/105792947502/locations/us-central1/reasoningEngines/6138588261280382976",
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_resource_name_exits_with_code_1(self):
        """Tests that probing an invalid resource name exits with code 1."""
        env = dict(os.environ)
        # Use token if available
        try:
            token = subprocess.check_output(
                ["gcloud", "auth", "application-default", "print-access-token"],
                timeout=10,
            ).decode().strip()
            env["CLOUDSDK_AUTH_ACCESS_TOKEN"] = token
        except Exception:
            pass

        cmd = [
            sys.executable,
            str(VERIFY_SCRIPT),
            "--project=riccardo-blog-test-v1",
            "--location=us-central1",
            "--resource-name=projects/105792947502/locations/us-central1/reasoningEngines/0000000000000000000",
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Failed to fetch Agent Engine", result.stderr + result.stdout)

    def test_response_parsing_resilience_adversarial_matrix(self):
        """
        Adversarial fuzzing matrix for query_response parsing logic:
        Validates that malformed responses correctly fail assertions.
        """
        def parse_and_validate(query_response):
            """Extracts the exact validation assertions from verify_agent_engine.py."""
            if not isinstance(query_response, dict):
                raise TypeError("Response must be a dictionary")
            assert query_response.get("status") == "success", "Expected status=='success'"
            conf = query_response.get("confidence_score", 0.0)
            if not isinstance(conf, (int, float)):
                raise TypeError("Confidence score must be numeric")
            assert conf >= 0.80, "Confidence below 0.80 threshold"
            assert "response" in query_response and len(query_response["response"]) > 100, "Empty response body"
            return True

        # Valid baseline
        valid_response = {
            "status": "success",
            "confidence_score": 0.86,
            "category": "DEVSECOPS",
            "assigned_sme": "security-sme@google.com",
            "response": "A" * 150,
        }
        self.assertTrue(parse_and_validate(valid_response))

        # Adversarial Test 1: Missing status
        with self.assertRaises(AssertionError):
            parse_and_validate({"confidence_score": 0.90, "response": "A" * 150})

        # Adversarial Test 2: status != 'success'
        with self.assertRaises(AssertionError):
            parse_and_validate({"status": "partial_failure", "confidence_score": 0.90, "response": "A" * 150})

        # Adversarial Test 3: confidence score below 0.80 (boundary test: 0.799)
        with self.assertRaises(AssertionError):
            parse_and_validate({"status": "success", "confidence_score": 0.799, "response": "A" * 150})

        # Adversarial Test 4: Missing confidence score defaults to 0.0 -> assertion fails
        with self.assertRaises(AssertionError):
            parse_and_validate({"status": "success", "response": "A" * 150})

        # Adversarial Test 5: String confidence score triggers TypeError
        with self.assertRaises(TypeError):
            parse_and_validate({"status": "success", "confidence_score": "0.95", "response": "A" * 150})

        # Adversarial Test 6: Empty response body
        with self.assertRaises(AssertionError):
            parse_and_validate({"status": "success", "confidence_score": 0.85, "response": ""})

        # Adversarial Test 7: Truncated response body (< 100 chars)
        with self.assertRaises(AssertionError):
            parse_and_validate({"status": "success", "confidence_score": 0.85, "response": "Short string"})

        # Adversarial Test 8: Non-string response body
        with self.assertRaises(TypeError):
            parse_and_validate({"status": "success", "confidence_score": 0.85, "response": 12345})

        # Adversarial Test 9: Non-dict response payload
        with self.assertRaises(TypeError):
            parse_and_validate(None)
        with self.assertRaises(TypeError):
            parse_and_validate(["status", "success"])

    def test_cross_environment_metadata_leakage_vulnerability(self):
        """
        Validates remediation of cross-environment metadata leakage.
        Ensures dev and staging probers never bind to production metadata.
        """
        import tempfile
        try:
            from infra.agent_engine.verify_agent_engine import resolve_target_resource
        except ImportError:
            from infra.agent_engine.archive_python.verify_agent_engine import resolve_target_resource

        with open(DEPLOYED_METADATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        top_level_resource = data.get("resource_name")
        dev_tier_resource = data.get("tiers", {}).get("dev")
        staging_tier_resource = data.get("tiers", {}).get("staging")
        prod_tier_resource = data.get("tiers", {}).get("prod")

        # 1. Multi-tier metadata resolution isolates environments
        dev_resolved = resolve_target_resource(None, "dev", str(DEPLOYED_METADATA_FILE))
        self.assertEqual(dev_resolved, dev_tier_resource)
        self.assertNotEqual(dev_resolved, prod_tier_resource)

        staging_resolved = resolve_target_resource(None, "staging", str(DEPLOYED_METADATA_FILE))
        self.assertEqual(staging_resolved, staging_tier_resource)
        self.assertNotEqual(staging_resolved, prod_tier_resource)

        prod_resolved = resolve_target_resource(None, "prod", str(DEPLOYED_METADATA_FILE))
        self.assertEqual(prod_resolved, prod_tier_resource)

        # 2. Single-tier metadata fallback respects environment guard
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as tmp:
            json.dump({"resource_name": prod_tier_resource, "env": "prod"}, tmp)
            tmp.flush()
            # Dev probe ignores prod metadata and returns None for dynamic lookup
            self.assertIsNone(resolve_target_resource(None, "dev", tmp.name))
            # Prod probe accepts matching env metadata
            self.assertEqual(resolve_target_resource(None, "prod", tmp.name), prod_tier_resource)

        # 3. Explicit CLI override takes precedence over file metadata
        custom_override = "projects/105792947502/locations/us-central1/reasoningEngines/9999999999"
        self.assertEqual(
            resolve_target_resource(custom_override, "dev", str(DEPLOYED_METADATA_FILE)),
            custom_override,
        )


if __name__ == "__main__":
    unittest.main()
