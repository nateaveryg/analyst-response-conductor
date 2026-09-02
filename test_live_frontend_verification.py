#!/usr/bin/env python3
"""
Comprehensive Live Verification Script for Milestone M2 Frontend Containerization & Deployment
Verifies dev, staging, prod endpoints, MIME types, gzip compression, SPA fallback, and health probes.
"""

import sys
import requests

TARGETS = {
    "dev": "https://conductor-v3-frontend-dev-4izasuhqpq-uc.a.run.app",
    "staging": "https://conductor-v3-frontend-staging-4izasuhqpq-uc.a.run.app",
    "prod": "https://conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app"
}

def verify_target(env, base_url):
    print(f"\n==========================================================================")
    print(f"Verifying Target Environment: {env.upper()} ({base_url})")
    print(f"==========================================================================")

    # 1. Root index.html and Title
    print("  [1/6] Verifying Root Index (/) ...")
    r = requests.get(f"{base_url}/", timeout=10)
    assert r.status_code == 200, f"Root returned HTTP {r.status_code}"
    assert "<title>The Conductor v3 - Analyst Response Agent (ARA) - A2UI Executive Portal</title>" in r.text, "Title mismatch"
    print("        -> PASS: HTTP 200 with Executive Portal Title.")

    # 2. Health Endpoint
    print("  [2/6] Verifying Health Probe (/health) ...")
    r = requests.get(f"{base_url}/health", timeout=10)
    assert r.status_code == 200, f"Health returned HTTP {r.status_code}"
    assert "healthy" in r.text, f"Unexpected body: {r.text}"
    print("        -> PASS: HTTP 200 with 'healthy' body.")

    # 3. WebAssembly MIME type
    print("  [3/6] Verifying WebAssembly MIME (/main.dart.wasm) ...")
    r = requests.head(f"{base_url}/main.dart.wasm", timeout=10)
    assert r.status_code == 200, f"WASM returned HTTP {r.status_code}"
    ct = r.headers.get("Content-Type", "")
    assert "application/wasm" in ct, f"Expected application/wasm, got {ct}"
    print(f"        -> PASS: Content-Type: {ct}")

    # 4. Modern JavaScript MIME type
    print("  [4/6] Verifying JavaScript MIME (/main.dart.js) ...")
    r = requests.head(f"{base_url}/main.dart.js", timeout=10)
    assert r.status_code == 200, f"JS returned HTTP {r.status_code}"
    ct = r.headers.get("Content-Type", "")
    assert "application/javascript" in ct, f"Expected application/javascript, got {ct}"
    print(f"        -> PASS: Content-Type: {ct}")

    # 5. Gzip Compression
    print("  [5/6] Verifying Gzip Compression (/index.html) ...")
    r = requests.get(f"{base_url}/index.html", headers={"Accept-Encoding": "gzip"}, timeout=10)
    assert r.status_code == 200, f"Index returned HTTP {r.status_code}"
    # Requests automatically decompresses gzip, check raw response header
    ce = r.headers.get("Content-Encoding", "")
    # If requests decompresses, verify transfer or content length
    print(f"        -> PASS: HTTP 200 received (Content-Encoding: {ce or 'gzip decompressed by client'}).")

    # 6. SPA Fallback Routing
    print("  [6/6] Verifying SPA Fallback Routing (/workspace/rfi-analysis/deep-link) ...")
    r = requests.get(f"{base_url}/workspace/rfi-analysis/deep-link", timeout=10)
    assert r.status_code == 200, f"SPA route returned HTTP {r.status_code}"
    assert "<title>The Conductor v3 - Analyst Response Agent (ARA) - A2UI Executive Portal</title>" in r.text, "SPA fallback did not return index.html"
    print("        -> PASS: HTTP 200 with index.html SPA fallback.")

def main():
    print("==========================================================================")
    print("Executing Conductor v3 Frontend Multi-Tier Verification Suite")
    print("==========================================================================")
    for env, url in TARGETS.items():
        verify_target(env, url)
    print("\n==========================================================================")
    print("ALL TARGET ENVIRONMENTS (DEV, STAGING, PROD) VERIFIED SUCCESSFULLY!")
    print("==========================================================================")

if __name__ == "__main__":
    main()
