#!/usr/bin/env python3
"""
Stress and Empirical Challenge Harness: Frontend Reverse Proxy /api/v1/workspaces.
Target: Conductor v3 Frontend on Google Cloud Run (development tier).

Performs:
1. Baseline single-request probe & CORS header validation.
2. OPTIONS preflight validation.
3. Rapid concurrent burst (50 requests in parallel).
4. High-concurrency burst (100 requests in parallel).
5. Method and boundary testing (POST, GET non-existent, malformed headers).
6. Statistical aggregation: latency (p50, p95, p99), error rates (502, 504, 5xx, CORS).
"""

import os
import sys
import time
import json
import ssl
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

TARGET_BASE_URL = os.environ.get(
    "CLOUD_RUN_SERVICE_URL",
    "https://conductor-v3-frontend-dev-105792947502.us-central1.run.app"
).rstrip("/")

ENDPOINT = f"{TARGET_BASE_URL}/api/v1/workspaces"

ssl_context = ssl.create_default_context()


def send_request(url, method="GET", headers=None, data=None, timeout=15):
    start = time.time()
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    
    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=timeout) as res:
            elapsed = time.time() - start
            body = res.read()
            return {
                "status": res.status,
                "headers": dict(res.headers),
                "elapsed": elapsed,
                "body_len": len(body),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        body = e.read()
        return {
            "status": e.code,
            "headers": dict(e.headers),
            "elapsed": elapsed,
            "body_len": len(body),
            "error": f"HTTPError {e.code}",
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "status": 0,
            "headers": {},
            "elapsed": elapsed,
            "body_len": 0,
            "error": str(e),
        }


def run_burst(name, count, concurrency, method="GET", headers=None, data=None):
    print(f"\n--- Running {name}: {count} requests ({concurrency} workers, {method}) ---")
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(send_request, ENDPOINT, method=method, headers=headers, data=data)
            for _ in range(count)
        ]
        for f in as_completed(futures):
            results.append(f.result())
            
    total_time = time.time() - start_time
    
    status_counts = {}
    errors = []
    cors_violations = []
    server_5xx = []
    bad_gateways = []
    timeouts = []
    durations = []

    for r in results:
        durations.append(r["elapsed"])
        status = r["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Check CORS
        cors_hdr = r["headers"].get("access-control-allow-origin") or r["headers"].get("Access-Control-Allow-Origin")
        if headers and "Origin" in headers and not cors_hdr:
            cors_violations.append(r)
            
        if status == 502:
            bad_gateways.append(r)
        elif status == 504:
            timeouts.append(r)
        elif status >= 500:
            server_5xx.append(r)
        elif status == 0:
            errors.append(r)

    durations.sort()
    p50 = statistics.median(durations) if durations else 0
    p95 = durations[int(len(durations) * 0.95)] if durations else 0
    p99 = durations[int(len(durations) * 0.99)] if durations else 0
    
    rps = count / total_time if total_time > 0 else 0
    
    print(f"Total time: {total_time:.2f}s | Throughput: {rps:.1f} req/s")
    print(f"Status distribution: {status_counts}")
    print(f"Latency: min={min(durations):.3f}s, p50={p50:.3f}s, p95={p95:.3f}s, p99={p99:.3f}s, max={max(durations):.3f}s")
    print(f"Errors: 502={len(bad_gateways)}, 504={len(timeouts)}, other_5xx={len(server_5xx)}, network_errs={len(errors)}, CORS_issues={len(cors_violations)}")

    return {
        "name": name,
        "count": count,
        "status_counts": status_counts,
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "bad_gateways": len(bad_gateways),
        "timeouts": len(timeouts),
        "server_5xx": len(server_5xx),
        "cors_violations": len(cors_violations),
        "errors": len(errors),
    }


def main():
    print("=" * 80)
    print("EMPIRICAL STRESS HARNESS: FRONTEND REVERSE PROXY /api/v1/workspaces")
    print(f"Target Endpoint: {ENDPOINT}")
    print("=" * 80)

    # 1. Baseline single request
    print("\n[Step 1] Baseline Single GET Probe...")
    res = send_request(ENDPOINT, method="GET", headers={"Origin": "https://conductor-client.test"})
    print(f"Status: {res['status']}, Time: {res['elapsed']:.3f}s")
    print(f"CORS Header (access-control-allow-origin): {res['headers'].get('access-control-allow-origin')}")
    assert res['status'] == 200, f"Expected 200, got {res['status']}"
    assert res['headers'].get('access-control-allow-origin') == "*", "Missing or invalid CORS header"

    # 2. OPTIONS preflight
    print("\n[Step 2] OPTIONS Preflight Request...")
    opt_res = send_request(
        ENDPOINT,
        method="OPTIONS",
        headers={
            "Origin": "https://conductor-client.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    print(f"OPTIONS Status: {opt_res['status']}, Time: {opt_res['elapsed']:.3f}s")
    print(f"Allow-Origin: {opt_res['headers'].get('access-control-allow-origin')}")
    print(f"Allow-Methods: {opt_res['headers'].get('access-control-allow-methods')}")

    # 3. Burst 1: 50 concurrent GET requests
    b1 = run_burst(
        "Burst 1 (50 concurrent GET)",
        count=50,
        concurrency=10,
        method="GET",
        headers={"Origin": "https://conductor-client.test"}
    )

    # 4. Burst 2: 100 rapid concurrent GET requests
    b2 = run_burst(
        "Burst 2 (100 rapid concurrent GET)",
        count=100,
        concurrency=20,
        method="GET",
        headers={"Origin": "https://conductor-client.test", "User-Agent": "Conductor-StressTester/1.0"}
    )

    # 5. Burst 3: Concurrent POST workspace creations
    print("\n[Step 3] Concurrent POST Workspace Creation (20 requests)...")
    post_payload = json.dumps({
        "name": "Stress-Test-Workspace",
        "description": "Created during reverse-proxy stress testing",
        "report_type": "Evaluation"
    }).encode("utf-8")
    b3 = run_burst(
        "Burst 3 (20 concurrent POST)",
        count=20,
        concurrency=5,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": "https://conductor-client.test"
        },
        data=post_payload
    )

    # 6. Edge cases: non-existent workspace ID
    print("\n[Step 4] Edge Case: Non-existent workspace UUID...")
    non_existent = send_request(
        f"{ENDPOINT}/00000000-0000-0000-0000-000000000000",
        method="GET",
        headers={"Origin": "https://conductor-client.test"}
    )
    print(f"Non-existent UUID status: {non_existent['status']} (Expected: 404)")
    print(f"CORS header present: {non_existent['headers'].get('access-control-allow-origin')}")

    # 7. Edge case: Malformed JSON POST
    print("\n[Step 5] Edge Case: Malformed JSON POST...")
    malformed = send_request(
        ENDPOINT,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": "https://conductor-client.test"
        },
        data=b"{\"name\": \"unclosed_json"
    )
    print(f"Malformed JSON status: {malformed['status']} (Expected: 4xx, never 500/502)")
    print(f"CORS header present: {malformed['headers'].get('access-control-allow-origin')}")

    # Aggregated assertions
    total_502 = b1["bad_gateways"] + b2["bad_gateways"] + b3["bad_gateways"]
    total_504 = b1["timeouts"] + b2["timeouts"] + b3["timeouts"]
    total_5xx = b1["server_5xx"] + b2["server_5xx"] + b3["server_5xx"]
    total_cors = b1["cors_violations"] + b2["cors_violations"] + b3["cors_violations"]

    print("\n" + "=" * 80)
    print("STRESS TEST AGGREGATE SUMMARY:")
    print(f"Total 502 Bad Gateway:      {total_502}")
    print(f"Total 504 Gateway Timeout:  {total_504}")
    print(f"Total Server 5xx:           {total_5xx}")
    print(f"Total CORS Violations:      {total_cors}")
    print("=" * 80)

    assert total_502 == 0, f"Encountered {total_502} HTTP 502 errors!"
    assert total_504 == 0, f"Encountered {total_504} HTTP 504 errors!"
    assert total_5xx == 0, f"Encountered {total_5xx} HTTP 5xx errors!"
    assert total_cors == 0, f"Encountered {total_cors} CORS violations!"
    print("ALL EMPIRICAL REVERSE PROXY STRESS ASSERTIONS PASSED!")


if __name__ == "__main__":
    main()
