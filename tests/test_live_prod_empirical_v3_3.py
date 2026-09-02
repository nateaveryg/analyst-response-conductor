"""
Empirical Challenger Verification Script for Conductor v3 Iteration 3
Target: https://conductor-v3-prod-4izasuhqpq-uc.a.run.app

Audits:
1. Root URL (/) loads Flutter Web application (index.html, flutter_bootstrap.js, main.dart.wasm / main.dart.js) with HTTP 200.
2. Evaluates browser console errors (distinguishing application runtime exceptions from browser-default favicon requests).
3. Verifies reactive backend connection (/api/v1/workspaces, /api/v1/a2ui/chat).
4. Verifies interactive PlutoGrid questionnaire data table and Governance Radar modal rendering.
5. Inspects all 7 lifecycle phases, visual rendering, and DOM semantics.
6. Stress-tests SPA routes and unmapped routes.
"""

import os
import sys
import time
import json
import urllib.request
from playwright.sync_api import sync_playwright

PROD_URL = "https://conductor-v3-prod-4izasuhqpq-uc.a.run.app"
ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_artifacts", "v3_3_empirical"))

def run_empirical_verification():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_url": PROD_URL,
        "browser": "Google Chrome (/usr/bin/google-chrome)",
        "checks": {}
    }

    console_logs = []
    app_uncaught_errors = []
    browser_resource_errors = []
    network_requests = []
    failed_requests = []

    print("=" * 80)
    print("CONDUCTOR v3 ITERATION 3 EMPIRICAL CHALLENGE VERIFICATION")
    print(f"Target URL:    {PROD_URL}")
    print(f"Artifacts Dir: {ARTIFACTS_DIR}")
    print("=" * 80)

    # 1. Direct HTTP Asset Verification
    print("\n[Step 1] Direct HTTP Asset Contract Verification...")
    assets_to_test = [
        ("/", 200, "text/html"),
        ("/flutter_bootstrap.js", 200, "javascript"),
        ("/main.dart.wasm", 200, "wasm"),
        ("/main.dart.js", 200, "javascript"),
        ("/health", 200, "application/json"),
        ("/api/v1/workspaces", 200, "application/json"),
        ("/workspaces", 200, "text/html"),
        ("/governance", 200, "text/html"),
        ("/var/log", 404, "application/json"),
        ("/etc/passwd", 404, "application/json"),
    ]
    direct_http_results = {}
    all_http_ok = True
    for path, expected_status, expected_ct in assets_to_test:
        req_url = f"{PROD_URL}{path}"
        try:
            req = urllib.request.Request(req_url, headers={"User-Agent": "ConductorV3EmpiricalChallenger/3.0"})
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                ct = resp.headers.get("content-type", "")
                body_sample = resp.read(256).decode("utf-8", errors="replace")
                passed = (status == expected_status) and (expected_ct in ct)
                direct_http_results[path] = {
                    "status": status,
                    "expected_status": expected_status,
                    "content_type": ct,
                    "body_sample": body_sample[:100],
                    "passed": passed
                }
                if not passed:
                    all_http_ok = False
        except urllib.error.HTTPError as e:
            status = e.code
            ct = e.headers.get("content-type", "")
            body_sample = e.read().decode("utf-8", errors="replace")
            passed = (status == expected_status) and (expected_ct in ct)
            direct_http_results[path] = {
                "status": status,
                "expected_status": expected_status,
                "content_type": ct,
                "body_sample": body_sample[:100],
                "passed": passed
            }
            if not passed:
                all_http_ok = False
        print(f" -> {path:25s} HTTP {status} (Expected {expected_status}) [CT: {ct[:30]}] -> {'PASS' if passed else 'FAIL'}")

    results["checks"]["direct_http_contracts"] = {
        "passed": all_http_ok,
        "details": direct_http_results
    }

    # 2. Browser Automation via Playwright
    with sync_playwright() as p:
        print("\n[Step 2] Launching Google Chrome headless...")
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
            console_logs.append({"type": msg.type, "text": msg.text, "location": msg.location})
            if msg.type == "error":
                loc_url = (msg.location.get("url", "") if isinstance(msg.location, dict) else "")
                if "favicon.ico" in msg.text or "favicon.ico" in loc_url:
                    browser_resource_errors.append(f"Browser Resource 404: {msg.text} @ {msg.location}")
                else:
                    app_uncaught_errors.append(f"App Console Error: {msg.text} @ {msg.location}")

        def on_pageerror(err):
            app_uncaught_errors.append(f"Uncaught Page Exception: {err}")

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

        print(f"\n[Step 3] Navigating to {PROD_URL}/ ...")
        nav_res = page.goto(PROD_URL, wait_until="networkidle", timeout=60000)
        time.sleep(5)

        title = page.title()
        status_code = nav_res.status if nav_res else 0
        flutter_view_count = page.locator("flutter-view").count()
        flt_glass_count = page.locator("flt-glass-pane").count()

        loaded_urls = {r["url"]: r["status"] for r in network_requests}
        wasm_loaded = any("main.dart.wasm" in url and status == 200 for url, status in loaded_urls.items())
        js_loaded = any(("main.dart.js" in url or "flutter_bootstrap.js" in url) and status == 200 for url, status in loaded_urls.items())

        # Enable accessibility semantics for DOM inspection
        page.evaluate("() => { const p = document.querySelector('flt-semantics-placeholder'); if (p) p.click(); }")
        time.sleep(2)

        path_p1 = os.path.join(ARTIFACTS_DIR, "01_root_initial_load.png")
        page.screenshot(path=path_p1)
        print(f" -> Root URL HTTP Status: {status_code}")
        print(f" -> Page Title: {title}")
        print(f" -> Flutter Canvas Mounted: {flt_glass_count > 0 or flutter_view_count > 0}")
        print(f" -> WASM/JS Distribution Assets: JS={js_loaded}, WASM={wasm_loaded}")
        print(f" -> Application Uncaught Errors: {len(app_uncaught_errors)}")
        print(f" -> Browser Default Resource Errors: {len(browser_resource_errors)} ({browser_resource_errors})")
        print(f" -> Failed Network Requests: {len(failed_requests)}")

        results["checks"]["root_url_and_assets"] = {
            "status_code": status_code,
            "title": title,
            "flutter_mounted": (flutter_view_count > 0 or flt_glass_count > 0),
            "wasm_loaded": wasm_loaded,
            "js_loaded": js_loaded,
            "total_requests": len(network_requests),
            "failed_requests": failed_requests,
            "app_uncaught_errors": app_uncaught_errors,
            "browser_resource_errors": browser_resource_errors,
            "passed": (status_code == 200 and (flutter_view_count > 0 or flt_glass_count > 0) and len(app_uncaught_errors) == 0 and len(failed_requests) == 0)
        }

        # 3. Reactive Backend API Connectivity
        print("\n[Step 4] Verifying Reactive Backend Connection (/api/v1/workspaces, /api/v1/a2ui/chat)...")
        workspaces_req = any("/api/v1/workspaces" in r["url"] and r["status"] == 200 for r in network_requests)
        chat_init_req = any("/api/v1/a2ui/chat" in r["url"] and r["status"] == 200 for r in network_requests)

        print(f" -> Initial Workspaces API Called: {workspaces_req}")
        print(f" -> Initial A2UI Chat Briefing Called: {chat_init_req}")

        # Interactive Chat Verification
        print("\n[Step 5] Submitting Interactive Chat Query via Browser DOM...")
        chat_prompt = "What is the revenue floor requirement for DevSecOps platforms?"
        # Input bar coordinates (500, 1044)
        page.mouse.click(500, 1044)
        time.sleep(1)
        page.keyboard.type(chat_prompt, delay=20)
        time.sleep(1)
        # Send button at (1884, 1044)
        page.mouse.click(1884, 1044)
        print(" -> Chat prompt submitted. Awaiting reactive response bubble...")
        time.sleep(6)

        path_chat = os.path.join(ARTIFACTS_DIR, "02_chat_reactive_response.png")
        page.screenshot(path=path_chat)

        semantics_chat = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
        has_chat_reply = any(term in semantics_chat for term in ["$25M", "revenue floor", "Universal Analyst Evaluation", "Cryptographic Lineage", "5913b82265885968", "Lineage:"])

        results["checks"]["reactive_chat_api"] = {
            "workspaces_endpoint_called": workspaces_req,
            "chat_endpoint_called": chat_init_req,
            "chat_prompt": chat_prompt,
            "reactive_response_rendered": has_chat_reply,
            "screenshot": path_chat,
            "passed": workspaces_req and chat_init_req and has_chat_reply
        }
        print(f" -> Reactive Chat Response Rendered in UI: {has_chat_reply} (Saved {path_chat})")

        # 4. Lifecycle Phases Progression (1 through 7)
        print("\n[Step 6] Stepping Through 7 Lifecycle Phases via JourneyStepper...")
        stepper_coords = {
            1: (100, 132),
            2: (300, 132),
            3: (520, 132),
            4: (749, 132),
            5: (960, 132),
            6: (1175, 132),
            7: (1395, 132),
        }
        phase_results = {}
        for p_idx in range(1, 8):
            cx, cy = stepper_coords[p_idx]
            page.mouse.click(cx, cy)
            time.sleep(3)

            scr_path = os.path.join(ARTIFACTS_DIR, f"03_phase_{p_idx}_rendered.png")
            page.screenshot(path=scr_path)

            sem_text = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
            phase_rendered = f"Phase {p_idx}" in sem_text
            phase_results[f"phase_{p_idx}"] = {
                "rendered": phase_rendered,
                "screenshot": scr_path
            }
            print(f" -> Phase {p_idx} Rendered: {phase_rendered} (Saved {scr_path})")

        all_phases_ok = all(v["rendered"] for v in phase_results.values())
        results["checks"]["lifecycle_phases"] = {
            "phases": phase_results,
            "passed": all_phases_ok
        }

        # 5. Interactive PlutoGrid Virtualized Data Table (Phase 4)
        print("\n[Step 7] Verifying Interactive PlutoGrid Data Table in Phase 4...")
        page.mouse.click(stepper_coords[4][0], stepper_coords[4][1])
        time.sleep(3)

        path_grid = os.path.join(ARTIFACTS_DIR, "04_plutogrid_virtualized_table.png")
        page.screenshot(path=path_grid)

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
        cols_found = [c for c in expected_cols if c in sem_text_p4]
        tabs_found = [t for t in ["All Tabs", "Product or Service 1-87", "Overall Viability 88-92", "Sales Execution-Pricing 93-105", "Customer Experience 111-121"] if t in sem_text_p4]
        rows_found = [r for r in ["SEC-01", "SEC-02", "SEC-03", "SEC-04", "SEC-05"] if r in sem_text_p4]

        grid_ok = len(cols_found) >= 5 and len(tabs_found) >= 3 and len(rows_found) >= 3
        results["checks"]["plutogrid_table"] = {
            "columns_detected": cols_found,
            "tabs_detected": tabs_found,
            "rows_detected": rows_found,
            "screenshot": path_grid,
            "passed": grid_ok
        }
        print(f" -> PlutoGrid Columns ({len(cols_found)}/{len(expected_cols)}): {cols_found}")
        print(f" -> PlutoGrid Tabs: {tabs_found}")
        print(f" -> PlutoGrid Rows: {rows_found}")
        print(f" -> PlutoGrid Status: {'PASS' if grid_ok else 'FAIL'}")

        # 6. Governance Radar Modal Display
        print("\n[Step 8] Verifying Governance Radar Modal Display...")
        page.mouse.click(1680, 28)
        time.sleep(3)

        path_radar = os.path.join(ARTIFACTS_DIR, "05_governance_radar_modal.png")
        page.screenshot(path=path_radar)

        sem_radar = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
        has_waiver = "Gemini Code Assist" in sem_radar or "PUBLIC_PREVIEW" in sem_radar
        has_approvers = "bradcalder@google.com" in sem_radar or "ar-counsel@google.com" in sem_radar or "Product GM" in sem_radar or "Corporate Legal" in sem_radar
        has_audit_btn = "Export Cryptographic Audit Bundle" in sem_radar or "Done" in sem_radar
        modal_opened = has_waiver and has_approvers and has_audit_btn

        results["checks"]["governance_radar_modal"] = {
            "modal_displayed": modal_opened,
            "waiver_rendered": has_waiver,
            "approvers_rendered": has_approvers,
            "action_buttons_rendered": has_audit_btn,
            "screenshot": path_radar,
            "passed": modal_opened
        }
        print(f" -> Governance Radar Modal Rendered: {modal_opened}")
        print(f" -> Dual Custody Sign-Offs Rendered: {has_approvers}")
        print(f" -> Audit Bundle Export Action: {has_audit_btn}")
        print(f" -> Modal Screenshot: {path_radar}")

        # Close modal
        page.mouse.click(1292, 786)
        time.sleep(1)

        # Final diagnostics summary
        print("\n[Step 9] Final Diagnostics Audit...")
        print(f" -> Total Console Messages Captured: {len(console_logs)}")
        print(f" -> Application Uncaught Errors:     {len(app_uncaught_errors)}")
        print(f" -> Browser Resource 404 Errors:     {len(browser_resource_errors)}")
        print(f" -> Total Network Requests:          {len(network_requests)}")
        print(f" -> Total Failed Network Requests:    {len(failed_requests)}")

        results["final_diagnostics"] = {
            "console_logs_count": len(console_logs),
            "app_uncaught_errors_count": len(app_uncaught_errors),
            "app_uncaught_errors": app_uncaught_errors,
            "browser_resource_errors_count": len(browser_resource_errors),
            "browser_resource_errors": browser_resource_errors,
            "network_requests_count": len(network_requests),
            "failed_requests_count": len(failed_requests),
            "failed_requests": failed_requests
        }

        app_passed = all(c.get("passed", False) for c in results["checks"].values()) and len(app_uncaught_errors) == 0 and len(failed_requests) == 0
        results["overall_passed"] = app_passed
        print("\n" + "=" * 80)
        print(f"OVERALL EMPIRICAL CHALLENGE VERDICT: {'APPROVE' if app_passed else 'REQUEST_CHANGES'}")
        print("=" * 80)

        # Write JSON output
        json_out = os.path.join(ARTIFACTS_DIR, "v3_3_empirical_results.json")
        with open(json_out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results JSON written to: {json_out}")

        browser.close()
        return results

if __name__ == "__main__":
    res = run_empirical_verification()
    if not res.get("overall_passed"):
        sys.exit(1)
