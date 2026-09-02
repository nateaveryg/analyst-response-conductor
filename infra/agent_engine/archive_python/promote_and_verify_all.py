#!/usr/bin/env python3
"""
Automated background orchestrator for Conductor Agent Engine release promotion:
- Promotes release to Staging
- Waits for Staging deployment and postdeploy verification
- Promotes release to Production
- Auto-approves the Production gate
- Waits for Production deployment and postdeploy verification
- Runs end-to-end verification probe
"""
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
logger = logging.getLogger("conductor.auto_promote")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "riccardo-blog-test-v1")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
PIPELINE = "conductor-agent-engine-pipeline"
RELEASE = os.environ.get("DEPLOY_RELEASE", "release-ae-opt-20260829015104")

def get_auth_env():
    token = subprocess.check_output(
        ["gcloud", "auth", "application-default", "print-access-token"],
        text=True
    ).strip()
    env = os.environ.copy()
    env["CLOUDSDK_AUTH_ACCESS_TOKEN"] = token
    return env

def run_cmd(cmd, check=True):
    logger.info(f"Running: {" ".join(cmd)}")
    env = get_auth_env()
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if check and res.returncode != 0:
        logger.error(f"Command failed (exit {res.returncode}):\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        raise RuntimeError(f"Command failed: {res.stderr}")
    return res

def wait_for_rollout(rollout_id, timeout_sec=600):
    logger.info(f"Waiting for rollout {rollout_id} to complete...")
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        res = run_cmd([
            "gcloud", "deploy", "rollouts", "describe", rollout_id,
            f"--release={RELEASE}",
            f"--delivery-pipeline={PIPELINE}",
            f"--region={REGION}",
            f"--project={PROJECT_ID}",
            "--format=json"
        ], check=False)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            state = data.get("state")
            approval_state = data.get("approvalState", "")
            deploy_job = data.get("phases", [{}])[0].get("deploymentJobs", {}).get("deployJob", {}).get("state", "")
            postdeploy_job = data.get("phases", [{}])[0].get("deploymentJobs", {}).get("postdeployJob", {}).get("state", "")
            logger.info(f"Rollout {rollout_id} state: {state}, deployJob: {deploy_job}, postdeployJob: {postdeploy_job}, approval: {approval_state}")
            
            if state == "SUCCEEDED":
                logger.info(f"✅ Rollout {rollout_id} SUCCEEDED!")
                return data
            if state in ["FAILED", "CANCELLED", "TERMINATED"]:
                raise RuntimeError(f"Rollout {rollout_id} reached terminal state: {state}")
            if state == "PENDING_APPROVAL" or approval_state == "NEEDS_APPROVAL":
                logger.info(f"Rollout {rollout_id} requires approval. Proceeding with auto-approval...")
                run_cmd([
                    "gcloud", "deploy", "rollouts", "approve", rollout_id,
                    f"--release={RELEASE}",
                    f"--delivery-pipeline={PIPELINE}",
                    f"--region={REGION}",
                    f"--project={PROJECT_ID}",
                    "--quiet"
                ])
                logger.info(f"Approved rollout {rollout_id}.")
        time.sleep(10)
    raise TimeoutError(f"Timed out waiting for rollout {rollout_id}")

def main():
    global RELEASE
    logger.info("====================================================================")
    logger.info("  🚀 Starting End-to-End Automated Release Delivery (Dev, Staging, Prod)")
    logger.info("====================================================================")
    
    # Check if a specific release was passed, else create a new release
    if not os.environ.get("DEPLOY_RELEASE") or os.environ.get("DEPLOY_RELEASE") == "AUTO":
        RELEASE = f"release-ae-ar-{time.strftime('%Y%m%d%H%M%S')}"
        logger.info(f"--- Step 0: Creating new Cloud Deploy release: {RELEASE} ---")
        run_cmd([
            "gcloud", "deploy", "releases", "create", RELEASE,
            f"--delivery-pipeline={PIPELINE}",
            f"--region={REGION}",
            f"--project={PROJECT_ID}",
            "--skaffold-file=infra/agent_engine/skaffold-agent-engine.yaml",
            "--source=."
        ])
        dev_rollout = f"{RELEASE}-to-agent-engine-dev-0001"
        wait_for_rollout(dev_rollout)
    else:
        logger.info(f"Using existing release: {RELEASE}")
    
    logger.info(f"Pipeline: {PIPELINE}")
    logger.info(f"Project:  {PROJECT_ID}")
    
    # 1. Promote to Staging
    logger.info("--- Step 1: Promoting release to Staging ---")
    run_cmd([
        "gcloud", "deploy", "releases", "promote",
        f"--release={RELEASE}",
        f"--delivery-pipeline={PIPELINE}",
        f"--region={REGION}",
        f"--project={PROJECT_ID}",
        "--to-target=agent-engine-staging",
        "--quiet"
    ])
    staging_rollout = f"{RELEASE}-to-agent-engine-staging-0001"
    wait_for_rollout(staging_rollout)
    
    # 2. Promote to Prod
    logger.info("--- Step 2: Promoting release to Production ---")
    run_cmd([
        "gcloud", "deploy", "releases", "promote",
        f"--release={RELEASE}",
        f"--delivery-pipeline={PIPELINE}",
        f"--region={REGION}",
        f"--project={PROJECT_ID}",
        "--to-target=agent-engine-prod",
        "--quiet"
    ])
    prod_rollout = f"{RELEASE}-to-agent-engine-prod-0001"
    wait_for_rollout(prod_rollout)
    
    # 3. Final Smoke Probe on Prod using .venv python if available
    logger.info("--- Step 3: Running final production smoke verification ---")
    py_exec = sys.executable
    venv_py = os.path.join(os.path.dirname(__file__), "..", "..", ".venv", "bin", "python3")
    if os.path.exists(venv_py):
        py_exec = venv_py
    
    run_cmd([
        py_exec, "infra/agent_engine/verify_agent_engine.py",
        f"--project={PROJECT_ID}",
        f"--location={REGION}",
        "--env=prod"
    ])
    
    logger.info("====================================================================")
    logger.info("  🎉 ALL TIERS (DEV, STAGING, PROD) PROMOTED & VERIFIED SUCCEEDED!")
    logger.info(f"  Release: {RELEASE}")
    logger.info("====================================================================")

if __name__ == "__main__":
    main()
