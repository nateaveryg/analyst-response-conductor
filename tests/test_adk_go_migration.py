"""Automated verification test suite for ADK Go on Vertex AI Agent Engine migration."""

import os
import re
import subprocess
import unittest
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADR_01_PATH = os.path.join(PROJECT_ROOT, "docs", "adr", "ADR-20260829-01-hybrid-go-python-architecture.md")
ADR_02_PATH = os.path.join(PROJECT_ROOT, "docs", "adr", "ADR-20260901-02-adk-go-agent-engine-migration.md")
PLAN_PATH = os.path.join(PROJECT_ROOT, "docs", "adk_go_agent_engine_migration_plan.md")
SKAFFOLD_PATH = os.path.join(PROJECT_ROOT, "infra", "agent_engine", "skaffold-agent-engine.yaml")
CLOUDDEPLOY_PATH = os.path.join(PROJECT_ROOT, "clouddeploy-agent-engine.yaml")
PROBER_PATH = os.path.join(PROJECT_ROOT, "infra", "agent_engine", "verify_agent_engine.go")


class TestAdkGoMigration(unittest.TestCase):
    """Verifies ADRs, Cloud Deploy configurations, Skaffold actions, and Go probers."""

    def test_adr_01_superseded(self):
        """Verify ADR-20260829-01 is marked as superseded."""
        self.assertTrue(os.path.exists(ADR_01_PATH))
        with open(ADR_01_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Superseded by [ADR-20260901-02]", content)
        self.assertIn("Addendum: Superseded by ADR-20260901-02", content)

    def test_adr_02_completeness(self):
        """Verify ADR-20260901-02 exists with required architectural rationale."""
        self.assertTrue(os.path.exists(ADR_02_PATH))
        with open(ADR_02_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("ADR-20260901-02", content)
        self.assertIn("google.golang.org/adk/v2", content)
        self.assertIn("adk deploy agent_engine", content)
        self.assertIn("Vertex AI Agent Engine", content)
        self.assertIn("CustomTargetType", content)

    def test_migration_plan_smart_brevity(self):
        """Verify executive migration plan adheres to Smart Brevity structure."""
        self.assertTrue(os.path.exists(PLAN_PATH))
        with open(PLAN_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("## Executive summary", content)
        self.assertIn("## What's new", content)
        self.assertIn("## Why it matters", content)
        self.assertIn("## Phased migration roadmap", content)
        self.assertIn("Cold Start Latency", content)

    def test_style_compliance(self):
        """Verify no prohibited style terms in new documentation."""
        prohibited = [
            (r"\bnative\b", "built-in"),
            (r"\bmaster\b", "primary"),
            (r"\bslave\b", "secondary"),
            (r"\bwhitelist\b", "allowlist"),
            (r"\bblacklist\b", "blocklist"),
            (r"\bwalkthroughs?\b", "guide/overview"),
            (r"every step of the way", "all along the way"),
            (r"first[- ]class citizen", "top-level"),
            (r"\[here\]", "meaningful link text"),
        ]
        for path in [ADR_02_PATH, PLAN_PATH]:
            with open(path, "r", encoding="utf-8") as f:
                doc = f.read()
            for pattern, rep in prohibited:
                matches = list(re.finditer(pattern, doc, re.IGNORECASE))
                self.assertEqual(
                    len(matches),
                    0,
                    f"Prohibited term '{matches[0].group() if matches else pattern}' found in {os.path.basename(path)}. Use '{rep}' instead."
                )

    def test_skaffold_adk_custom_actions(self):
        """Verify Skaffold customActions run ADK deployment and Go verification."""
        self.assertTrue(os.path.exists(SKAFFOLD_PATH))
        with open(SKAFFOLD_PATH, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        config = docs[0]
        self.assertEqual(config.get("apiVersion"), "skaffold/v4beta7")
        action_names = [a.get("name") for a in config.get("customActions", [])]
        self.assertIn("render-agent-engine", action_names)
        self.assertIn("deploy-agent-engine", action_names)

        # Inspect deploy-agent-engine command
        deploy_action = next(a for a in config["customActions"] if a["name"] == "deploy-agent-engine")
        cmd_str = " ".join(deploy_action["containers"][0]["command"])
        self.assertTrue(
            "adk deploy agent_engine" in cmd_str or "adk deploy agentengine" in cmd_str,
            f"Expected 'adk deploy agentengine' or 'adk deploy agent_engine' in deploy command: {cmd_str}"
        )

        # Inspect verify hook
        verify_hooks = config.get("verify", [])
        self.assertTrue(len(verify_hooks) > 0)
        verify_cmd = " ".join(verify_hooks[0]["container"]["command"])
        self.assertIn("verify_agent_engine.go", verify_cmd)

    def test_clouddeploy_custom_target_validity(self):
        """Verify Cloud Deploy manifests declare vertex-ai-agent-engine CustomTargetType."""
        self.assertTrue(os.path.exists(CLOUDDEPLOY_PATH))
        with open(CLOUDDEPLOY_PATH, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))

        kinds = {d.get("kind") for d in docs if d}
        self.assertIn("DeliveryPipeline", kinds)
        self.assertIn("CustomTargetType", kinds)
        self.assertIn("Target", kinds)

        custom_target = next(d for d in docs if d.get("kind") == "CustomTargetType")
        self.assertEqual(custom_target["metadata"]["name"], "vertex-ai-agent-engine")
        self.assertEqual(custom_target["customActions"]["renderAction"], "render-agent-engine")
        self.assertEqual(custom_target["customActions"]["deployAction"], "deploy-agent-engine")

    def test_go_verification_prober(self):
        """Verify the Go synthetic smoke test prober executes successfully."""
        self.assertTrue(os.path.exists(PROBER_PATH))
        cmd = ["go", "run", PROBER_PATH, "--target=dev"]
        res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Prober failed: {res.stderr}\n{res.stdout}")
        combined_output = res.stdout + res.stderr
        self.assertIn("All 3/3 synthetic smoke test scenarios PASSED", combined_output)

    def test_go_agent_unit_tests(self):
        """Verify unit tests in app/agent_engine_go execute and pass."""
        agent_dir = os.path.join(PROJECT_ROOT, "app", "agent_engine_go")
        self.assertTrue(os.path.exists(agent_dir))
        cmd = ["go", "test", "-v", "./..."]
        res = subprocess.run(cmd, cwd=agent_dir, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Go unit tests failed: {res.stderr}\n{res.stdout}")
        combined_output = res.stdout + res.stderr
        self.assertIn("PASS", combined_output)

    def test_cloudbuild_pipeline_includes_adk_steps(self):
        """Verify cloudbuild-agent-engine.yaml includes Go ADK test and deployer steps."""
        cb_path = os.path.join(PROJECT_ROOT, "cloudbuild-agent-engine.yaml")
        self.assertTrue(os.path.exists(cb_path))
        with open(cb_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        step_ids = [s.get("id") for s in data.get("steps", []) if s.get("id")]
        self.assertIn("go-adk-agent-tests", step_ids)
        self.assertIn("build-and-push-adk-deployer", step_ids)


if __name__ == "__main__":
    unittest.main()
