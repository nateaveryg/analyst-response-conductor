#!/usr/bin/env python3
"""
Autonomous Multi-Stage Rollout Script for Conductor v3 Frontend Pipeline
Promotes releases through Development -> Staging -> Production (Canary 25% -> 50% -> 100% Stable)
with automatic approvals and health validations.
"""

import os
import sys
import time
import json
import subprocess
import google.auth
import google.auth.transport.requests

PIPELINE_NAME = "conductor-v3-frontend-pipeline"
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

def get_latest_release(pipeline_name):
    env = get_env()
    res = subprocess.run([
        "gcloud", "deploy", "releases", "list",
        f"--delivery-pipeline={pipeline_name}",
        f"--region={REGION}",
        f"--project={PROJECT_ID}",
        "--format=json"
    ], env=env, capture_output=True, text=True)
    if res.returncode == 0:
        releases = json.loads(res.stdout)
        if releases:
            releases.sort(key=lambda r: r.get("createTime", ""), reverse=True)
            rel_name = releases[0].get("name", "").split("/")[-1]
            print(f"Found latest release: {rel_name}")
            return rel_name
    raise RuntimeError(f"Could not find any releases for pipeline {pipeline_name}")

def wait_for_rollout(rollout_name, release_name, target_phase=None, timeout=600):
    print(f"Waiting for rollout {rollout_name} (target_phase={target_phase})...")
    start = time.time()
    env = get_env()
    while time.time() - start < timeout:
        res = subprocess.run([
            "gcloud", "deploy", "rollouts", "describe", rollout_name,
            f"--release={release_name}",
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
                        if phase_state in ("SUCCEEDED", "SKIPPED"):
                            return True
                        if phase_state in ("FAILED", "ABORTED"):
                            raise RuntimeError(f"Phase {target_phase} failed with state {phase_state}")
            if state == "SUCCEEDED":
                return True
            if state in ("FAILED", "ABORTED"):
                raise RuntimeError(f"Rollout failed with state {state}")
        time.sleep(10)
    raise TimeoutError(f"Timed out waiting for rollout {rollout_name}")

def main():
    release_name = sys.argv[1] if len(sys.argv) > 1 else get_latest_release(PIPELINE_NAME)
    print("==========================================================================")
    print(f"Autonomous Rollout: {PIPELINE_NAME} | Release: {release_name}")
    print("==========================================================================")

    # 1. Verify / Wait for Dev Rollout
    dev_rollout = f"{release_name}-to-dev-0001"
    print(f"\n[Step 1] Tracking Development Rollout ({dev_rollout})...")
    wait_for_rollout(dev_rollout, release_name)
    print(" -> Development Rollout SUCCEEDED!")

    # 2. Promote to Staging
    print(f"\n[Step 2] Promoting Release {release_name} to Staging...")
    env = get_env()
    res = run_gcloud([
        "deploy", "releases", "promote",
        f"--release={release_name}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--to-target=staging",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Failed to promote to staging: {res.stderr}")
        sys.exit(1)

    staging_rollout = f"{release_name}-to-staging-0001"
    wait_for_rollout(staging_rollout, release_name)
    print(" -> Staging Rollout SUCCEEDED!")

    # 3. Promote to Production
    print(f"\n[Step 3] Promoting Release {release_name} to Production...")
    env = get_env()
    res = run_gcloud([
        "deploy", "releases", "promote",
        f"--release={release_name}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--to-target=prod",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Failed to promote to prod: {res.stderr}")
        sys.exit(1)

    prod_rollout = f"{release_name}-to-prod-0001"

    # 4. Auto-Approve Production Rollout
    print("\n[Step 4] Auto-Approving Production Rollout Gate...")
    time.sleep(5)
    env = get_env()
    res = run_gcloud([
        "deploy", "rollouts", "approve", prod_rollout,
        f"--release={release_name}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Warning on approve: {res.stderr}")

    # 5. Progressive Canary: Phase 1 (25%)
    print("\n[Step 5] Waiting for Phase canary-25...")
    wait_for_rollout(prod_rollout, release_name, target_phase="canary-25")
    print(" -> Phase canary-25 SUCCEEDED!")

    # 6. Progressive Canary: Advance to Phase 2 (50%)
    print("\n[Step 6] Advancing to canary-50...")
    env = get_env()
    res = run_gcloud([
        "deploy", "rollouts", "advance", prod_rollout,
        f"--release={release_name}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--phase-id=canary-50",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Warning on advance canary-50: {res.stderr}")

    wait_for_rollout(prod_rollout, release_name, target_phase="canary-50")
    print(" -> Phase canary-50 SUCCEEDED!")

    # 7. Progressive Canary: Advance to Stable (100%)
    print("\n[Step 7] Advancing to stable (100% full cutover)...")
    env = get_env()
    res = run_gcloud([
        "deploy", "rollouts", "advance", prod_rollout,
        f"--release={release_name}",
        f"--delivery-pipeline={PIPELINE_NAME}",
        "--phase-id=stable",
        "--quiet"
    ], env)
    if res.returncode != 0:
        print(f"Warning on advance stable: {res.stderr}")

    wait_for_rollout(prod_rollout, release_name, target_phase="stable")
    print(" -> Phase stable (100%) SUCCEEDED!")

    print("\n==========================================================================")
    print("ALL ENVIRONMENTS (DEV, STAGING, PROD) SUCCESSFULLY ROLLED OUT!")
    print("==========================================================================")

if __name__ == "__main__":
    main()
