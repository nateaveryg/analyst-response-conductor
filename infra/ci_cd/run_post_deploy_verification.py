#!/usr/bin/env python3
"""
Google Cloud Deploy Post-Deploy Verification Hook Runner
Executes comprehensive synthetic and live integration tests against the newly deployed Cloud Run target URL.
Compatible with Cloud Deploy customActions and Cloud Build verification steps.
"""

import os
import sys
import subprocess
def main():
    target_url = (
        os.getenv("CLOUD_RUN_SERVICE_URL")
        or os.getenv("CLOUD_RUN_URL")
        or os.getenv("TARGET_URL")
        or os.getenv("SERVICE_URL")
    )
    if not target_url and len(sys.argv) > 1:
        target_url = sys.argv[1]

    if not target_url:
        print("[WARN] No CLOUD_RUN_SERVICE_URL, CLOUD_RUN_URL, or TARGET_URL provided. Defaulting to production benchmark URL.")
        target_url = "https://conductor-v2-105792947502.us-central1.run.app"

    print(f"==========================================================================")
    print(f"🚀 Cloud Deploy Post-Deploy Verification Hook Starting")
    print(f"🎯 Target URL: {target_url}")
    print(f"==========================================================================")

    env = os.environ.copy()
    env["TARGET_URL"] = target_url
    env["CLOUD_RUN_URL"] = target_url
    env["CLOUD_RUN_SERVICE_URL"] = target_url

    # 1. Run Standard Workflow & Exploratory E2E Tests
    print("\n--- [Step 1/2] Running Live Full E2E Workflow Test ---")
    ret1 = subprocess.run([sys.executable, "test_live_cloud_run_full_e2e.py"], env=env)
    if ret1.returncode != 0:
        print("[FAIL] Post-deploy full E2E workflow verification failed!")
        sys.exit(ret1.returncode)

    # 2. Run Defensive Error Interception Test
    print("\n--- [Step 2/2] Running Live Error Handling & Resilience Test ---")
    ret2 = subprocess.run([sys.executable, "test_live_cloud_run_error_scenarios.py"], env=env)
    if ret2.returncode != 0:
        print("[FAIL] Post-deploy error scenario resilience verification failed!")
        sys.exit(ret2.returncode)

    print("\n==========================================================================")
    print("✅ All Cloud Deploy Post-Deploy Verification Checks Passed (100%)")
    print("==========================================================================")

if __name__ == "__main__":
    main()
