#!/usr/bin/env python3
"""
Unit and Integration Tests for Conductor v3 Frontend Cloud Deploy Pipeline & Automations.
Validates:
1. Declarative Automations schema (infra/frontend/automations.yaml)
   - Auto-promotion from dev to staging via promoteReleaseRule
   - Auto-advancement of canary phases on prod via advanceRolloutRule
   - Strict absence of automated staging-to-prod promotion (manual gate enforcement)
2. Delivery Pipeline & Targets (clouddeploy-frontend.yaml)
   - Built-in verification (verify: true) across standard and canary stages
   - Canary traffic shaping (25% -> 50% -> 100% stable)
   - Mandatory manual approval gate on prod (requireApproval: true)
   - Execution configs specifying VERIFY usage and dedicated service account
3. Skaffold verification block (skaffold-frontend.yaml)
4. Frontend verification prober logic (infra/frontend/verify_frontend.py)
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

REPO_ROOT = Path(__file__).parent.parent
AUTOMATIONS_FILE = REPO_ROOT / "infra" / "frontend" / "automations.yaml"
CLOUDDEPLOY_FILE = REPO_ROOT / "clouddeploy-frontend.yaml"
SKAFFOLD_FILE = REPO_ROOT / "skaffold-frontend.yaml"
VERIFY_SCRIPT = REPO_ROOT / "infra" / "frontend" / "verify_frontend.py"


def load_yaml_documents(filepath: Path) -> list[dict]:
    assert filepath.exists(), f"File {filepath} does not exist"
    with open(filepath, "r", encoding="utf-8") as f:
        return list(yaml.safe_load_all(f))


class TestFrontendPipelineAndAutomations(unittest.TestCase):
    """Verifies declarative Cloud Deploy configuration and automated promotion rules."""

    def test_01_automations_yaml_declarative_schema_and_rules(self):
        """Validates infra/frontend/automations.yaml syntax, rules, and selectors."""
        self.assertTrue(AUTOMATIONS_FILE.exists(), f"Missing {AUTOMATIONS_FILE}")
        automations = load_yaml_documents(AUTOMATIONS_FILE)

        self.assertEqual(len(automations), 2, "Expected exactly 2 Automation resources in automations.yaml")

        auto_map = {}
        for auto in automations:
            self.assertEqual(auto.get("apiVersion"), "deploy.cloud.google.com/v1")
            self.assertEqual(auto.get("kind"), "Automation")
            name = auto["metadata"]["name"]
            auto_map[name] = auto

            # Service account binding check
            sa = auto.get("serviceAccount", "")
            self.assertIn("105792947502-compute@developer.gserviceaccount.com", sa)

        # 1. Dev-to-Staging Auto-Promotion Rule
        dev_auto_name = "conductor-v3-frontend-pipeline/auto-promote-dev-to-staging"
        self.assertIn(dev_auto_name, auto_map)
        dev_auto = auto_map[dev_auto_name]
        dev_targets = [t["id"] for t in dev_auto.get("selector", {}).get("targets", [])]
        self.assertEqual(dev_targets, ["dev"], "Dev automation must select target 'dev'")

        dev_rules = dev_auto.get("rules", [])
        self.assertEqual(len(dev_rules), 1)
        promote_rule = dev_rules[0].get("promoteReleaseRule")
        self.assertIsNotNone(promote_rule, "Dev automation must declare promoteReleaseRule")
        self.assertEqual(promote_rule.get("destinationTargetId"), "staging")
        self.assertIn(promote_rule.get("wait"), ["0m", "0s", "0"])

        # 2. Prod Canary Auto-Advancement Rule
        canary_auto_name = "conductor-v3-frontend-pipeline/auto-advance-canary"
        self.assertIn(canary_auto_name, auto_map)
        canary_auto = auto_map[canary_auto_name]
        prod_targets = [t["id"] for t in canary_auto.get("selector", {}).get("targets", [])]
        self.assertEqual(prod_targets, ["prod"], "Canary automation must select target 'prod'")

        canary_rules = canary_auto.get("rules", [])
        self.assertEqual(len(canary_rules), 1)
        advance_rule = canary_rules[0].get("advanceRolloutRule")
        self.assertIsNotNone(advance_rule, "Prod automation must declare advanceRolloutRule")
        self.assertEqual(advance_rule.get("sourcePhases"), ["canary-25", "canary-50"])
        self.assertIn(advance_rule.get("wait"), ["0m", "0s", "0"])

        # 3. Verify Absence of Automated Promotion from Staging to Prod
        staging_auto = next(
            (a for a in automations if "auto-promote-staging-to-prod" in a["metadata"]["name"]),
            None,
        )
        self.assertIsNone(
            staging_auto,
            "Automated promotion from staging to prod must NOT exist; manual approval required.",
        )

    def test_02_clouddeploy_frontend_pipeline_verification_and_canary(self):
        """Validates clouddeploy-frontend.yaml pipeline stages, verify configs, and targets."""
        self.assertTrue(CLOUDDEPLOY_FILE.exists(), f"Missing {CLOUDDEPLOY_FILE}")
        docs = load_yaml_documents(CLOUDDEPLOY_FILE)

        pipeline = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
        self.assertIsNotNone(pipeline, "DeliveryPipeline not found")
        self.assertEqual(pipeline["metadata"]["name"], "conductor-v3-frontend-pipeline")

        stages = pipeline["serialPipeline"]["stages"]
        stage_map = {s["targetId"]: s for s in stages}
        self.assertEqual(list(stage_map.keys()), ["dev", "staging", "prod"])

        # Dev and Staging built-in verification
        self.assertTrue(
            stage_map["dev"].get("strategy", {}).get("standard", {}).get("verify"),
            "Dev stage must enable standard verify: true",
        )
        self.assertTrue(
            stage_map["staging"].get("strategy", {}).get("standard", {}).get("verify"),
            "Staging stage must enable standard verify: true",
        )

        # Prod Canary strategy and verification
        prod_strategy = stage_map["prod"].get("strategy", {}).get("canary", {})
        self.assertIsNotNone(prod_strategy, "Prod stage must declare canary strategy")
        self.assertTrue(
            prod_strategy.get("runtimeConfig", {}).get("cloudRun", {}).get("automaticTrafficControl"),
            "Canary must enable automaticTrafficControl for Cloud Run",
        )
        canary_deploy = prod_strategy.get("canaryDeployment", {})
        self.assertEqual(canary_deploy.get("percentages"), [25, 50])
        self.assertTrue(canary_deploy.get("verify"), "Canary deployment must enable verify: true")

        # Target definitions
        targets = {d["metadata"]["name"]: d for d in docs if d.get("kind") == "Target"}
        self.assertIn("dev", targets)
        self.assertIn("staging", targets)
        self.assertIn("prod", targets)

        # Manual approval gate on prod
        self.assertTrue(
            targets["prod"].get("requireApproval"),
            "Prod target must enforce requireApproval: true",
        )

        # ExecutionConfigs with VERIFY usage
        for target_name, target_doc in targets.items():
            exec_configs = target_doc.get("executionConfigs", [])
            self.assertGreaterEqual(len(exec_configs), 1, f"Target {target_name} missing executionConfigs")
            usages = exec_configs[0].get("usages", [])
            self.assertIn("VERIFY", usages, f"Target {target_name} executionConfigs must include VERIFY")
            self.assertIn("RENDER", usages)
            self.assertIn("DEPLOY", usages)

    def test_03_skaffold_frontend_verify_block(self):
        """Validates skaffold-frontend.yaml contains a top-level verify block."""
        self.assertTrue(SKAFFOLD_FILE.exists(), f"Missing {SKAFFOLD_FILE}")
        docs = load_yaml_documents(SKAFFOLD_FILE)
        sk = docs[0]

        verify_list = sk.get("verify", [])
        self.assertGreaterEqual(len(verify_list), 1, "skaffold-frontend.yaml must declare verify list")

        verify_item = verify_list[0]
        self.assertEqual(verify_item.get("name"), "verify-frontend")
        container = verify_item.get("container", {})
        command_str = " ".join(container.get("command", []))
        self.assertIn("verify_frontend.py", command_str)

    def test_04_verify_frontend_script_cli_and_resolution(self):
        """Validates verify_frontend.py argument parsing and environment resolution."""
        self.assertTrue(VERIFY_SCRIPT.exists(), f"Missing {VERIFY_SCRIPT}")
        self.assertTrue(os.access(VERIFY_SCRIPT, os.X_OK), "verify_frontend.py must be executable")

        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_frontend", str(VERIFY_SCRIPT))
        vf_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vf_mod)

        # Test CLI environment resolution
        mock_args = MagicMock()
        mock_args.env = "staging"
        mock_args.phase = "canary-25"
        mock_args.url = None

        env, phase, url = vf_mod.resolve_environment(mock_args)
        self.assertEqual(env, "staging")
        self.assertEqual(phase, "canary-25")
        self.assertIn("staging", url)

        # Test environment variable resolution
        mock_args_none = MagicMock()
        mock_args_none.env = None
        mock_args_none.phase = None
        mock_args_none.url = None

        with patch.dict(os.environ, {"CLOUD_DEPLOY_TARGET": "prod", "CLOUD_DEPLOY_PHASE": "canary-50"}):
            env, phase, url = vf_mod.resolve_environment(mock_args_none)
            self.assertEqual(env, "prod")
            self.assertEqual(phase, "canary-50")
            self.assertIn("prod", url)


if __name__ == "__main__":
    unittest.main()
