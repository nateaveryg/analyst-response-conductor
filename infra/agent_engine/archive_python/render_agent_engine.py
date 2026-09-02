#!/usr/bin/env python3
"""
Custom Target Renderer for Vertex AI Agent Engine in Cloud Deploy.
Fulfills the Cloud Deploy Custom Render contract by generating the target manifest
and writing/uploading results.json to CLOUD_DEPLOY_OUTPUT_GCS_PATH.
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("conductor.render_agent_engine")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Cloud Deploy artifacts for Agent Engine target.")
    parser.add_argument(
        "--target",
        default=os.environ.get("CLOUD_DEPLOY_TARGET", "agent-engine-dev"),
        help="Cloud Deploy target name",
    )
    parser.add_argument(
        "--pipeline",
        default=os.environ.get("CLOUD_DEPLOY_DELIVERY_PIPELINE", "conductor-agent-engine-pipeline"),
        help="Cloud Deploy delivery pipeline name",
    )
    parser.add_argument(
        "--release",
        default=os.environ.get("CLOUD_DEPLOY_RELEASE", "unknown-release"),
        help="Cloud Deploy release name",
    )
    parser.add_argument(
        "--output-gcs-path",
        default=os.environ.get("CLOUD_DEPLOY_OUTPUT_GCS_PATH", ""),
        help="GCS output path provided by Cloud Deploy",
    )
    parser.add_argument(
        "--local-dir",
        default="/tmp/rendered_artifacts",
        help="Local directory for temporary artifact staging",
    )
    return parser.parse_args()


def upload_file_to_gcs(local_file: str, gcs_destination: str) -> None:
    """Uploads a file to Google Cloud Storage using google-cloud-storage or gcloud storage."""
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

    logger.info("====================================================================")
    logger.info("  ⚙️  Rendering Vertex AI Agent Engine Target")
    logger.info("====================================================================")
    logger.info(f"Target:          {args.target}")
    logger.info(f"Pipeline:        {args.pipeline}")
    logger.info(f"Release:         {args.release}")
    logger.info(f"Output GCS Path: {args.output_gcs_path}")

    target_env = "dev"
    if "staging" in args.target:
        target_env = "staging"
    elif "prod" in args.target:
        target_env = "prod"

    os.makedirs(args.local_dir, exist_ok=True)
    manifest_path = os.path.join(args.local_dir, "manifest.json")
    results_path = os.path.join(args.local_dir, "results.json")

    manifest_payload = {
        "kind": "VertexAIAgentEngineManifest",
        "apiVersion": "conductor.google.com/v2",
        "targetEnvironment": target_env,
        "targetName": args.target,
        "pipeline": args.pipeline,
        "release": args.release,
        "version": "2.2.0",
        "runtime": "Vertex AI Agent Engine (Reasoning Engine)",
        "model": "gemini-2.5-flash",
        "region": "us-central1",
        "renderedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)
    logger.info(f"Created local manifest at: {manifest_path}")

    # Build Cloud Deploy Custom Render Results Specification
    remote_manifest_uri = f"{args.output_gcs_path.rstrip('/')}/manifest.json" if args.output_gcs_path else manifest_path
    results_payload = {
        "resultStatus": "SUCCEEDED",
        "manifestFile": remote_manifest_uri,
        "failureMessage": "",
        "metadata": {
            "target": args.target,
            "environment": target_env,
            "runtime": "agent-engine",
            "version": "2.2.0",
            "pipeline": args.pipeline,
        },
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)
    logger.info(f"Created local results.json at: {results_path}")

    # Upload to Cloud Deploy GCS destination if provided
    if args.output_gcs_path:
        out_gcs = args.output_gcs_path.rstrip("/")
        logger.info(f"Uploading render artifacts to Cloud Deploy storage: {out_gcs}...")
        upload_file_to_gcs(manifest_path, f"{out_gcs}/manifest.json")
        upload_file_to_gcs(results_path, f"{out_gcs}/results.json")
        logger.info("Custom render artifacts uploaded successfully.")

    logger.info("====================================================================")
    logger.info("  ✅ Agent Engine Custom Render Completed Successfully")
    logger.info("====================================================================")


if __name__ == "__main__":
    main()
