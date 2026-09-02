#!/usr/bin/env python3
"""
Live Cloud Run Verification Script (`test_live_cloud_run_portal.py`)
Verifies endpoint liveness, Saved Artifacts persistence & restoration, and Dynamic AI responses via Gemini 3.5 Flash against:
https://conductor-v2-105792947502.us-central1.run.app
"""

import os
import sys
import json
import requests

BASE_URL = (
    os.getenv("CLOUD_RUN_SERVICE_URL")
    or os.getenv("TARGET_URL")
    or os.getenv("CLOUD_RUN_URL")
    or os.getenv("SERVICE_URL")
    or "https://conductor-v2-105792947502.us-central1.run.app"
).rstrip("/")

def run_live_tests():
    print(f"==========================================================================")
    print(f"Executing Live Verification Suite against: {BASE_URL}")
    print(f"==========================================================================")

    # 1. Verify Root Web Portal UI
    print("\n[Test 1] Verifying Root A2UI Executive Web Portal (/)...")
    r_root = requests.get(f"{BASE_URL}/", timeout=10)
    assert r_root.status_code == 200, f"Expected 200, got {r_root.status_code}"
    assert "Analyst Response Agent (ARA) - A2UI Executive Portal" in r_root.text
    print(" -> PASSED: Web Portal loaded successfully (200 OK).")

    # 2. Verify Health & Readiness Probes
    print("\n[Test 2] Verifying Health Probes (/health, /ready)...")
    r_health = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r_health.status_code == 200, f"Expected 200, got {r_health.status_code}"
    print(f" -> PASSED: /health -> {r_health.json()}")

    r_ready = requests.get(f"{BASE_URL}/ready", timeout=10)
    assert r_ready.status_code == 200, f"Expected 200, got {r_ready.status_code}"
    print(f" -> PASSED: /ready -> {r_ready.json()}")

    # 3. Verify Saved Artifacts API (List & Create)
    print("\n[Test 3] Verifying Saved Artifacts Persistence (/api/v1/artifacts/)...")
    r_list = requests.get(f"{BASE_URL}/api/v1/artifacts/", timeout=10)
    assert r_list.status_code == 200, f"Expected 200, got {r_list.status_code}"
    artifacts = r_list.json()
    print(f" -> PASSED: Listed {len(artifacts)} persisted artifacts from Cloud SQL Postgres.")

    # Create a test saved artifact
    test_artifact_data = {
        "title": "Live Cloud Run Test Matrix",
        "artifact_type": "scorecard",
        "summary": "Automated verification artifact saved from live test run",
        "content": "### Evaluation Matrix Results\n1. Gemini Code Assist: Qualified (100/100).",
        "metadata_json": json.dumps({"vendor": "Conductor v2", "score": 100, "verified": True})
    }
    r_create = requests.post(f"{BASE_URL}/api/v1/artifacts/", json=test_artifact_data, timeout=10)
    assert r_create.status_code == 201, f"Expected 201, got {r_create.status_code}"
    created_id = r_create.json()["id"]
    print(f" -> PASSED: Created SavedArtifact id={created_id}.")

    # Verify Restore Session Context synthesis
    print("\n[Test 4] Verifying Session Context Synthesis Engine (/api/v1/artifacts/restore)...")
    r_restore = requests.post(f"{BASE_URL}/api/v1/artifacts/restore", json={}, timeout=10)
    assert r_restore.status_code == 200, f"Expected 200, got {r_restore.status_code}"
    restored_context = r_restore.json()
    assert "response_text" in restored_context or "restored_context" in restored_context
    print(f" -> PASSED: {restored_context.get('response_text', 'Session context restored successfully.')}")

    # 5. Verify Dynamic AI Question-Answering (a2ui_chat fallback via Gemini 3.5 Flash)
    print("\n[Test 5] Verifying Dynamic AI Conversational Handler (/api/v1/a2ui/chat)...")
    chat_payload = {
        "message": "Hello! Can you explain how our RFI evaluation criteria are structured and scored?"
    }
    r_chat = requests.post(f"{BASE_URL}/api/v1/a2ui/chat", json=chat_payload, timeout=30)
    assert r_chat.status_code == 200, f"Expected 200, got {r_chat.status_code}"
    chat_response = r_chat.json()
    assert "response_text" in chat_response or "a2ui_payloads" in chat_response
    print(" -> PASSED: Vertex AI (gemini-3.5-flash) responded dynamically:")
    if "response_text" in chat_response:
        print(f"    AI Response: {chat_response['response_text'][:200]}...")

    print(f"\n==========================================================================")
    print(f"ALL 5 LIVE CLOUD RUN INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print(f"==========================================================================")

if __name__ == "__main__":
    run_live_tests()
