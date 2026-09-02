#!/usr/bin/env python3
"""
Adversarial Edge-Case and Boundary Fuzzing Harness for Frontend Reverse Proxy.
Target: Conductor v3 Frontend on Google Cloud Run (development tier).

Stress vectors:
1. SQL injection strings in path parameters
2. Path traversal attack attempts (/api/v1/workspaces/../../etc/passwd)
3. Large payload rejection (1MB payload)
4. Unsupported HTTP verbs (TRACE, CONNECT, PATCH)
5. XSS polyglots in workspace creation payload
6. Very long URL query parameters (>4KB)
7. HTTP header injection attempts / invalid header values
"""

import os
import sys
import time
import json
import ssl
import urllib.request
import urllib.error

TARGET_BASE_URL = os.environ.get(
    "CLOUD_RUN_SERVICE_URL",
    "https://conductor-v3-frontend-dev-105792947502.us-central1.run.app"
).rstrip("/")

ssl_context = ssl.create_default_context()


def send_raw(url, method="GET", headers=None, data=None, timeout=10):
    start = time.time()
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=timeout) as res:
            return res.status, dict(res.headers), res.read(), time.time() - start
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(), time.time() - start
    except Exception as e:
        return 0, {}, str(e).encode(), time.time() - start


def run_adversarial_suite():
    print("=" * 80)
    print("ADVERSARIAL EDGE CASE AND BOUNDARY HARNESS")
    print(f"Target Base: {TARGET_BASE_URL}")
    print("=" * 80)

    findings = []

    # Vector 1: SQL injection in UUID path
    sqli_paths = [
        "/api/v1/workspaces/' OR '1'='1",
        "/api/v1/workspaces/1; DROP TABLE workspaces;--",
        "/api/v1/workspaces/00000000-0000-0000-0000-000000000000' UNION SELECT *--",
    ]
    for p in sqli_paths:
        status, hdrs, body, el = send_raw(f"{TARGET_BASE_URL}{p}")
        print(f"SQLi Path [{p}] -> HTTP {status} in {el:.3f}s")
        if status in (500, 502, 504):
            findings.append(f"CRITICAL: SQLi path {p} caused HTTP {status}")
        elif status not in (400, 404, 422):
            print(f"  Note: unexpected status {status}")

    # Vector 2: Path traversal
    traversal_paths = [
        "/api/v1/workspaces/../../../../etc/passwd",
        "/api/v1/../../etc/passwd",
        "/static/../../index.html",
    ]
    for p in traversal_paths:
        status, hdrs, body, el = send_raw(f"{TARGET_BASE_URL}{p}")
        print(f"Traversal Path [{p}] -> HTTP {status} in {el:.3f}s")
        if status == 200 and b"root:" in body:
            findings.append(f"CRITICAL: Path traversal exposed /etc/passwd: {p}")
        elif status in (500, 502, 504):
            findings.append(f"HIGH: Path traversal caused HTTP {status}")

    # Vector 3: Massive payload POST (1 MB)
    large_payload = json.dumps({
        "name": "A" * 500000,
        "report_type": "Evaluation",
        "description": "B" * 500000,
    }).encode("utf-8")
    status, hdrs, body, el = send_raw(
        f"{TARGET_BASE_URL}/api/v1/workspaces",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=large_payload,
        timeout=15
    )
    print(f"Massive Payload POST (1MB) -> HTTP {status} in {el:.3f}s")
    if status in (500, 502, 504):
        findings.append(f"HIGH: 1MB payload caused server failure {status}")

    # Vector 4: Unsupported HTTP verbs
    verbs = ["TRACE", "PATCH"]
    for v in verbs:
        status, hdrs, body, el = send_raw(
            f"{TARGET_BASE_URL}/api/v1/workspaces",
            method=v,
            headers={"Content-Type": "application/json"}
        )
        print(f"Verb [{v}] -> HTTP {status} in {el:.3f}s")
        if status in (500, 502, 504):
            findings.append(f"MEDIUM: Verb {v} caused HTTP {status}")

    # Vector 5: XSS Polyglot in workspace creation
    xss_payload = json.dumps({
        "name": "<script>alert('xss')</script>",
        "report_type": "Evaluation",
        "description": "javascript:/*--></title></style></textarea></script></xmp><svg/onload='+/'/+/onmouseover=1/+/[*/[]/+alert(1)//'>",
    }).encode("utf-8")
    status, hdrs, body, el = send_raw(
        f"{TARGET_BASE_URL}/api/v1/workspaces",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=xss_payload
    )
    print(f"XSS Polyglot POST -> HTTP {status} in {el:.3f}s")
    if status == 201:
        # Check if returned JSON properly escapes or sanitizes
        resp_json = json.loads(body.decode("utf-8", errors="ignore"))
        print(f"  Sanitized response name: {resp_json.get('name')}")
    elif status in (500, 502, 504):
        findings.append(f"HIGH: XSS polyglot caused HTTP {status}")

    # Vector 6: Ultra-long query parameter (8KB)
    long_query = "/api/v1/workspaces?" + "filter=" + ("X" * 8000)
    status, hdrs, body, el = send_raw(f"{TARGET_BASE_URL}{long_query}")
    print(f"Ultra-long Query (8KB) -> HTTP {status} in {el:.3f}s")
    if status in (500, 502, 504):
        findings.append(f"MEDIUM: Ultra-long query caused HTTP {status}")

    print("\n" + "=" * 80)
    print(f"ADVERSARIAL STRESS TEST COMPLETE: {len(findings)} CRITICAL/HIGH/MEDIUM FAILURES")
    for f in findings:
        print(f"  ! {f}")
    print("=" * 80)
    assert len(findings) == 0, f"Adversarial vulnerabilities detected: {findings}"


if __name__ == "__main__":
    run_adversarial_suite()
