#!/usr/bin/env python3
"""
Adversarial Multi-Tier Live Probing, Boundary Stress Testing, and Pipeline Idempotency Harness.
Targeting Vertex AI Agent Engine (Reasoning Engine) across Dev, Staging, and Production tiers.

Objectives:
1. Probe all three tier live endpoints (dev, staging, prod) with standard and adversarial queries.
2. Validate performance (latency < 1.0s) and quality (confidence score >= 0.80) across all environments.
3. Validate error resilience under adversarial boundary inputs.
4. Verify pipeline idempotency via live Cloud Deploy state.
"""

import json
import logging
import os
import subprocess
import sys
import time
import unittest
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("adv_multi_tier_probe")

PROJECT_ID = "riccardo-blog-test-v1"
LOCATION = "us-central1"

TIER_ENDPOINTS = {
    "dev": "projects/105792947502/locations/us-central1/reasoningEngines/6138588261280382976",
    "staging": "projects/105792947502/locations/us-central1/reasoningEngines/99261160976547840",
    "prod": "projects/105792947502/locations/us-central1/reasoningEngines/1252182665583394816",
}


def get_gcloud_auth_env() -> Dict[str, str]:
    env = os.environ.copy()
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            text=True,
            timeout=15,
        ).strip()
        env["CLOUDSDK_AUTH_ACCESS_TOKEN"] = token
    except Exception as e:
        logger.warning(f"Could not fetch auth access token: {e}")
    return env


class TestMultiTierLiveProbesAndStress(unittest.TestCase):
    """Adversarial stress and performance prober across Dev, Staging, and Prod tiers."""

    @classmethod
    def setUpClass(cls):
        import vertexai
        from vertexai import agent_engines
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        cls.agent_engines = agent_engines
        cls.clients = {}
        for tier, res_name in TIER_ENDPOINTS.items():
            logger.info(f"Connecting to {tier.upper()} engine: {res_name}")
            cls.clients[tier] = cls.agent_engines.get(res_name)

    def test_01_baseline_query_performance_and_quality_all_tiers(self):
        """Probes all three live endpoints: latency < 1.0s, confidence >= 0.80, status == 'success'."""
        prompt = (
            "How does Google Cloud ensure container vulnerability scanning, "
            "SLSA level 3 artifact provenance, and SOC2 compliance across multi-stage pipelines?"
        )

        results = {}
        for tier, client in self.clients.items():
            logger.info(f"Executing baseline probe against {tier.upper()} ({client.display_name})...")
            t0 = time.perf_counter()
            resp = client.query(prompt=prompt, workspace_id=f"ws-challenger-{tier}-baseline")
            elapsed = time.perf_counter() - t0

            status = resp.get("status")
            confidence = resp.get("confidence_score", 0.0)
            category = resp.get("category")
            sme = resp.get("assigned_sme")
            text = resp.get("response", "")

            logger.info(
                f"[{tier.upper()}] Status: {status}, Latency: {elapsed:.4f}s, Confidence: {confidence:.2f}, SME: {sme}"
            )

            results[tier] = {
                "latency": elapsed,
                "confidence": confidence,
                "status": status,
                "category": category,
                "sme": sme,
            }

            self.assertEqual(status, "success", f"Tier {tier} query failed: {resp}")
            self.assertGreaterEqual(
                confidence, 0.80,
                f"Tier {tier} confidence {confidence} is below required threshold 0.80"
            )
            self.assertLess(
                elapsed, 1.0,
                f"Tier {tier} latency {elapsed:.4f}s exceeded required limit of 1.0s"
            )
            self.assertGreater(len(text), 100, f"Tier {tier} response body unexpectedly short")
            self.assertIsNotNone(sme, f"Tier {tier} missing assigned SME")
            self.assertIsNotNone(category, f"Tier {tier} missing taxonomy category")

    def test_02_adversarial_high_complexity_multi_standard_query(self):
        """Adversarial stress test: Deep compliance inquiry covering 6 distinct regulatory frameworks."""
        complex_prompt = (
            "Provide detailed architectural controls and evidence mapping for Conductor v3 covering: "
            "1. HIPAA § 164.312(a)(2)(iv) encryption at rest and in transit. "
            "2. FedRAMP High Moderate baseline access control AC-2 and AC-3. "
            "3. PCI DSS 4.0 requirement 6.4 regarding web applications and DLP scrubbing. "
            "4. ISO/IEC 27001:2022 Annex A 8.24 cryptography and key rotation. "
            "5. NIST SP 800-53 Rev 5 SI-4 system monitoring and Cloud Audit Logging. "
            "6. SLSA Level 4 hermetic container build pipelines and non-forgeable attestation."
        )

        for tier, client in self.clients.items():
            logger.info(f"Injecting complex multi-standard prompt into {tier.upper()}...")
            t0 = time.perf_counter()
            resp = client.query(prompt=complex_prompt, workspace_id=f"ws-adv-complex-{tier}")
            elapsed = time.perf_counter() - t0

            confidence = resp.get("confidence_score", 0.0)
            status = resp.get("status")

            logger.info(
                f"[ADV-{tier.upper()}] Status: {status}, Latency: {elapsed:.4f}s, Confidence: {confidence:.2f}"
            )
            self.assertEqual(status, "success")
            self.assertGreaterEqual(confidence, 0.80)
            self.assertLess(elapsed, 1.0, f"Tier {tier} complex query latency {elapsed:.4f}s >= 1.0s")

    def test_03_adversarial_boundary_injection_and_symbol_handling(self):
        """Adversarial stress test: Edge case symbols, punctuation, quotes, and long token boundaries."""
        boundary_prompt = (
            "Evaluate compliance: <script>alert('xss')</script> -- "
            "SELECT * FROM users WHERE '1'='1'; "
            "Unicode test: \u00e9\u00e0\u00e7\u20ac\u00a9\u2122\U0001f512\U0001f6e1\ufe0f "
            "Special characters: !@#$%^&*()_+~`|}{[]:;?><,./'\" "
            "Does the container runtime prevent shell escapes and enforce distroless isolation?"
        )

        for tier, client in self.clients.items():
            logger.info(f"Injecting boundary symbols into {tier.upper()}...")
            t0 = time.perf_counter()
            resp = client.query(prompt=boundary_prompt, workspace_id=f"ws-adv-boundary-{tier}")
            elapsed = time.perf_counter() - t0

            confidence = resp.get("confidence_score", 0.0)
            status = resp.get("status")

            logger.info(
                f"[BOUNDARY-{tier.upper()}] Status: {status}, Latency: {elapsed:.4f}s, Confidence: {confidence:.2f}"
            )
            self.assertEqual(status, "success")
            self.assertGreaterEqual(confidence, 0.80)
            self.assertLess(elapsed, 1.0)

    def test_04_pipeline_idempotency_and_active_release_integrity(self):
        """Validates that re-applying manifests via gcloud deploy apply does not disrupt active rollouts."""
        env = get_gcloud_auth_env()

        # Step 1: Re-apply pipeline
        apply_pipe_cmd = [
            "gcloud", "deploy", "apply",
            "--file=clouddeploy-agent-engine.yaml",
            "--region=us-central1",
            "--project=riccardo-blog-test-v1",
        ]
        res1 = subprocess.run(apply_pipe_cmd, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(res1.returncode, 0, f"Re-applying pipeline manifest failed: {res1.stderr}")

        # Step 2: Re-apply automations
        apply_auto_cmd = [
            "gcloud", "deploy", "apply",
            "--file=infra/agent_engine/automations.yaml",
            "--region=us-central1",
            "--project=riccardo-blog-test-v1",
        ]
        res2 = subprocess.run(apply_auto_cmd, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(res2.returncode, 0, f"Re-applying automations manifest failed: {res2.stderr}")

        # Step 3: Verify automations list retains both rules
        list_auto_cmd = [
            "gcloud", "deploy", "automations", "list",
            "--delivery-pipeline=conductor-agent-engine-pipeline",
            "--region=us-central1",
            "--project=riccardo-blog-test-v1",
            "--format=json",
        ]
        res3 = subprocess.run(list_auto_cmd, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(res3.returncode, 0, f"Listing automations failed: {res3.stderr}")
        automations = json.loads(res3.stdout)
        auto_names = [a.get("name", "").split("/")[-1] for a in automations]
        self.assertIn("auto-promote-dev-to-staging", auto_names)
        self.assertIn("auto-promote-staging-to-prod", auto_names)

        # Step 4: Verify latest release rollouts remain SUCCEEDED
        release_id = "release-ae-auto-20260829032842"
        list_rollouts_cmd = [
            "gcloud", "deploy", "rollouts", "list",
            f"--release={release_id}",
            "--delivery-pipeline=conductor-agent-engine-pipeline",
            "--region=us-central1",
            "--project=riccardo-blog-test-v1",
            "--format=json",
        ]
        res4 = subprocess.run(list_rollouts_cmd, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(res4.returncode, 0, f"Listing rollouts failed: {res4.stderr}")
        rollouts = json.loads(res4.stdout)
        self.assertEqual(len(rollouts), 3, "Expected 3 rollouts for active release")
        for r in rollouts:
            target = r.get("targetId")
            state = r.get("state")
            self.assertEqual(state, "SUCCEEDED", f"Rollout for {target} is not SUCCEEDED: {state}")


if __name__ == "__main__":
    unittest.main()
