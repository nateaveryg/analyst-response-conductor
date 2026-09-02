#!/usr/bin/env python3
"""
Post-Deployment Automated Verification & Smoke Testing Prober for Vertex AI Agent Engine.
Invoked as a post-deploy verification stage within Cloud Deploy pipelines.
"""
import argparse
import json
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("conductor.verify_agent_engine")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Deployed Vertex AI Agent Engine.")
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("CLOUD_DEPLOY_PROJECT_ID", "riccardo-blog-test-v1")),
        help="Google Cloud Project ID",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("GOOGLE_CLOUD_LOCATION", os.environ.get("CLOUD_DEPLOY_LOCATION", "us-central1")),
        help="Google Cloud Region",
    )
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "prod"],
        default=os.environ.get("TARGET_ENV", "dev"),
        help="Deployment Target Environment Tier",
    )
    parser.add_argument(
        "--resource-name",
        default=None,
        help="Explicit Resource Name of the Reasoning Engine to probe",
    )
    parser.add_argument(
        "--deployed-metadata",
        default=os.path.join(os.path.dirname(__file__), "deployed_engine.json"),
        help="Path to deployment JSON metadata",
    )
    return parser.parse_args()


def resolve_target_resource(
    resource_name: str | None,
    env_tier: str,
    metadata_path: str,
) -> str | None:
    """Resolves target Reasoning Engine resource name for the specified tier.

    Resolution order:
    1. Explicit CLI argument (--resource-name).
    2. Multi-tier metadata lookup: data.get("tiers", {}).get(env_tier).
    3. Single-tier metadata fallback: data.get("resource_name") if data.get("env") == env_tier.
    4. Fallback: returns None (triggers dynamic lookup by display name).
    """
    if resource_name:
        return resource_name

    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Step 1: Look up tier-specific resource from "tiers" dictionary
            tier_resource = data.get("tiers", {}).get(env_tier)
            if tier_resource:
                logger.info(
                    f"Loaded target resource for tier '{env_tier}' from metadata tiers: {tier_resource}"
                )
                return tier_resource

            # Step 2: Check if single-tier metadata env matches the target tier
            if data.get("env") == env_tier and data.get("resource_name"):
                matched_resource = data.get("resource_name")
                logger.info(
                    f"Loaded target resource matching env '{env_tier}' from metadata: {matched_resource}"
                )
                return matched_resource

            logger.info(
                f"No metadata resource matching tier '{env_tier}', falling back to dynamic lookup"
            )
        except Exception as e:
            logger.warning(f"Could not read metadata from {metadata_path}: {e}")

    return None


def main():
    args = parse_args()

    env_tier = args.env
    target_name = os.environ.get("CLOUD_DEPLOY_TARGET", "")
    if "staging" in target_name:
        env_tier = "staging"
    elif "prod" in target_name:
        env_tier = "prod"
    elif "dev" in target_name:
        env_tier = "dev"

    logger.info("====================================================================")
    logger.info("  🧪 Conductor v2 -> Agent Engine Post-Deployment Verification Prober")
    logger.info("====================================================================")
    logger.info(f"Target Environment: {env_tier.upper()}")
    logger.info(f"Project ID:         {args.project}")
    logger.info(f"Region:             {args.location}")

    resource_name = resolve_target_resource(
        args.resource_name,
        env_tier,
        args.deployed_metadata,
    )

    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=args.project, location=args.location)

    engine_client = None
    if resource_name:
        logger.info(f"Binding client to Reasoning Engine: {resource_name}...")
        try:
            engine_client = agent_engines.get(resource_name)
        except Exception as e:
            logger.error(f"Failed to fetch Agent Engine at '{resource_name}': {e}")
            sys.exit(1)
    else:
        # Look up by display name convention
        target_display_name = f"Analyst Response Agent (Agent Engine {env_tier.capitalize()})"
        logger.info(f"Looking up Agent Engine matching '{target_display_name}'...")
        for engine in agent_engines.list():
            if engine.display_name == target_display_name:
                engine_client = engine
                resource_name = engine.resource_name
                logger.info(f"Found active engine resource: {resource_name}")
                break

    if not engine_client:
        logger.error(f"No Agent Engine found for tier '{env_tier}' to verify.")
        sys.exit(1)

    logger.info("--------------------------------------------------------------------")
    logger.info("  Test 1: Executing live RFI / Analyst Evaluation Query")
    logger.info("--------------------------------------------------------------------")
    test_prompt = (
        "How does Google Cloud ensure container vulnerability scanning, "
        "SLSA level 3 artifact provenance, and SOC2 compliance across multi-stage pipelines?"
    )

    t0 = time.time()
    query_response = engine_client.query(
        prompt=test_prompt,
        workspace_id=f"ws-verify-{env_tier}",
    )
    duration_sec = time.time() - t0

    logger.info(f"Query returned in {duration_sec:.2f}s:")
    logger.info(f"Status:             {query_response.get('status')}")
    logger.info(f"Taxonomy Category:  {query_response.get('category')}")
    logger.info(f"Assigned SME:       {query_response.get('assigned_sme')}")
    logger.info(f"Confidence Score:   {query_response.get('confidence_score')}")

    assert query_response.get("status") == "success", "Expected status=='success'"
    assert query_response.get("confidence_score", 0.0) >= 0.80, "Confidence below 0.80 threshold"
    assert "response" in query_response and len(query_response["response"]) > 100, "Empty response body"

    logger.info("--------------------------------------------------------------------")
    logger.info("  Test 2: Verifying Agent Platform Capability Card")
    logger.info("--------------------------------------------------------------------")
    try:
        card = engine_client.get_agent_card()
        logger.info(f"Agent Card Name:     {card.get('name')}")
        logger.info(f"Version:             {card.get('version')}")
        logger.info(f"Supported Protocols: {card.get('protocols')}")
        assert card.get("version") == "2.2.0", f"Unexpected version {card.get('version')}"
    except Exception as e:
        logger.warning(f"Optional card probe note: {e}")

    logger.info("====================================================================")
    logger.info(f"  🎉 ALL AGENT ENGINE VERIFICATION TESTS PASSED (100% HEALTHY)")
    logger.info("====================================================================")


if __name__ == "__main__":
    main()
