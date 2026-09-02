"""
Production Contract & Boundary Stress-Testing Harness for Conductor v3 APIs
Target: https://conductor-v3-prod-4izasuhqpq-uc.a.run.app
"""

import urllib.request
import urllib.error
import json
import time
import uuid

BASE_URL = "https://conductor-v3-prod-4izasuhqpq-uc.a.run.app"

def test_api_endpoints():
    tests = [
        # Health & Readiness
        ("GET", "/health", None, 200),
        ("GET", "/ready", None, 200),
        ("GET", "/api/v1/agent-card", None, 200),
        ("GET", "/.well-known/agent.json", None, 200),

        # Workspaces
        ("GET", "/api/v1/workspaces", None, 200),
        ("GET", "/api/v1/workspaces/11111111-1111-1111-1111-111111111111", None, 200),
        ("GET", "/api/v1/workspaces/invalid-uuid-format", None, 422),
        ("GET", f"/api/v1/workspaces/{uuid.uuid4()}", None, 404),
        ("POST", "/api/v1/workspaces", {"name": "Empirical Stress Workspace", "report_type": "DevSecOps"}, 201),

        # Chat
        ("POST", "/api/v1/a2ui/chat", {"message": "What is the revenue floor requirement for DevSecOps platforms?"}, 200),
        ("POST", "/api/v1/a2ui/chat", {"message": "Tell me about Phase 4 RAG grounded answers.", "workspace_id": "11111111-1111-1111-1111-111111111111"}, 200),
        ("POST", "/api/v1/a2ui/chat", {"message": "X" * 5000}, 200),
        # Validation checks (missing message field)
        ("POST", "/api/v1/a2ui/chat", {}, 422),
        ("POST", "/api/v1/a2ui/chat", {"action": "unsupported_action_without_message"}, 422),

        # Artifacts
        ("GET", "/api/v1/artifacts", None, 200),
        ("GET", "/api/v1/artifacts/invalid-uuid", None, 422),
        ("GET", f"/api/v1/artifacts/{uuid.uuid4()}", None, 404),

        # Exports
        ("GET", "/api/v1/export/deep-dive-report", None, 200),
        ("GET", "/api/v1/export/workback-schedule", None, 200),
        ("GET", "/api/v1/export/kickoff-deck", None, 200),
        ("GET", "/api/v1/export/rfi-responses", None, 200),
        ("GET", "/api/v1/export/demo-playbook", None, 200),
        ("GET", "/api/v1/export/executive-review-memo", None, 200),
        ("GET", "/api/v1/export/final-publication-bundle", None, 200),

        # Governance
        ("GET", "/api/v1/governance/scorecard", None, 200),
        ("GET", "/api/v1/governance/waivers", None, 200),
        ("GET", "/api/v1/governance/audit-bundle", None, 200),

        # SPA Allowed Routes
        ("GET", "/", None, 200),
        ("GET", "/workspaces", None, 200),
        ("GET", "/governance", None, 200),
        ("GET", "/review", None, 200),
        ("GET", "/publish", None, 200),
        ("GET", "/onboarding", None, 200),
        ("GET", "/intake", None, 200),

        # Sensitive / Path Traversal Rejections
        ("GET", "/etc/passwd", None, 404),
        ("GET", "/var/log", None, 404),
        ("GET", "/var/log/syslog", None, 404),
        ("GET", "/bin/sh", None, 404),
        ("GET", "/proc/self/environ", None, 404),
        ("GET", "/../backend/internal/api/router.go", None, 404),
        ("GET", "/random-non-existent-path-12345", None, 404),
    ]

    results = []
    print(f"Executing {len(tests)} API Stress & Boundary Tests against {BASE_URL}...\n")
    all_passed = True

    for method, path, body, expected_status in tests:
        url = f"{BASE_URL}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        headers = {"User-Agent": "ConductorV3StressTester/3.0"}
        if data:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed = (time.time() - t0) * 1000
                status = resp.status
                passed = (status == expected_status)
                if not passed:
                    all_passed = False
                print(f"[{'PASS' if passed else 'FAIL'}] {method:4s} {path:45s} -> Status {status} (Expected {expected_status}) in {elapsed:.1f}ms")
                results.append({"method": method, "path": path, "status": status, "expected": expected_status, "passed": passed, "latency_ms": elapsed})
        except urllib.error.HTTPError as e:
            elapsed = (time.time() - t0) * 1000
            status = e.code
            passed = (status == expected_status)
            if not passed:
                all_passed = False
            print(f"[{'PASS' if passed else 'FAIL'}] {method:4s} {path:45s} -> Status {status} (Expected {expected_status}) in {elapsed:.1f}ms")
            results.append({"method": method, "path": path, "status": status, "expected": expected_status, "passed": passed, "latency_ms": elapsed})
        except Exception as ex:
            elapsed = (time.time() - t0) * 1000
            print(f"[ERROR] {method:4s} {path:45s} -> Exception: {ex} in {elapsed:.1f}ms")
            results.append({"method": method, "path": path, "status": "ERROR", "expected": expected_status, "passed": False, "error": str(ex)})
            all_passed = False

    print("\n" + "=" * 80)
    print(f"Total Tests: {len(tests)}, All Passed: {all_passed}")
    print("=" * 80)
    return all_passed, results

if __name__ == "__main__":
    passed, res = test_api_endpoints()
    import sys
    sys.exit(0 if passed else 1)
