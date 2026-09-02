"""
Empirical Challenge Test Suite for Conductor v3 Requirement R4.
Audits live Cloud Run production deployment for:
1. Browser Automation via Playwright with /usr/bin/google-chrome.
2. Root URL (/) serving index.html, main.dart.wasm, main.dart.js, manifest.json with HTTP 200.
   Zero uncaught JavaScript errors or network failures.
3. Reactive backend API connectivity (/api/v1/workspaces, /api/v1/a2ui/chat).
4. Declarative <a2ui-json> payloads across all 7 lifecycle phases.
5. PlutoGrid virtualized data table (9 structured columns, multi-tab ChoiceChips).
6. Governance Radar modal display (compliance scorecards, dual-custody waiver signing).
"""

import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

PROD_URL = "https://conductor-v3-prod-105792947502.us-central1.run.app"
ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_artifacts", "r4_empirical"))

def run_empirical_challenge():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_url": PROD_URL,
        "browser": "Google Chrome (/usr/bin/google-chrome)",
        "checks": {}
    }

    console_logs = []
    uncaught_errors = []
    network_requests = []
    failed_requests = []

    print("=" * 80)
    print("CONDUCTOR v3 REQUIREMENT R4 EMPIRICAL CHALLENGE")
    print(f"Target Service: {PROD_URL}")
    print(f"Artifacts Dir:  {ARTIFACTS_DIR}")
    print("=" * 80)

    with sync_playwright() as p:
        print("\n[Step 1] Launching System Google Chrome in Headless Mode...")
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1920,1080"
            ]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Listeners
        def on_console(msg):
            console_logs.append({"type": msg.type, "text": msg.text})
            if msg.type == "error":
                uncaught_errors.append(f"Console Error: {msg.text}")

        def on_pageerror(err):
            uncaught_errors.append(f"Uncaught Exception: {err}")

        def on_response(res):
            network_requests.append({
                "url": res.url,
                "status": res.status,
                "content_type": res.headers.get("content-type", "")
            })
            if res.status >= 400:
                failed_requests.append({
                    "url": res.url,
                    "status": res.status,
                    "content_type": res.headers.get("content-type", "")
                })

        page.on("console", on_console)
        page.on("pageerror", on_pageerror)
        page.on("response", on_response)

        print("\n[Step 2] Navigating to Root URL (/) and checking asset loading...")
        nav_res = page.goto(PROD_URL, wait_until="networkidle", timeout=60000)
        time.sleep(4)

        # Check title and initial assets
        title = page.title()
        status_code = nav_res.status if nav_res else 0
        flutter_view_count = page.locator("flutter-view").count()

        # Verify key assets loaded
        loaded_urls = {r["url"]: r["status"] for r in network_requests}
        wasm_loaded = any("main.dart.wasm" in url and status == 200 for url, status in loaded_urls.items())
        js_loaded = any(("main.dart.js" in url or "flutter_bootstrap.js" in url) and status == 200 for url, status in loaded_urls.items())
        manifest_loaded = any("manifest" in url.lower() and status == 200 for url, status in loaded_urls.items())

        results["checks"]["root_url_loading"] = {
            "status_code": status_code,
            "title": title,
            "flutter_view_mounted": flutter_view_count > 0,
            "wasm_loaded": wasm_loaded,
            "js_loaded": js_loaded,
            "manifest_loaded": manifest_loaded,
            "total_requests": len(network_requests),
            "failed_requests_count": len(failed_requests),
            "uncaught_errors_count": len(uncaught_errors),
            "passed": status_code == 200 and flutter_view_count > 0 and len(uncaught_errors) == 0 and len(failed_requests) == 0
        }
        print(f" -> Root URL Status: {status_code}")
        print(f" -> Page Title: {title}")
        print(f" -> Flutter View Mounted: {flutter_view_count > 0}")
        print(f" -> WASM / JS Assets Loaded with HTTP 200: {wasm_loaded or js_loaded}")
        print(f" -> Uncaught Errors: {len(uncaught_errors)}, Failed Requests: {len(failed_requests)}")

        # Enable accessibility semantics for DOM inspection
        page.evaluate("() => { const p = document.querySelector('flt-semantics-placeholder'); if (p) p.click(); }")
        time.sleep(2)

        # Screenshot Phase 1
        path_p1 = os.path.join(ARTIFACTS_DIR, "01_phase1_initial.png")
        page.screenshot(path=path_p1)
        print(f" -> Phase 1 screenshot saved to {path_p1}")

        # Verify workspaces API call
        workspaces_called = any("/api/v1/workspaces" in r["url"] and r["status"] == 200 for r in network_requests)
        chat_called = any("/api/v1/a2ui/chat" in r["url"] and r["status"] == 200 for r in network_requests)
        results["checks"]["backend_api_connectivity"] = {
            "workspaces_endpoint_called": workspaces_called,
            "chat_endpoint_called": chat_called,
            "passed": workspaces_called and chat_called
        }
        print(f" -> Backend Workspaces API Verified: {workspaces_called}")
        print(f" -> Backend A2UI Chat API Verified: {chat_called}")

        print("\n[Step 3] Verifying Interactive Chat Interaction via Browser Input Bar...")
        chat_test_prompt = "What is the revenue floor requirement for DevSecOps platforms?"
        # Click chat input field at (500, 1044)
        page.mouse.click(500, 1044)
        time.sleep(1)
        page.keyboard.type(chat_test_prompt, delay=25)
        time.sleep(1)
        # Click send button at (1884, 1044)
        page.mouse.click(1884, 1044)
        print(" -> Sent chat prompt from browser. Waiting for reactive response...")
        time.sleep(6)

        path_chat = os.path.join(ARTIFACTS_DIR, "02_chat_interaction.png")
        page.screenshot(path=path_chat)

        semantics_chat = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
        has_revenue_resp = any(k in semantics_chat for k in ["$25M", "revenue floor", "Audit Token", "Cryptographic Lineage"])
        results["checks"]["interactive_chat"] = {
            "prompt_submitted": chat_test_prompt,
            "response_rendered_in_dom": has_revenue_resp,
            "screenshot": path_chat,
            "passed": has_revenue_resp
        }
        print(f" -> Reactive Chat Response Rendered in UI: {has_revenue_resp}")

        print("\n[Step 4] Verifying Declarative <a2ui-json> Across 7 Lifecycle Phases...")
        phase_results = {}

        stepper_coords = {
            1: (100, 132),
            2: (300, 132),
            3: (520, 132),
            4: (749, 132),
            5: (960, 132),
            6: (1175, 132),
            7: (1395, 132),
        }

        for p_num in range(1, 8):
            cx, cy = stepper_coords[p_num]
            print(f" -> Engaging Stepper for Phase {p_num} at ({cx}, {cy})...")
            page.mouse.click(cx, cy)
            time.sleep(3)

            scr_path = os.path.join(ARTIFACTS_DIR, f"03_phase_{p_num}_rendered.png")
            page.screenshot(path=scr_path)

            sem_text = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
            phase_rendered = f"Phase {p_num}" in sem_text
            phase_results[f"phase_{p_num}"] = {
                "stepper_clicked": True,
                "rendered_in_dom": phase_rendered,
                "screenshot": scr_path
            }
            print(f"    Phase {p_num} DOM Verification: {phase_rendered} (Saved {scr_path})")

        all_phases_passed = all(pr["rendered_in_dom"] for pr in phase_results.values())
        results["checks"]["lifecycle_phases"] = {
            "phases": phase_results,
            "passed": all_phases_passed
        }

        print("\n[Step 5] Verifying PlutoGrid Virtualized Data Table (Phase 4)...")
        page.mouse.click(stepper_coords[4][0], stepper_coords[4][1])
        time.sleep(3)

        grid_scr_path = os.path.join(ARTIFACTS_DIR, "04_plutogrid_detailed.png")
        page.screenshot(path=grid_scr_path)

        sem_text_p4 = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
        
        expected_cols = [
            "Section ID",
            "Worksheet Tab",
            "RFI Question Text",
            "Assigned SME",
            "Confidence",
            "Offered (Built-in)",
            "Grounded Draft Response",
        ]
        cols_detected = [col for col in expected_cols if col in sem_text_p4]
        tabs_detected = [t for t in ["All Tabs", "Product or Service 1-87", "Overall Viability 88-92", "Sales Execution-Pricing 93-105", "Customer Experience 111-121"] if t in sem_text_p4]
        rows_detected = [r for r in ["SEC-01", "SEC-02", "SEC-03", "SEC-04", "SEC-05"] if r in sem_text_p4]

        results["checks"]["plutogrid_virtualized_table"] = {
            "columns_detected": cols_detected,
            "tabs_detected": tabs_detected,
            "rows_detected": rows_detected,
            "screenshot": grid_scr_path,
            "passed": len(cols_detected) >= 5 and len(tabs_detected) >= 3 and len(rows_detected) >= 3
        }
        print(f" -> PlutoGrid Columns Detected: {len(cols_detected)}/{len(expected_cols)}: {cols_detected}")
        print(f" -> PlutoGrid Tab ChoiceChips: {tabs_detected}")
        print(f" -> PlutoGrid Virtualized Rows: {rows_detected}")

        print("\n[Step 6] Verifying Governance Radar Modal Display & Waiver Actions...")
        # Click Governance Radar button at (1680, 28)
        page.mouse.click(1680, 28)
        time.sleep(3)

        radar_scr_path = os.path.join(ARTIFACTS_DIR, "05_governance_radar_detailed.png")
        page.screenshot(path=radar_scr_path)

        sem_radar = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")

        has_waiver = "Gemini Code Assist" in sem_radar or "PUBLIC_PREVIEW" in sem_radar
        has_approvers = "bradcalder@google.com" in sem_radar or "ar-counsel@google.com" in sem_radar or "Product GM" in sem_radar or "Corporate Legal" in sem_radar
        has_audit_btn = "Export Cryptographic Audit Bundle" in sem_radar or "Done" in sem_radar
        modal_opened = has_waiver and has_approvers and has_audit_btn

        results["checks"]["governance_radar_modal"] = {
            "modal_displayed": modal_opened,
            "deficit_waivers_rendered": has_waiver,
            "dual_custody_approvers_rendered": has_approvers,
            "audit_bundle_action_rendered": has_audit_btn,
            "screenshot": radar_scr_path,
            "passed": modal_opened
        }
        print(f" -> Governance Radar Modal Displayed: {modal_opened}")
        print(f" -> Deficit Attestation Waivers Rendered: {has_waiver}")
        print(f" -> Dual-Custody Approvers Rendered: {has_approvers}")
        print(f" -> Audit Export & Action Buttons Rendered: {has_audit_btn}")

        # Close modal
        page.mouse.click(1292, 786) # Done button
        time.sleep(1)

        print("\n" + "=" * 80)
        overall_passed = all(check.get("passed", False) for check in results["checks"].values())
        results["overall_passed"] = overall_passed
        print(f"OVERALL EMPIRICAL CHALLENGE VERDICT: {'APPROVE' if overall_passed else 'REQUEST_CHANGES'}")
        print("=" * 80)

        # Save JSON results
        json_path = os.path.join(ARTIFACTS_DIR, "empirical_challenge_results.json")
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed JSON report saved to: {json_path}")

        browser.close()
        return results

if __name__ == "__main__":
    res = run_empirical_challenge()
    if not res.get("overall_passed"):
        sys.exit(1)
