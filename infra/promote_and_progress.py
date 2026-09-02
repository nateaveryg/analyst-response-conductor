#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import google.auth
import google.auth.transport.requests

RELEASE_NAME = "release-v3-5cea6459-63bb-42f6-ab84-06e86973ecc8"
PIPELINE_NAME = "conductor-v3-pipeline"
REGION = "us-central1"
PROJECT_ID = "riccardo-blog-test-v1"

def get_env():
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    env = os.environ.copy()
    env["CLOUDSDK_AUTH_ACCESS_TOKEN"] = creds.token
    return env

def run_gcloud(args, env=None):
    if env is None:
        env = get_env()
    cmd = ["gcloud"] + args + [
        f"--project={PROJECT_ID}",
        f"--region={REGION}",
    ]
    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Command stderr: {res.stderr}")
    return res

def wait_for_rollout(rollout_name, target_phase=None, timeout=600):
    print(f"Waiting for rollout {rollout_name} (target_phase={target_phase})...")
    start = time.time()
    env = get_env()
    while time.time() - start < timeout:
        res = subprocess.run([
            "gcloud", "deploy", "rollouts", "describe", rollout_name,
            f"--release={RELEASE_NAME}",
            f"--delivery-pipeline={PIPELINE_NAME}",
            f"--region={REGION}",
            f"--project={PROJECT_ID}",
            "--format=json"
        ], env=env, capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            state = data.get("state")
            phases = data.get("phases", [])
            print(f"Rollout state: {state}")
            if target_phase:
                for phase in phases:
                    if phase.get("id") == target_phase:
                        phase_state = phase.get("state")
                        print(f"Phase {target_phase} state: {phase_state}")
                        if phase_state == "SUCCEEDED":
                            return True
                        if phase_state in ("FAILED", "ABORTED"):
                            raise RuntimeError(f"Phase {target_phase} failed with state {phase_state}")
            else:
                if state == "SUCCEEDED":
                    return True
                if state in ("FAILED", "ABORTED"):
                    raise RuntimeError(f"Rollout failed with state {state}")
        time.sleep(10)
    raise TimeoutError(f"Timed out waiting for rollout {rollout_name}")

def main():
    env = get_env()
    print("==========================================================================")
    print(f"Promoting Release: {RELEASE_NAME} to Staging")
    print("==========================================================================")
    res = run_gcloud([
        "deploy", "releases", "promote",
        f"--release={RELEASE_NAME}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--to-target=staging",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Failed to promote to staging: {res.stderr}")
        sys.exit(1)
    
    staging_rollout = f"{RELEASE_NAME}-to-staging-0001"
    wait_for_rollout(staging_rollout)
    print("✅ Staging Rollout SUCCEEDED!")

    print("==========================================================================")
    print(f"Promoting Release: {RELEASE_NAME} to Production")
    print("==========================================================================")
    res = run_gcloud([
        "deploy", "releases", "promote",
        f"--release={RELEASE_NAME}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--to-target=prod",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Failed to promote to prod: {res.stderr}")
        sys.exit(1)

    prod_rollout = f"{RELEASE_NAME}-to-prod-0001"

    print("Approving Prod Rollout...")
    time.sleep(5)
    env = get_env()
    res = run_gcloud([
        "deploy", "rollouts", "approve", prod_rollout,
        f"--release={RELEASE_NAME}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Warning on approve: {res.stderr}")

    print("Waiting for Phase canary-25...")
    wait_for_rollout(prod_rollout, target_phase="canary-25")
    print("✅ canary-25 SUCCEEDED!")

    print("Advancing to canary-50...")
    env = get_env()
    res = run_gcloud([
        "deploy", "rollouts", "advance", prod_rollout,
        f"--release={RELEASE_NAME}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--phase-id=canary-50",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Warning on advance canary-50: {res.stderr}")

    print("Waiting for Phase canary-50...")
    wait_for_rollout(prod_rollout, target_phase="canary-50")
    print("✅ canary-50 SUCCEEDED!")

    print("Advancing to stable (100%)...")
    env = get_env()
    res = run_gcloud([
        "deploy", "rollouts", "advance", prod_rollout,
        f"--release={RELEASE_NAME}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--phase-id=stable",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Warning on advance stable: {res.stderr}")

    print("Waiting for Phase stable (100%)...")
    wait_for_rollout(prod_rollout, target_phase="stable")
    print("✅ stable (100%) SUCCEEDED!")

    print("==========================================================================")
    print("🏆 ALL ENVIRONMENTS (DEV, STAGING, PROD) SUCCESSFULLY ROLLED OUT!")
    print("==========================================================================")

if __name__ == "__main__":
    main()
