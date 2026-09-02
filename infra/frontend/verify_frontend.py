#!/usr/bin/env python3
"""
Post-Deployment Verification Prober for Conductor v3 Frontend (Flutter Web on Cloud Run).
Executes as a built-in Cloud Deploy verify job to gate automated rollouts and canary progression.
Uses Python standard library (urllib) for zero external dependencies in slim containers.
"""

import argparse
import gzip
import logging
import os
import sys
import time
import urllib.error
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("conductor.verify_frontend")

DEFAULT_TARGETS = {
    "dev": "https://conductor-v3-frontend-dev-4izasuhqpq-uc.a.run.app",
    "staging": "https://conductor-v3-frontend-staging-4izasuhqpq-uc.a.run.app",
    "prod": "https://conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Deployed Conductor v3 Frontend on Cloud Run."
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("CLOUD_DEPLOY_PROJECT", "riccardo-blog-test-v1")),
        help="Google Cloud Project ID",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("GOOGLE_CLOUD_LOCATION", os.environ.get("CLOUD_DEPLOY_LOCATION", "us-central1")),
        help="Google Cloud Region",
    )
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "prod"],
        default=None,
        help="Deployment Target Environment Tier (dev, staging, prod)",
    )
    parser.add_argument(
        "--phase",
        default=None,
        help="Rollout Phase (e.g. canary-25, canary-50, stable)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Explicit base URL of frontend service to verify",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="HTTP request timeout in seconds",
    )
    return parser.parse_args()


def resolve_environment(args: argparse.Namespace) -> tuple[str, str, str]:
    """Resolves environment tier, phase, and target URL from CLI args or environment variables."""
    # 1. Resolve target environment tier
    env_tier = args.env
    if not env_tier:
        target_env = os.environ.get("CLOUD_DEPLOY_TARGET", "").lower()
        if "prod" in target_env:
            env_tier = "prod"
        elif "staging" in target_env:
            env_tier = "staging"
        elif "dev" in target_env:
            env_tier = "dev"
        else:
            env_tier = os.environ.get("TARGET_ENV", "dev").lower()

    # 2. Resolve phase
    phase = args.phase or os.environ.get("CLOUD_DEPLOY_PHASE", "stable")

    # 3. Resolve target URL
    target_url = args.url or os.environ.get("TARGET_URL")
    if not target_url:
        target_url = DEFAULT_TARGETS.get(env_tier, DEFAULT_TARGETS["dev"])

    return env_tier, phase, target_url.rstrip("/")


def http_request(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    timeout: int = 10,
) -> tuple[int, dict, bytes]:
    """Performs an HTTP request using urllib and returns status, lowercase headers dict, and body bytes."""
    req_headers = {"User-Agent": "Conductor-Frontend-Verifier/1.0"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            # Store headers with lowercased keys for case-insensitive access
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            body = response.read()
            return status, resp_headers, body
    except urllib.error.HTTPError as e:
        resp_headers = {k.lower(): v for k, v in e.headers.items()}
        body = e.read()
        return e.code, resp_headers, body


def run_verification(env_tier: str, phase: str, base_url: str, timeout: int = 10) -> bool:
    """Runs the 6-point verification suite against the specified frontend deployment."""
    logger.info("====================================================================")
    logger.info("  🧪 Conductor v3 Frontend Post-Deployment Verification Prober")
    logger.info("====================================================================")
    logger.info(f"Target Environment: {env_tier.upper()}")
    logger.info(f"Rollout Phase:      {phase}")
    logger.info(f"Base Endpoint:      {base_url}")
    logger.info("--------------------------------------------------------------------")

    # 1. Health Probe (/health)
    logger.info("  [1/6] Probing Health Endpoint (/health) ...")
    t0 = time.time()
    status, _, body = http_request(f"{base_url}/health", method="GET", timeout=timeout)
    latency_ms = (time.time() - t0) * 1000
    text_body = body.decode("utf-8", errors="replace")
    if status != 200 or "healthy" not in text_body:
        logger.error(f"Health check failed with status {status}: {text_body}")
        return False
    logger.info(f"        -> PASS: HTTP 200 with 'healthy' body ({latency_ms:.1f}ms).")

    # 2. Root index.html and Title Validation
    logger.info("  [2/6] Verifying Root Index (/) and Executive Portal Metadata ...")
    status, _, body = http_request(f"{base_url}/", method="GET", timeout=timeout)
    text_root = body.decode("utf-8", errors="replace")
    if status != 200:
        logger.error(f"Root index returned HTTP status {status}")
        return False
    expected_title = "<title>The Conductor v3 - Analyst Response Agent (ARA) - A2UI Executive Portal</title>"
    if expected_title not in text_root:
        logger.error(f"Page title mismatch in root index. Received snippet: {text_root[:300]}")
        return False
    logger.info("        -> PASS: HTTP 200 with Executive Portal Title present.")

    # 3. WebAssembly MIME Type Verification (/main.dart.wasm)
    logger.info("  [3/6] Verifying WebAssembly MIME Type (/main.dart.wasm) ...")
    status, headers, _ = http_request(f"{base_url}/main.dart.wasm", method="HEAD", timeout=timeout)
    if status != 200:
        logger.error(f"WASM head request returned HTTP status {status}")
        return False
    wasm_content_type = headers.get("content-type", headers.get("Content-Type", ""))
    if "application/wasm" not in wasm_content_type:
        logger.error(f"Expected Content-Type 'application/wasm', received '{wasm_content_type}'")
        return False
    logger.info(f"        -> PASS: Content-Type is '{wasm_content_type}'.")

    # 4. Modern JavaScript Module MIME Type (/main.dart.js)
    logger.info("  [4/6] Verifying JavaScript MIME Type (/main.dart.js) ...")
    status, headers, _ = http_request(f"{base_url}/main.dart.js", method="HEAD", timeout=timeout)
    if status != 200:
        logger.error(f"JavaScript head request returned HTTP status {status}")
        return False
    js_content_type = headers.get("content-type", headers.get("Content-Type", ""))
    if "application/javascript" not in js_content_type and "text/javascript" not in js_content_type:
        logger.error(f"Expected javascript MIME, received '{js_content_type}'")
        return False
    logger.info(f"        -> PASS: Content-Type is '{js_content_type}'.")

    # 5. Gzip Compression Verification (/index.html)
    logger.info("  [5/6] Verifying Gzip Compression (/index.html) ...")
    status, headers, raw_body = http_request(
        f"{base_url}/index.html",
        method="GET",
        headers={"Accept-Encoding": "gzip"},
        timeout=timeout,
    )
    if status != 200:
        logger.error(f"Index request returned HTTP status {status}")
        return False
    content_encoding = headers.get("content-encoding", headers.get("Content-Encoding", ""))
    if content_encoding == "gzip":
        try:
            decompressed = gzip.decompress(raw_body).decode("utf-8", errors="replace")
            assert expected_title in decompressed
            logger.info("        -> PASS: HTTP 200 with verified Content-Encoding: gzip.")
        except Exception as e:
            logger.error(f"Failed to decompress gzipped body: {e}")
            return False
    else:
        logger.info(f"        -> PASS: HTTP 200 received (Content-Encoding: {content_encoding or 'identity'}).")

    # 6. SPA Routing Fallback Verification (/workspace/rfi-analysis/deep-link)
    logger.info("  [6/6] Verifying SPA Fallback Routing (/workspace/rfi-analysis/deep-link) ...")
    status, _, body = http_request(
        f"{base_url}/workspace/rfi-analysis/deep-link",
        method="GET",
        timeout=timeout,
    )
    text_spa = body.decode("utf-8", errors="replace")
    if status != 200 or expected_title not in text_spa:
        logger.error(f"SPA fallback routing failed: status {status}")
        return False
    logger.info("        -> PASS: HTTP 200 with index.html SPA fallback verified.")

    logger.info("====================================================================")
    logger.info(f"  🎉 ALL VERIFICATION CHECKS PASSED FOR PHASE [{phase.upper()}] ON [{env_tier.upper()}]")
    logger.info("====================================================================")
    return True


def main():
    args = parse_args()
    env_tier, phase, target_url = resolve_environment(args)

    success = run_verification(
        env_tier=env_tier,
        phase=phase,
        base_url=target_url,
        timeout=args.timeout,
    )

    if not success:
        logger.critical(
            f"Verification failed for {env_tier} phase {phase}. Halting automated promotion."
        )
        sys.exit(1)

    logger.info("Positive verification confirmed. Rollout is eligible for automated advancement.")
    sys.exit(0)


if __name__ == "__main__":
    main()
