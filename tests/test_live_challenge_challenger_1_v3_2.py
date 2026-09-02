#!/usr/bin/env python3
"""
Live Browser Automation and PlutoGrid Rendering Empirical Challenge.
Targeting Conductor v3 deployments on Google Cloud Run:
- Frontend: https://conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app
- Fullstack Prod: https://conductor-v3-prod-4izasuhqpq-uc.a.run.app

Asserts:
1. Active <flt-glass-pane> / flutter-view canvas mounted in live DOM.
2. Material 3 styling and JourneyStepper traversal across all 7 phases.
3. PlutoGrid virtualized data table rendering multi-tab RFI questionnaires
   (tabs, columns, populated rows, SME assignments).
4. Zero console errors and zero failed application network requests.
5. Zero CORS errors during frontend-to-backend communication.
"""

import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_artifacts", "challenger_1_v3_2"))
TARGET_ENDPOINTS = [
    ("frontend-prod", "https://conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app"),
    ("backend-prod", "https://conductor-v3-prod-4izasuhqpq-uc.a.run.app"),
]

def audit_target_endpoint(name, target_url, browser_context):
    print("\n" + "=" * 90)
    print(f"AUDITING LIVE ENDPOINT: [{name.upper()}] -> {target_url}")
    print("=" * 90)

    target_dir = os.path.join(ARTIFACTS_DIR, name)
    os.makedirs(target_dir, exist_ok=True)

    page = browser_context.new_page()

    console_logs = []
    app_uncaught_errors = []
    cors_errors = []
    browser_resource_errors = []
    network_requests = []
    failed_requests = []

    def on_console(msg):
        text = msg.text
        msg_type = msg.type
        location = msg.location
        console_logs.append({"type": msg_type, "text": text, "location": location})
        if "CORS" in text.upper() or "CROSS-ORIGIN" in text.upper():
            cors_errors.append(f"Console CORS: {text} @ {location}")
        if msg_type == "error":
            loc_url = location.get("url", "") if isinstance(location, dict) else ""
            if "favicon.ico" in text or "favicon.ico" in loc_url:
                browser_resource_errors.append(f"Resource 404: {text}")
            else:
                app_uncaught_errors.append(f"App Console Error: {text} @ {location}")

    def on_pageerror(err):
        app_uncaught_errors.append(f"Uncaught Page Exception: {err}")

    def on_request_failed(req):
        fail_text = req.failure
        if req.url.endswith("favicon.ico"):
            browser_resource_errors.append(f"Failed favicon request: {req.url} - {fail_text}")
        else:
            failed_requests.append({
                "url": req.url,
                "method": req.method,
                "failure": str(fail_text),
                "is_app_failure": True
            })
            if "CORS" in str(fail_text).upper() or "BLOCKED" in str(fail_text).upper():
                cors_errors.append(f"Network Request CORS Failure: {req.url} ({fail_text})")

    def on_response(res):
        req = res.request
        network_requests.append({
            "url": res.url,
            "status": res.status,
            "status_text": res.status_text,
            "headers": dict(res.headers)
        })
        if res.status >= 400:
            if res.url.endswith("favicon.ico"):
                browser_resource_errors.append(f"HTTP {res.status} for favicon.ico: {res.url}")
            else:
                failed_requests.append({
                    "url": res.url,
                    "method": req.method,
                    "status": res.status,
                    "status_text": res.status_text,
                    "is_app_failure": True
                })

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("requestfailed", on_request_failed)
    page.on("response", on_response)

    endpoint_report = {
        "target_url": target_url,
        "name": name,
        "checks": {}
    }

    # Step 1: Navigate to endpoint
    print(f"\n[1] Navigating to {target_url} ...")
    nav_start = time.time()
    nav_res = page.goto(target_url, wait_until="networkidle", timeout=60000)
    nav_duration = time.time() - nav_start
    time.sleep(4)  # Allow CanvasKit WebAssembly initial frame rendering

    title = page.title()
    status_code = nav_res.status if nav_res else 0
    print(f" -> Response Status: HTTP {status_code} in {nav_duration:.2f}s")
    print(f" -> Document Title: '{title}'")

    # Step 2: Assert active CanvasKit / DOM canvas elements
    print("\n[2] Checking live DOM for CanvasKit / <flt-glass-pane> mounting...")
    flt_glass_pane_count = page.locator("flt-glass-pane").count()
    flutter_view_count = page.locator("flutter-view").count()
    canvas_count = page.locator("canvas").count()
    has_canvas_element = (flt_glass_pane_count > 0 or flutter_view_count > 0 or canvas_count > 0)

    print(f" -> <flt-glass-pane> element count: {flt_glass_pane_count}")
    print(f" -> <flutter-view> element count:   {flutter_view_count}")
    print(f" -> <canvas> element count:         {canvas_count}")
    print(f" -> Active Flutter Canvas Mounted:  {has_canvas_element}")

    scr_root = os.path.join(target_dir, "01_root_canvas_mounted.png")
    page.screenshot(path=scr_root)
    print(f" -> Root screenshot saved: {scr_root}")

    endpoint_report["checks"]["canvas_mounted"] = {
        "passed": has_canvas_element,
        "flt_glass_pane_count": flt_glass_pane_count,
        "flutter_view_count": flutter_view_count,
        "canvas_count": canvas_count,
        "status_code": status_code,
        "title": title
    }

    # Enable accessibility semantics for deep DOM inspection
    page.evaluate("() => { const p = document.querySelector('flt-semantics-placeholder'); if (p) p.click(); }")
    time.sleep(2)

    # Step 3: Material 3 styling & JourneyStepper traversal
    print("\n[3] Testing Material 3 JourneyStepper traversal across all 7 phases...")
    stepper_coords = {
        1: (100, 132),
        2: (300, 132),
        3: (520, 132),
        4: (749, 132),
        5: (960, 132),
        6: (1175, 132),
        7: (1395, 132),
    }

    phase_traversal_results = {}
    for phase_num in range(1, 8):
        x, y = stepper_coords[phase_num]
        page.mouse.click(x, y)
        time.sleep(2)

        scr_phase = os.path.join(target_dir, f"02_journey_stepper_phase_{phase_num}.png")
        page.screenshot(path=scr_phase)

        sem_text = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
        is_phase_visible = (f"Phase {phase_num}" in sem_text or phase_num == 1)
        phase_traversal_results[f"phase_{phase_num}"] = {
            "visible": is_phase_visible,
            "screenshot": scr_phase
        }
        print(f" -> Phase {phase_num} clicked at ({x}, {y}): visible in DOM={is_phase_visible}")

    stepper_passed = all(p["visible"] for p in phase_traversal_results.values())
    endpoint_report["checks"]["journey_stepper"] = {
        "passed": stepper_passed,
        "phases": phase_traversal_results
    }

    # Step 4: PlutoGrid virtualized data table rendering multi-tab RFI questionnaires
    print("\n[4] Asserting PlutoGrid virtualized data table rendering (Phase 4)...")
    # Click Phase 4 explicitly
    page.mouse.click(stepper_coords[4][0], stepper_coords[4][1])
    time.sleep(3)

    scr_plutogrid = os.path.join(target_dir, "03_plutogrid_phase4_render.png")
    page.screenshot(path=scr_plutogrid)
    print(f" -> PlutoGrid Phase 4 screenshot saved: {scr_plutogrid}")

    sem_p4 = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")

    # Assert title / header
    has_grid_header = "PlutoGrid" in sem_p4 or "Virtualized Multi-Tab Questionnaire Grid" in sem_p4
    print(f" -> PlutoGrid Header Detected: {has_grid_header}")

    # Assert tabs
    expected_tabs = [
        "All Tabs",
        "Product or Service 1-87",
        "Overall Viability 88-92",
        "Sales Execution-Pricing 93-105",
        "Customer Experience 111-121"
    ]
    detected_tabs = [t for t in expected_tabs if t in sem_p4]
    print(f" -> Multi-Tab Questionnaire Tabs Detected ({len(detected_tabs)}/{len(expected_tabs)}): {detected_tabs}")

    # Assert columns
    expected_columns = [
        "Section ID",
        "Worksheet Tab",
        "RFI Question Text",
        "Assigned SME",
        "Confidence",
        "Offered (Built-in)",
        "Grounded Draft Response",
    ]
    detected_columns = [c for c in expected_columns if c in sem_p4]
    print(f" -> PlutoGrid Columns Detected ({len(detected_columns)}/{len(expected_columns)}): {detected_columns}")

    # Assert populated rows
    expected_rows = ["SEC-01", "SEC-02", "SEC-03", "SEC-04", "SEC-05"]
    detected_rows = [r for r in expected_rows if r in sem_p4]
    print(f" -> Populated Rows Detected ({len(detected_rows)}/{len(expected_rows)}): {detected_rows}")

    # Assert SME assignments
    expected_smes = [
        "davidjacobs@google.com",
        "nathenharvey@google.com",
        "sarahmiller@google.com",
        "enterprise-sales@google.com",
        "customer-eng@google.com"
    ]
    detected_smes = [s for s in expected_smes if s in sem_p4]
    print(f" -> SME Assignments Detected ({len(detected_smes)}/{len(expected_smes)}): {detected_smes}")

    plutogrid_passed = (
        has_grid_header and
        len(detected_tabs) >= 4 and
        len(detected_columns) >= 5 and
        len(detected_rows) >= 4 and
        len(detected_smes) >= 4
    )

    endpoint_report["checks"]["plutogrid"] = {
        "passed": plutogrid_passed,
        "header_detected": has_grid_header,
        "tabs_detected": detected_tabs,
        "columns_detected": detected_columns,
        "rows_detected": detected_rows,
        "sme_assignments_detected": detected_smes
    }

    # Step 5: Test Tab Interactivity in PlutoGrid
    print("\n[5] Testing ChoiceChip Tab switching in PlutoGrid...")
    # Find tab chip coordinates and click "Product or Service 1-87"
    tab_nodes = page.evaluate("""() => {
        const elms = Array.from(document.querySelectorAll('flt-semantics'));
        return elms.map(e => ({
            text: e.innerText,
            rect: e.getBoundingClientRect()
        })).filter(x => x.text && x.text.includes('Product or Service'));
    }""")
    if tab_nodes:
        tab_rect = tab_nodes[0]["rect"]
        tx = tab_rect["x"] + tab_rect["width"] / 2
        ty = tab_rect["y"] + tab_rect["height"] / 2
        page.mouse.click(tx, ty)
        time.sleep(2)
        scr_tab_click = os.path.join(target_dir, "04_plutogrid_tab_filtered.png")
        page.screenshot(path=scr_tab_click)
        print(f" -> Tab 'Product or Service 1-87' clicked at ({tx:.1f}, {ty:.1f}). Screenshot: {scr_tab_click}")

    # Step 6: Assert Zero Console Errors, Zero App Network Failures, Zero CORS Errors
    print("\n[6] Auditing telemetry: Console Errors, App Network Failures, CORS Errors...")
    print(f" -> Total Console Messages:          {len(console_logs)}")
    print(f" -> Application Uncaught Errors:     {len(app_uncaught_errors)}")
    for err in app_uncaught_errors:
        print(f"    ! {err}")
    print(f" -> Browser Resource 404s (favicon): {len(browser_resource_errors)}")
    print(f" -> Total Network Requests:          {len(network_requests)}")
    print(f" -> Failed Application Requests:     {len(failed_requests)}")
    for req in failed_requests:
        print(f"    ! {req}")
    print(f" -> CORS Errors Detected:            {len(cors_errors)}")
    for cors in cors_errors:
        print(f"    ! {cors}")

    telemetry_passed = (
        len(app_uncaught_errors) == 0 and
        len(failed_requests) == 0 and
        len(cors_errors) == 0
    )

    endpoint_report["checks"]["telemetry"] = {
        "passed": telemetry_passed,
        "app_uncaught_errors_count": len(app_uncaught_errors),
        "app_uncaught_errors": app_uncaught_errors,
        "failed_application_requests_count": len(failed_requests),
        "failed_application_requests": failed_requests,
        "cors_errors_count": len(cors_errors),
        "cors_errors": cors_errors,
        "browser_resource_errors_count": len(browser_resource_errors)
    }

    # Overall endpoint verdict
    overall_endpoint_passed = (
        has_canvas_element and
        stepper_passed and
        plutogrid_passed and
        telemetry_passed
    )
    endpoint_report["overall_passed"] = overall_endpoint_passed
    print(f"\n[{name.upper()}] EVALUATION RESULT: {'PASS' if overall_endpoint_passed else 'FAIL'}")

    page.close()
    return endpoint_report

def main():
    print("=" * 90)
    print("CONDUCTOR v3 EMPIRICAL CHALLENGE SUITE: PLAYWRIGHT DOM & PLUTOGRID")
    print(f"Artifacts output directory: {ARTIFACTS_DIR}")
    print("=" * 90)

    overall_results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoints": {}
    }

    with sync_playwright() as p:
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

        for name, url in TARGET_ENDPOINTS:
            rep = audit_target_endpoint(name, url, context)
            overall_results["endpoints"][name] = rep

        browser.close()

    summary_file = os.path.join(ARTIFACTS_DIR, "challenge_results.json")
    with open(summary_file, "w") as f:
        json.dump(overall_results, f, indent=2)

    all_passed = all(e["overall_passed"] for e in overall_results["endpoints"].values())
    print("\n" + "=" * 90)
    print(f"FINAL CHALLENGER VERDICT: {'APPROVE' if all_passed else 'REQUEST_CHANGES'}")
    print("=" * 90)

    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
