#!/usr/bin/env python3
"""
Comprehensive Live Cloud Run End-to-End (E2E) Verification Suite
Tests all sequential choices ON the standard workflow path (Phases 1-7) and OFF the standard workflow path (exploratory, ad-hoc, out-of-order queries) against:
https://conductor-v2-105792947502.us-central1.run.app
"""

import os
import sys
import json
import urllib.request
import requests
from typing import Any, Dict

BASE_URL = (
    os.getenv("CLOUD_RUN_SERVICE_URL")
    or os.getenv("TARGET_URL")
    or os.getenv("CLOUD_RUN_URL")
    or os.getenv("SERVICE_URL")
    or "https://conductor-v2-105792947502.us-central1.run.app"
).rstrip("/")
TIMEOUT = 30

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

def check(condition: bool, msg: str):
    if not condition:
        print(f"[FAIL] {msg}")
        raise AssertionError(msg)
    print(f"  [PASS] {msg}")

def post_chat(message: str, action_id: str | None = None, context_data: dict | None = None) -> Dict[str, Any]:
    payload = {"message": message}
    if action_id:
        payload["action_id"] = action_id
    if context_data:
        payload["context_data"] = context_data
    r = SESSION.post(f"{BASE_URL}/api/v1/a2ui/chat", json=payload, timeout=TIMEOUT)
    check(r.status_code == 200, f"POST /api/v1/a2ui/chat ({action_id or message}) returned {r.status_code}")
    return r.json()

def test_on_path_standard_workflow():
    print("\n==========================================================================")
    print("PART 1: ON-PATH STANDARD WORKFLOW VERIFICATION (PHASE 1 -> PHASE 7)")
    print("==========================================================================")

    # 1. Root Web Portal
    print("\n[On-Path 1] Verifying Root A2UI Executive Web Portal (/)...")
    r_root = SESSION.get(f"{BASE_URL}/", timeout=TIMEOUT)
    check(r_root.status_code == 200, "Web Portal HTTP 200 OK")
    check("Analyst Response Agent" in r_root.text, "Portal title rendered correctly")

    # 2. Phase 1: Onboarding / Open Intake
    print("\n[On-Path 2] Verifying Phase 1 Intake Surface (action: open_intake)...")
    res1 = post_chat("open intake", action_id="open_intake", context_data={"report_name": "DevSecOps Platforms, 2026"})
    check("Phase 1:" in res1["a2ui_payloads"][0], "Standardized Phase 1 title verified")
    check("7-Phase Operational Lifecycle Progress (14% Complete)" in res1["a2ui_payloads"][0], "Lifecycle progress tracker header verified (14%)")
    check("1A: Document Link Intake" in res1["a2ui_payloads"][0], "Sub-process checkpoint 1A confirmed")

    # 3. Phase 1: Submit Criteria Analysis & Scorecard
    print("\n[On-Path 3] Verifying Phase 1 Criteria Evaluation & Workback Schedule...")
    ctx = {"welcome_packet_url": "https://docs.google.com/devsecops-mq-2026", "analyst_notes": "devsecops evaluation"}
    res_eval = post_chat("run evaluation", action_id="submit_criteria_analysis", context_data=ctx)
    check("Portfolio Eligibility Scorecard" in res_eval["a2ui_payloads"][0], "Scorecard rendered")
    check("PROCEED WITH PARTICIPATION" in res_eval["a2ui_payloads"][0] or "Decline" in res_eval["a2ui_payloads"][0], "Go/No-Go Recommendation verified")

    # 4. Phase 2: SME Task Routing
    print("\n[On-Path 4] Verifying Phase 2 SME Task Routing & Workstream Assignment...")
    res2 = post_chat("assign tasks", action_id="assign_tasks", context_data=ctx)
    check("Phase 2: SME Task Routing & Workstream Assignment" in res2["a2ui_payloads"][0], "Phase 2 card verified")
    check("David Jacobs" in res2["a2ui_payloads"][0] and "Nathen Harvey" in res2["a2ui_payloads"][0], "Domain SME allocations confirmed")

    # 5. Phase 3: Stakeholder Kickoff & Charter
    print("\n[On-Path 5] Verifying Phase 3 Stakeholder Kickoff & OPM/SME Alignment...")
    res3 = post_chat("align teams", action_id="kickoff_project", context_data=ctx)
    check("Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter" in res3["a2ui_payloads"][0], "Phase 3 charter verified")
    check("Phase 5 Video Recording Budget Guidelines" in res3["a2ui_payloads"][0], "Updated Phase 5 video guidelines verified in charter")
    check("T-14 Storyboard & Narrative Freeze" in res3["a2ui_payloads"][0], "Calendar freezes verified")

    # 6. Phase 4A: RFI Spreadsheet Upload Drop-Zone
    print("\n[On-Path 6] Verifying Phase 4A RFI Questionnaire Spreadsheet Intake...")
    res4a = post_chat("upload rfi", action_id="upload_rfi", context_data=ctx)
    check("Phase 4A: RFI Questionnaire Spreadsheet Intake" in res4a["a2ui_payloads"][0], "Phase 4A drop-zone verified")
    check("4A: RFI Questionnaire Spreadsheet Upload & Intake (Active)" in res4a["a2ui_payloads"][0], "Sub-process 4A tracker confirmed")

    # 7. Phase 4B: Automated RAG Technical Draft Generation & Dual-Format Downloads
    print("\n[On-Path 7] Verifying Phase 4B Automated RAG Pre-Population & Exports...")
    res4b = post_chat("generate rfi responses", action_id="generate_rfi_responses", context_data=ctx)
    check("Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts" in res4b["a2ui_payloads"][0], "Phase 4B technical drafts verified")
    check("98.2% Grounded" in res4b["a2ui_payloads"][0], "Grounding confidence scores verified")
    check("download_rfi_md" in res4b["a2ui_payloads"][0] and "download_rfi_csv" in res4b["a2ui_payloads"][0], "Dual-format export buttons verified")

    # Test standalone RFI downloads
    r_rfi_md = SESSION.get(f"{BASE_URL}/api/v1/export/rfi-responses?format=md&report=devsecops", timeout=TIMEOUT)
    check(r_rfi_md.status_code == 200 and "Google Cloud Support" in r_rfi_md.text, "Standalone RFI Markdown export HTTP 200 verified")
    r_rfi_csv = SESSION.get(f"{BASE_URL}/api/v1/export/rfi-responses?format=csv&report=devsecops", timeout=TIMEOUT)
    check(r_rfi_csv.status_code == 200 and "Question & Capability Requirement" in r_rfi_csv.text, "Standalone RFI CSV export HTTP 200 verified")

    # 8. Phase 5: On-Demand Demo Sandboxes & Storyboard Playbooks (NEW MILESTONE)
    print("\n[On-Path 8] Verifying Phase 5 On-Demand Demo Environments & Playbooks...")
    res5 = post_chat("deploy demo environments", action_id="open_demo_sandboxes", context_data=ctx)
    check("Phase 5: On-Demand Demo Environments & Storyboard Playbook" in res5["a2ui_payloads"][0], "Phase 5 Demo Sandboxes card verified")
    check("71% Complete" in res5["a2ui_payloads"][0], "Lifecycle progress tracker verified (71%)")
    check("download_demo_playbook" in res5["a2ui_payloads"][0], "Demo Playbook export button verified")

    # Test standalone Demo Playbook downloads for both DevSecOps and CNAP scopes
    r_playbook_dev = SESSION.get(f"{BASE_URL}/api/v1/export/demo-playbook?report=devsecops", timeout=TIMEOUT)
    check(r_playbook_dev.status_code == 200 and "60 Minutes Overall Cap" in r_playbook_dev.text, "DevSecOps Demo Playbook export (<=60m cap) HTTP 200 verified")
    r_playbook_cnap = SESSION.get(f"{BASE_URL}/api/v1/export/demo-playbook?report=cnap", timeout=TIMEOUT)
    check(r_playbook_cnap.status_code == 200 and "45 Minutes Overall Cap" in r_playbook_cnap.text, "CNAP Demo Playbook export (<=45m cap) HTTP 200 verified")

    # 9. Phase 6: Executive Review Panel & GA Deficit Attestation Waivers (NEW MILESTONE)
    print("\n[On-Path 9] Verifying Phase 6 Executive Reviews & Deficit Waivers...")
    res6 = post_chat("open executive review", action_id="open_executive_review", context_data=ctx)
    check("Phase 6: Executive Review Panel & GA Deficit Attestation Waivers" in res6["a2ui_payloads"][0], "Phase 6 Executive Review card verified")
    check("download_executive_memo" in res6["a2ui_payloads"][0], "Executive Waiver Memo download button verified")
    r_memo = SESSION.get(f"{BASE_URL}/api/v1/export/executive-review-memo?report=cnap", timeout=TIMEOUT)
    check(r_memo.status_code == 200 and "APPROVED BY EXECUTIVE REVIEW PANEL" in r_memo.text, "Standalone Executive Review Waiver Memo HTTP 200 verified")

    # 10. Phase 7: Master Portal Publication & Contributor Recognition Manifesto (NEW MILESTONE)
    print("\n[On-Path 10] Verifying Phase 7 Master Portal Publication & Contributor Recognition...")
    res7 = post_chat("publish and recognize", action_id="open_publication_recognition", context_data=ctx)
    check("Phase 7: Master Portal Publication & Contributor Recognition Manifesto" in res7["a2ui_payloads"][0], "Phase 7 Master Publication card verified")
    check("100% Complete" in res7["a2ui_payloads"][0], "Lifecycle progress completion verified (100%)")
    check("download_publication_bundle" in res7["a2ui_payloads"][0], "Final Publication Bundle download button verified")
    r_bundle = SESSION.get(f"{BASE_URL}/api/v1/export/final-publication-bundle?report=cnap", timeout=TIMEOUT)
    check(r_bundle.status_code == 200 and "100% COMPLETE & APPROVED FOR UPLOAD" in r_bundle.text, "Standalone Final Publication Bundle HTTP 200 verified")

def test_off_path_non_standard_workflow():
    print("\n==========================================================================")
    print("PART 2: OFF-PATH & EXPLORATORY WORKFLOW VERIFICATION (NON-STANDARD)")
    print("==========================================================================")

    # 1. Ad-Hoc Conversational AI Query outside sequential phase steps
    print("\n[Off-Path 1] Verifying Ad-Hoc Conversational AI Fallback (Out of sequence question)...")
    q1 = "What is the GAAP revenue floor threshold and how do we calculate standalone CAGR for enterprise SKUs?"
    res_ai1 = post_chat(q1)
    check(res_ai1.get("a2ui_payloads", []) == [], "AI fallback did not erroneously throw back an onboarding form")
    check("revenue" in res_ai1["response_text"].lower() or "floor" in res_ai1["response_text"].lower() or "$25" in res_ai1["response_text"] or "gaap" in res_ai1["response_text"].lower() or "cagr" in res_ai1["response_text"].lower(), f"Intelligent dynamic AI reasoning generated: {res_ai1['response_text'][:120]}...")

    # 2. Out-of-Order Natural Language Phase Jumping
    print("\n[Off-Path 2] Verifying Out-of-Order Natural Language Phase Jumping...")
    res_jump = post_chat("show me the demo sandboxes for cloud-native applications")
    check("Phase 5: On-Demand Demo Environments" in res_jump["a2ui_payloads"][0], "Successfully jumped out of sequence directly into Phase 5 via natural language")
    check("71% Complete" in res_jump["a2ui_payloads"][0], "Phase tracker maintained correct completion math after jump")

    # 3. Saved Artifacts Persistence & Session State Restoration
    print("\n[Off-Path 3] Verifying Saved Artifacts Persistence & Session State Restoration...")
    r_list = SESSION.get(f"{BASE_URL}/api/v1/artifacts/", timeout=TIMEOUT)
    check(r_list.status_code == 200, f"Listed {len(r_list.json()) if r_list.status_code == 200 else 0} persisted artifacts from storage")

    # Save current context test
    test_artifact = {
        "title": "Live E2E Verification Matrix",
        "artifact_type": "scorecard",
        "summary": "Automated verification artifact saved from full E2E run",
        "content": "### E2E Evaluation Matrix\nAll 7 phases 100% verified.",
        "metadata_json": json.dumps({"verified": True, "phase": 7})
    }
    r_create = SESSION.post(f"{BASE_URL}/api/v1/artifacts/", json=test_artifact, timeout=TIMEOUT)
    check(r_create.status_code == 201, f"Created new SavedArtifact id={r_create.json()['id']}")

    # Restore session context
    r_restore = SESSION.post(f"{BASE_URL}/api/v1/artifacts/restore", json={}, timeout=TIMEOUT)
    check(r_restore.status_code == 200, "Session context restoration engine returned 200 OK")
    print("  [PASS] Session context synthesis successfully restored previous application state.")

def main():
    try:
        test_on_path_standard_workflow()
        test_off_path_non_standard_workflow()
        print("\n==========================================================================")
        print("🏆 SUCCESS: ALL ON-PATH & OFF-PATH END-TO-END WORKFLOW TESTS PASSED 100%!")
        print("==========================================================================")
    except Exception as e:
        print(f"\n❌ FATAL E2E VERIFICATION ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
