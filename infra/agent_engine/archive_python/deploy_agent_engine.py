#!/usr/bin/env python3
"""
Vertex AI Agent Engine Continuous Delivery Deployer.
Used by Cloud Build and Cloud Deploy pipelines to package, stage, provision,
or update Analyst Response Agent (Conductor v2) Reasoning Engine instances across tiers (Dev, Staging, Prod).
Fulfills Cloud Deploy Custom Target deploy contract by uploading artifacts and results.json.
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import time
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("conductor.deploy_agent_engine")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy Conductor v2 to Vertex AI Agent Engine.")
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
        "--gcs-bucket",
        default=os.environ.get("STAGING_BUCKET", "gs://riccardo-blog-test-v1-agent-engine"),
        help="GCS Staging Bucket URI for Agent Engine source packaging",
    )
    parser.add_argument(
        "--display-name",
        default=None,
        help="Custom display name override for Vertex AI Agent Engine",
    )
    parser.add_argument(
        "--requirements-file",
        default=os.path.join(os.path.dirname(__file__), "requirements.txt"),
        help="Path to requirements.txt for the remote Agent Engine environment",
    )
    parser.add_argument(
        "--output-file",
        default=os.path.join(os.path.dirname(__file__), "deployed_engine.json"),
        help="Path to write deployment output metadata JSON",
    )
    parser.add_argument(
        "--output-gcs-path",
        default=os.environ.get("CLOUD_DEPLOY_OUTPUT_GCS_PATH", ""),
        help="Cloud Storage directory provided by Cloud Deploy for deploy artifacts and results.json",
    )
    parser.add_argument(
        "--resource-name",
        default=os.environ.get("AGENT_ENGINE_RESOURCE", None),
        help="Explicit Vertex AI Agent Engine resource name to update in-place",
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force full recreation of the Agent Engine even if an existing instance is found",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate packaging and exit without creating remote cloud resource",
    )
    return parser.parse_args()


def load_requirements(req_path: str) -> list[str]:
    if not os.path.exists(req_path):
        base_reqs = ["google-cloud-aiplatform>=1.70.0", "google-genai>=0.1.0", "pydantic>=2.0.0", "typing-extensions>=4.9.0"]
    else:
        with open(req_path, "r", encoding="utf-8") as f:
            base_reqs = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    
    ar_repo = os.environ.get("ARTIFACT_REGISTRY_PYPI_URL", "https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/")
    if ar_repo and not any("index-url" in r for r in base_reqs):
        base_reqs.insert(0, f"--extra-index-url {ar_repo}")
    return base_reqs


def upload_file_to_gcs(local_file: str, gcs_destination: str) -> None:
    """Uploads a file to Google Cloud Storage using SDK or gcloud storage CLI."""
    try:
        from google.cloud import storage
        if gcs_destination.startswith("gs://"):
            parts = gcs_destination[5:].split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_file)
            logger.info(f"Uploaded via Storage SDK: {local_file} -> {gcs_destination}")
            return
    except Exception as e:
        logger.debug(f"Storage SDK upload fallback: {e}")

    cmd = ["gcloud", "storage", "cp", local_file, gcs_destination]
    logger.info(f"Executing GCS copy: {' '.join(cmd)}")
    subprocess.check_call(cmd)


def main():
    args = parse_args()

    # Determine environment tier
    env_tier = args.env
    target_name = os.environ.get("CLOUD_DEPLOY_TARGET", "")
    if "staging" in target_name:
        env_tier = "staging"
    elif "prod" in target_name:
        env_tier = "prod"

    tier_name = env_tier.capitalize()
    target_display_name = args.display_name or f"Analyst Response Agent (Agent Engine {tier_name})"
    description = (
        f"Autonomous multi-agent enterprise response platform for analyst evaluations "
        f"(Conductor v2 - {tier_name} Tier, Managed Vertex AI Agent Engine Runtime)."
    )

    logger.info("====================================================================")
    logger.info("  🚀 Conductor v2 -> Vertex AI Agent Engine Deployment Pipeline")
    logger.info("====================================================================")
    logger.info(f"Project:         {args.project}")
    logger.info(f"Location:        {args.location}")
    logger.info(f"Target Tier:     {env_tier.upper()}")
    logger.info(f"Display Name:    {target_display_name}")
    logger.info(f"Staging Bucket:  {args.gcs_bucket}")
    logger.info(f"Output GCS Path: {args.output_gcs_path}")

    requirements = load_requirements(args.requirements_file)
    logger.info(f"Parsed {len(requirements)} runtime dependencies: {requirements}")

    # Ensure repository root is on sys.path
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    try:
        from app.agent_engine.conductor_engine import ConductorAgentEngine
    except ImportError as e:
        logger.error(f"Failed to import ConductorAgentEngine from {repo_root}: {e}")
        sys.exit(1)

    agent_engine_instance = ConductorAgentEngine(
        model_name="gemini-2.5-flash",
        project=args.project,
        location=args.location,
    )
    agent_engine_instance.set_up()
    agent_card = agent_engine_instance.get_agent_card()
    logger.info(f"Agent instance validated successfully: {agent_card['name']} (v{agent_card['version']})")

    if args.dry_run:
        logger.info("Dry-run mode active: validation succeeded. Exiting without remote deploy.")
        return

    import vertexai
    from vertexai import agent_engines

    gcs_staging_bucket = args.gcs_bucket if args.gcs_bucket.startswith("gs://") else f"gs://{args.gcs_bucket}"
    gcs_staging_bucket = gcs_staging_bucket.rstrip("/")
    vertexai.init(
        project=args.project,
        location=args.location,
        staging_bucket=gcs_staging_bucket,
    )

    existing_engine = None
    if not args.force_recreate:
        # 1. Try explicit resource name if provided via arg or env
        if args.resource_name:
            try:
                existing_engine = agent_engines.get(args.resource_name)
                logger.info(f"Targeting explicit Agent Engine resource: {existing_engine.resource_name}")
            except Exception as e:
                logger.warning(f"Could not retrieve explicit resource '{args.resource_name}': {e}")

        # 2. Try looking up in local deployed_engine.json if tier matches
        if not existing_engine and os.path.exists(args.output_file):
            try:
                with open(args.output_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    tier_resource = cached_data.get("tiers", {}).get(env_tier) or (
                        cached_data.get("resource_name") if cached_data.get("env") == env_tier else None
                    )
                    if tier_resource:
                        existing_engine = agent_engines.get(tier_resource)
                        logger.info(f"Found cached Agent Engine for tier '{env_tier}': {existing_engine.resource_name}")
            except Exception as e:
                logger.debug(f"Cached engine resolution failed: {e}")

        # 3. Dynamic lookup across Vertex AI by display name convention
        if not existing_engine:
            logger.info("Scanning existing Vertex AI Agent Engines...")
            try:
                for engine in agent_engines.list():
                    if engine.display_name == target_display_name:
                        existing_engine = engine
                        logger.info(f"Found existing matching Agent Engine by display name: {engine.resource_name}")
                        break
            except Exception as e:
                logger.warning(f"Error querying existing Agent Engines: {e}")

    env_vars = {
        "ENVIRONMENT": env_tier,
        "PROJECT_ID": args.project,
        "LOCATION": args.location,
        "CONDUCTOR_VERSION": agent_engine_instance.VERSION,
    }

    os.chdir(repo_root)
    extra_packages = ["app"] if os.path.exists(os.path.join(repo_root, "app")) else []
    logger.info(f"Repository root set to {repo_root} (cwd: {os.getcwd()}), extra_packages: {extra_packages}")

    deployed_engine = None
    update_mode = "CLEAN_CREATE"
    if existing_engine and not args.force_recreate:
        logger.info(f"⚡ Performing fast in-place update on resource: {existing_engine.resource_name}...")
        t_update_start = time.time()
        try:
            deployed_engine = existing_engine.update(
                agent_engine=agent_engine_instance,
                requirements=requirements,
                display_name=target_display_name,
                description=description,
                extra_packages=extra_packages,
                env_vars=env_vars,
                gcs_dir_name=f"conductor_agent_engine_{env_tier}",
            )
            update_duration = time.time() - t_update_start
            update_mode = "IN_PLACE"
            logger.info(f"✅ In-place update completed successfully in {update_duration:.2f}s!")
        except Exception as e:
            logger.warning(f"In-place update failed ({e}). Proceeding with clean create...")

    if not deployed_engine:
        logger.info(f"Provisioning new Vertex AI Agent Engine for tier '{env_tier}' (clean create)...")
        t_create_start = time.time()
        deployed_engine = agent_engines.create(
            agent_engine=agent_engine_instance,
            requirements=requirements,
            display_name=target_display_name,
            description=description,
            extra_packages=extra_packages,
            env_vars=env_vars,
            gcs_dir_name=f"conductor_agent_engine_{env_tier}",
        )
        create_duration = time.time() - t_create_start
        logger.info(f"Clean create completed in {create_duration:.2f}s.")

    resource_name = getattr(deployed_engine, "resource_name", str(deployed_engine))
    logger.info("====================================================================")
    logger.info(f"  ✅ Deployed Vertex AI Agent Engine successfully! Mode: {update_mode}")
    logger.info(f"  Resource Name: {resource_name}")
    logger.info("====================================================================")

    output_data = {
        "status": "SUCCESS",
        "resource_name": resource_name,
        "display_name": target_display_name,
        "env": env_tier,
        "project": args.project,
        "location": args.location,
        "version": agent_engine_instance.VERSION,
        "update_mode": update_mode,
        "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    logger.info(f"Deployment manifest persisted to: {args.output_file}")

    # Build Cloud Deploy results.json contract
    out_dir = os.path.dirname(os.path.abspath(args.output_file))
    local_results_file = os.path.join(out_dir, "results.json")

    remote_artifact_path = f"{args.output_gcs_path.rstrip('/')}/deployed_engine.json" if args.output_gcs_path else args.output_file
    deploy_results = {
        "resultStatus": "SUCCEEDED",
        "artifactFiles": [remote_artifact_path],
        "failureMessage": "",
        "metadata": {
            "resourceName": resource_name,
            "displayName": target_display_name,
            "env": env_tier,
            "version": agent_engine_instance.VERSION,
            "updateMode": update_mode,
        },
    }

    with open(local_results_file, "w", encoding="utf-8") as f:
        json.dump(deploy_results, f, indent=2)
    logger.info(f"Cloud Deploy results file persisted to: {local_results_file}")

    if args.output_gcs_path:
        out_gcs = args.output_gcs_path.rstrip("/")
        logger.info(f"Uploading deploy artifacts to Cloud Deploy storage: {out_gcs}...")
        upload_file_to_gcs(args.output_file, f"{out_gcs}/deployed_engine.json")
        upload_file_to_gcs(local_results_file, f"{out_gcs}/results.json")
        logger.info("Cloud Deploy results.json successfully uploaded to GCS.")


if __name__ == "__main__":
    main()
