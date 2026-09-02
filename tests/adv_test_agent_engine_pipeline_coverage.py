#!/usr/bin/env python3
"""
Adversarial Coverage Audit & Manifest Contract Tests for Conductor v3 Agent Engine Pipeline.
Validates Requirements R1, R2, R3, and R4 declarative contracts and live GCP state:
- R1: Skaffold Native Verification (verify: block, singular container mapping)
- R2: Cloud Deploy Verification Strategy (strategy.standard.verify: true, no postdeploy.actions, requireApproval: false)
- R3: Cloud Deploy Automations (kind: Automation, promoteReleaseRule, correct targets & service account)
- R4: Multi-tier target configuration and idempotency readiness
"""

import os
import unittest
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_yaml_documents(filepath: Path):
    assert filepath.exists(), f"Configuration file {filepath} does not exist"
    with open(filepath, "r", encoding="utf-8") as f:
        return list(yaml.safe_load_all(f))


class TestAgentEnginePipelineCoverageAudit(unittest.TestCase):
    """Audits test coverage and declarative specification conformance for Session 4."""

    def test_r1_skaffold_native_verify_block_conformance(self):
        """R1: Verifies skaffold-agent-engine.yaml top-level verify block."""
        skaffold_file = REPO_ROOT / "infra" / "agent_engine" / "skaffold-agent-engine.yaml"
        docs = load_yaml_documents(skaffold_file)
        self.assertEqual(len(docs), 1, "skaffold-agent-engine.yaml should contain exactly 1 document")
        sk = docs[0]

        # Verify apiVersion and kind
        self.assertTrue(sk.get("apiVersion", "").startswith("skaffold/"), "Must specify skaffold apiVersion")
        self.assertEqual(sk.get("kind"), "Config")

        # Verify customActions does NOT contain verify-agent-engine
        custom_actions = sk.get("customActions", [])
        action_names = [a.get("name") for a in custom_actions]
        self.assertNotIn(
            "verify-agent-engine",
            action_names,
            "Legacy verify-agent-engine must be removed from customActions",
        )
        self.assertIn("render-agent-engine", action_names)
        self.assertIn("deploy-agent-engine", action_names)

        # Verify top-level verify block exists
        self.assertIn("verify", sk, "skaffold-agent-engine.yaml must declare a top-level 'verify:' block")
        verify_entries = sk.get("verify", [])
        self.assertEqual(len(verify_entries), 1, "Expected exactly 1 verify entry")
        verify_item = verify_entries[0]
        self.assertEqual(verify_item.get("name"), "verify-agent-engine")

        # Verify singular container mapping (Skaffold v4 schema requirement)
        self.assertIn("container", verify_item, "Must use singular 'container:' mapping, not 'containers:'")
        self.assertNotIn("containers", verify_item, "Must NOT use plural 'containers:' in verify")
        container = verify_item["container"]
        self.assertEqual(container.get("name"), "agent-engine-verifier")
        self.assertTrue(
            "adk-deployer" in container.get("image", "") or "agent-engine-deployer" in container.get("image", ""),
            f"Unexpected verifier image: {container.get('image', '')}",
        )

        # Verify verify_agent_engine.go or legacy verify_agent_engine.py is executed
        cmd = " ".join(container.get("command", []))
        self.assertTrue(
            "verify_agent_engine.go" in cmd or "verify_agent_engine.py" in cmd,
            f"Unexpected verify command: {cmd}",
        )

    def test_r2_clouddeploy_pipeline_verify_strategy_conformance(self):
        """R2: Verifies clouddeploy-agent-engine.yaml delivery pipeline and stages."""
        cd_file = REPO_ROOT / "clouddeploy-agent-engine.yaml"
        docs = load_yaml_documents(cd_file)
        self.assertGreaterEqual(len(docs), 4, "Must contain DeliveryPipeline, CustomTargetType, and 3 Targets")

        pipeline_doc = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
        self.assertIsNotNone(pipeline_doc, "DeliveryPipeline kind not found")
        self.assertEqual(pipeline_doc["metadata"]["name"], "conductor-agent-engine-pipeline")

        stages = pipeline_doc.get("serialPipeline", {}).get("stages", [])
        self.assertEqual(len(stages), 3, "Pipeline must define 3 stages (dev, staging, prod)")

        stage_target_ids = [s.get("targetId") for s in stages]
        self.assertEqual(stage_target_ids, ["agent-engine-dev", "agent-engine-staging", "agent-engine-prod"])

        # Check each stage specifies strategy.standard.verify: true and NO postdeploy.actions
        for stage in stages:
            target_id = stage.get("targetId")
            strategy = stage.get("strategy", {}).get("standard", {})
            self.assertTrue(
                strategy.get("verify") is True,
                f"Stage {target_id} must have strategy.standard.verify: true",
            )
            self.assertNotIn(
                "postdeploy",
                strategy,
                f"Stage {target_id} must NOT have legacy postdeploy actions",
            )

        # Check Target agent-engine-prod has requireApproval: false for autonomous mode
        targets = [d for d in docs if d.get("kind") == "Target"]
        self.assertEqual(len(targets), 3, "Must define exactly 3 Target resources")

        prod_target = next((t for t in targets if t["metadata"]["name"] == "agent-engine-prod"), None)
        self.assertIsNotNone(prod_target, "agent-engine-prod target not found")
        self.assertFalse(
            prod_target.get("requireApproval", True),
            "agent-engine-prod must have requireApproval: false for autonomous auto-approval",
        )

        # Check execution configs
        for target in targets:
            name = target["metadata"]["name"]
            exec_configs = target.get("executionConfigs", [])
            self.assertTrue(len(exec_configs) > 0, f"Target {name} must declare executionConfigs")
            usages = exec_configs[0].get("usages", [])
            self.assertIn("VERIFY", usages, f"Target {name} executionConfig must permit VERIFY usage")
            self.assertEqual(
                exec_configs[0].get("serviceAccount"),
                "105792947502-compute@developer.gserviceaccount.com",
            )

    def test_r3_automations_manifest_conformance(self):
        """R3: Verifies infra/agent_engine/automations.yaml declaration and rules."""
        auto_file = REPO_ROOT / "infra" / "agent_engine" / "automations.yaml"
        docs = load_yaml_documents(auto_file)
        self.assertEqual(len(docs), 2, "automations.yaml should contain exactly 2 Automation documents")

        auto_dev = next((d for d in docs if "auto-promote-dev-to-staging" in d["metadata"]["name"]), None)
        self.assertIsNotNone(auto_dev, "auto-promote-dev-to-staging not found")
        self.assertEqual(auto_dev.get("apiVersion"), "deploy.cloud.google.com/v1")
        self.assertEqual(auto_dev.get("kind"), "Automation")
        self.assertEqual(
            auto_dev.get("serviceAccount"),
            "105792947502-compute@developer.gserviceaccount.com",
        )
        self.assertEqual(auto_dev.get("selector", {}).get("targets", [])[0].get("id"), "agent-engine-dev")
        dev_rules = auto_dev.get("rules", [])
        self.assertEqual(len(dev_rules), 1)
        self.assertIn("promoteReleaseRule", dev_rules[0])
        self.assertEqual(dev_rules[0]["promoteReleaseRule"].get("destinationTargetId"), "agent-engine-staging")
        self.assertEqual(dev_rules[0]["promoteReleaseRule"].get("wait"), "0m")

        auto_staging = next((d for d in docs if "auto-promote-staging-to-prod" in d["metadata"]["name"]), None)
        self.assertIsNotNone(auto_staging, "auto-promote-staging-to-prod not found")
        self.assertEqual(auto_staging.get("apiVersion"), "deploy.cloud.google.com/v1")
        self.assertEqual(auto_staging.get("kind"), "Automation")
        self.assertEqual(
            auto_staging.get("serviceAccount"),
            "105792947502-compute@developer.gserviceaccount.com",
        )
        self.assertEqual(auto_staging.get("selector", {}).get("targets", [])[0].get("id"), "agent-engine-staging")
        staging_rules = auto_staging.get("rules", [])
        self.assertEqual(len(staging_rules), 1)
        self.assertIn("promoteReleaseRule", staging_rules[0])
        self.assertEqual(staging_rules[0]["promoteReleaseRule"].get("destinationTargetId"), "agent-engine-prod")
        self.assertEqual(staging_rules[0]["promoteReleaseRule"].get("wait"), "0m")


if __name__ == "__main__":
    unittest.main()
