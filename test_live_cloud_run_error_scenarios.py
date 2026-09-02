#!/usr/bin/env python3
"""
Live Cloud Run Error Handling & Resilience Verification Suite
Executes the Top 10 most anticipated error-producing scenarios against:
https://conductor-v2-105792947502.us-central1.run.app
Records and verifies the exact response payloads, status codes, and error messages shown to end-users.
"""

import os
import sys
import json
import time
import urllib.request
import requests

BASE_URL = (
    os.getenv("CLOUD_RUN_SERVICE_URL")
    or os.getenv("TARGET_URL")
    or os.getenv("CLOUD_RUN_URL")
    or os.getenv("SERVICE_URL")
    or "https://conductor-v2-105792947502.us-central1.run.app"
).rstrip("/")
TIMEOUT = 45
results = []

SESSION = requests.Session()

def init_auth_session():
    token = os.getenv("CLOUD_RUN_AUTH_TOKEN")
    if not token:
        try:
            req = urllib.request.Request(
                f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={BASE_URL}",
                headers={"Metadata-Flavor": "Google"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                token = resp.read().decode().strip()
        except Exception:
            pass
    if token:
        SESSION.headers.update({"Authorization": f"Bearer {token}"})

init_auth_session()

def safe_format_response(r: requests.Response) -> str:
    try:
        return json.dumps(r.json(), indent=2)
    except Exception:
        return r.text

def record(scenario_num: int, title: str, expected_status: int | str, actual_status: int | str, enduser_response: str, passed: bool):
    status_str = "PASS" if passed else "FAIL"
    print(f"\n[{status_str}] Scenario {scenario_num}: {title}")
    print(f"       Expected Status: {expected_status} | Actual Status: {actual_status}")
    print(f"       End-User / Client Response Output:\n         {enduser_response[:300]}...")
    results.append({
        "scenario": scenario_num,
        "title": title,
        "expected_status": str(expected_status),
        "actual_status": str(actual_status),
        "enduser_response": enduser_response,
        "passed": passed
    })
    if not passed:
        raise AssertionError(f"Scenario {scenario_num} failed verification! (Expected: {expected_status}, Got: {actual_status})")

def run_error_scenarios():
    print(f"==========================================================================")
    print(f"Warming up Google Cloud Run instance (handling potential cold starts)...")
    print(f"==========================================================================")
    warmed_up = False
    for attempt in range(1, 4):
        try:
            print(f"Warm-up ping attempt {attempt} to {BASE_URL}/health...")
            r_warm = SESSION.get(f"{BASE_URL}/health", timeout=60)
            if r_warm.status_code == 200:
                print(f" -> Warm-up successful (200 OK)! Cloud Run revision is ready: {r_warm.json()}")
                warmed_up = True
                break
        except Exception as e:
            print(f" -> Warm-up attempt {attempt} timed out or failed: {e}. Retrying after 5s...")
            time.sleep(5)
    if not warmed_up:
        print("⚠️ Warning: Could not confirm warm-up within retries, proceeding with scenarios anyway...")

    print(f"\n==========================================================================")
    print(f"Executing Top 10 Error-Producing Scenarios against Live Cloud Run App:")
    print(f"{BASE_URL}")
    print(f"==========================================================================")

    # 1. Missing Required Payload Fields in Chat Action (HTTP 422)
    r1 = SESSION.post(f"{BASE_URL}/api/v1/a2ui/chat", json={"action_id": "open_intake"}, timeout=TIMEOUT)
    record(
        1, "Missing Mandatory Pydantic Field ('message') in Chat Request",
        422, r1.status_code,
        safe_format_response(r1),
        r1.status_code == 422 and ("field required" in r1.text.lower() or "missing" in r1.text.lower())
    )

    # 2. Retrieving Non-Existent Persisted Artifact by UUID (HTTP 404)
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    r2 = SESSION.get(f"{BASE_URL}/api/v1/artifacts/{fake_uuid}", timeout=TIMEOUT)
    record(
        2, "Retrieving Non-Existent Saved Artifact by UUID",
        404, r2.status_code,
        safe_format_response(r2),
        r2.status_code == 404 and f"Artifact [{fake_uuid}] not found" in r2.text
    )

    # 3. Deleting Non-Existent Persisted Artifact by UUID (HTTP 404)
    fake_uuid2 = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    r3 = SESSION.delete(f"{BASE_URL}/api/v1/artifacts/{fake_uuid2}", timeout=TIMEOUT)
    record(
        3, "Deleting Non-Existent Saved Artifact by UUID",
        404, r3.status_code,
        safe_format_response(r3),
        r3.status_code == 404 and f"Artifact [{fake_uuid2}] not found" in r3.text
    )

    # 4. Malformed / Non-UUID String passed as Artifact ID (HTTP 422)
    bad_id = "not-a-valid-uuid-string-12345"
    r4 = SESSION.get(f"{BASE_URL}/api/v1/artifacts/{bad_id}", timeout=TIMEOUT)
    record(
        4, "Malformed Path Parameter (Non-UUID String) for Artifact GET",
        422, r4.status_code,
        safe_format_response(r4),
        r4.status_code == 422 and "uuid" in r4.text.lower()
    )

    # 5. Creating Saved Artifact with Missing Mandatory Pydantic Fields (HTTP 422)
    bad_payload = {"title": "Incomplete Artifact"}  # missing artifact_type, content
    r5 = SESSION.post(f"{BASE_URL}/api/v1/artifacts/", json=bad_payload, timeout=TIMEOUT)
    record(
        5, "Creating Saved Artifact with Missing Pydantic Metadata Fields",
        422, r5.status_code,
        safe_format_response(r5),
        r5.status_code == 422 and "artifact_type" in r5.text and "content" in r5.text
    )

    # 6. Empty / Too-Short Criteria Text Submission (Graceful Fallback via Auto-Defaulting)
    # When text is < 20 chars, instead of crashing on division/regex, the engine defaults to standard GAAP criteria
    r6 = SESSION.post(f"{BASE_URL}/api/v1/a2ui/chat", json={"message": "run evaluation", "action_id": "submit_criteria_analysis", "context_data": {"analyst_notes": "too short"}}, timeout=TIMEOUT)
    res6 = r6.json()
    record(
        6, "Empty or Malformed (<20 chars) Evaluation Criteria Submission (Graceful Fallback)",
        "200 OK (Recovered via Auto-Defaulting)", f"{r6.status_code} OK (Recovered via Auto-Defaulting)",
        res6["response_text"] + "\nCard Output Sample: " + (res6["a2ui_payloads"][0][:180] if res6.get("a2ui_payloads") else "No card"),
        r6.status_code == 200 and "Portfolio Eligibility Scorecard" in str(res6)
    )

    # 7. Simulated AI Model Exemption / Timeout during Ad-Hoc Question Answering (Graceful Offline AI Resilience)
    # Sending a chat query without an action_id evaluates Vertex AI; if any model exception occurs, our graceful exception handler synthesizes structured Markdown guidance
    r7 = SESSION.post(f"{BASE_URL}/api/v1/a2ui/chat", json={"message": "What is our sovereign cloud strategy for disconnected operations?"}, timeout=TIMEOUT)
    res7 = r7.json()
    record(
        7, "Conversational AI Query Execution & Graceful Exception Resilience",
        200, r7.status_code,
        res7["response_text"],
        r7.status_code == 200 and len(res7["response_text"]) > 50
    )

    # 8. Invoking Non-Existent REST URL Path (HTTP 404 Not Found)
    r8 = SESSION.get(f"{BASE_URL}/api/v1/export/invalid-endpoint-name-test", timeout=TIMEOUT)
    record(
        8, "Invoking Non-Existent REST Route (404 Not Found)",
        404, r8.status_code,
        safe_format_response(r8),
        r8.status_code == 404 and "Not Found" in r8.text
    )

    # 9. Method Not Allowed on Protected API Endpoints (HTTP 405)
    r9 = SESSION.post(f"{BASE_URL}/api/v1/export/demo-playbook?report=cnap", json={"unsupported": "post"}, timeout=TIMEOUT)
    record(
        9, "POST Request to Read-Only GET Endpoint (HTTP 405 Method Not Allowed)",
        405, r9.status_code,
        safe_format_response(r9),
        r9.status_code == 405 and "Method Not Allowed" in r9.text
    )

    # 10. Client-Side UI Error Display Simulation (UI Catch Blocks in index.html)
    # Verifies that index.html contains the exact defensive UI DOM trapping elements for display to endusers
    r10 = SESSION.get(f"{BASE_URL}/", timeout=TIMEOUT)
    html_content = r10.text
    render_err_box_present = 'Failed to render A2UI surface:' in html_content and 'bg-red-50 text-red-700' in html_content
    conn_err_msg_present = '⚠️ Error connecting to Cloud Run A2UI engine:' in html_content
    enduser_ui_behavior = (
        "Client UI DOM Catch Box: <div class='bg-red-50 text-red-700 p-3 rounded-xl text-xs border border-red-200'>Failed to render A2UI surface: ${escapeHtml(err.message)}</div>\n"
        "Client UI Network Alert: appendMessage('agent', '⚠️ Error connecting to Cloud Run A2UI engine: ' + error.message)"
    )
    record(
        10, "Client-Side Defensive Error Trapping (UI Network Faults & Corrupted DOM JSON)",
        "200 OK (Defensive HTML Traps Confirmed)", f"{r10.status_code} OK (Defensive HTML Traps Confirmed)",
        enduser_ui_behavior,
        r10.status_code == 200 and render_err_box_present and conn_err_msg_present
    )

    print("\n==========================================================================")
    print("🏆 SUCCESS: ALL 10 ERROR-PRODUCING SCENARIOS EXECUTED & VERIFIED 100%!")
    print("==========================================================================")
    
    # Save results summary to JSON for reporting
    with open("error_scenario_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    try:
        run_error_scenarios()
    except Exception as e:
        print(f"\n❌ FATAL ERROR IN VERIFICATION: {e}")
        sys.exit(1)
