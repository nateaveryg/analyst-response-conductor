"""
Hermetic & Integration Tests for Agent Platform Agent Gateway.
Covers:
1. Declarative manifest syntax and schema validation.
2. Ingress routing to Vertex AI Agent Engine microservice.
3. Inline Model Armor DLP redaction (partner discount 45%, margins, SSN, external emails, injection blocking).
4. CORS preflight OPTIONS resolution (HTTP 204 No Content).
5. Agent Identity attestation and Cloud Trace propagation.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import pytest
import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GATEWAY_DIR = os.path.join(REPO_ROOT, "infra", "gateway")
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
BINARY_PATH = os.path.join(BACKEND_DIR, "conductor-server")
PYTHON_BIN = os.path.join(REPO_ROOT, ".venv", "bin", "python3")
if not os.path.exists(PYTHON_BIN):
    PYTHON_BIN = sys.executable


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def test_manifest_validation():
    """Validates declarative YAML manifests using deploy_gateway.py --validate-only."""
    deploy_script = os.path.join(GATEWAY_DIR, "deploy_gateway.py")
    res = subprocess.run(
        [PYTHON_BIN, deploy_script, "--validate-only", "--manifest-dir", GATEWAY_DIR],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Manifest validation failed: {res.stderr}"


def test_gateway_dry_run_deployment():
    """Validates dry-run deployment and generation of deployed_gateway.json & results.json."""
    deploy_script = os.path.join(GATEWAY_DIR, "deploy_gateway.py")
    res = subprocess.run(
        [PYTHON_BIN, deploy_script, "--dry-run", "--manifest-dir", GATEWAY_DIR],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Dry-run deployment failed: {res.stderr}"

    deployed_file = os.path.join(GATEWAY_DIR, "deployed_gateway.json")
    results_file = os.path.join(GATEWAY_DIR, "results.json")
    assert os.path.exists(deployed_file), "deployed_gateway.json not generated"
    assert os.path.exists(results_file), "results.json not generated"

    with open(deployed_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["governed_access_path"] == "CLIENT_TO_AGENT"
    assert data["project"] == "riccardo-blog-test-v1"
    assert data["location"] == "us-central1"


@pytest.fixture(scope="module")
def gateway_environment():
    """Spins up Go backend server and Agent Gateway for integration testing."""
    if not os.path.exists(BINARY_PATH):
        build_res = subprocess.run(["go", "build", "-o", BINARY_PATH, "./cmd/server"], cwd=BACKEND_DIR, capture_output=True, text=True)
        assert build_res.returncode == 0, f"Failed to build Go binary: {build_res.stderr}"

    backend_port = find_free_port()
    gateway_port = find_free_port()
    backend_url = f"http://127.0.0.1:{backend_port}"
    gateway_url = f"http://127.0.0.1:{gateway_port}"

    env = os.environ.copy()
    env["PORT"] = str(backend_port)
    env["ENVIRONMENT"] = "test"
    env["VERTEX_AI_PROJECT"] = "riccardo-blog-test-v1"
    env["VERTEX_AI_LOCATION"] = "us-central1"
    env["VERTEX_AI_MODEL"] = "gemini-3.5-flash"
    env["SECURITY_SECRET_KEY"] = "conductor-v3-e2e-test-secret-key-32bytes!!"

    backend_proc = subprocess.Popen(
        [BINARY_PATH],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for backend
    ready = False
    for _ in range(30):
        try:
            r = requests.get(f"{backend_url}/health", timeout=1.0)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)
    if not ready:
        backend_proc.kill()
        raise RuntimeError("Go backend failed to respond on /health")

    # Start Gateway
    gw_cmd = [
        PYTHON_BIN,
        os.path.join(GATEWAY_DIR, "gateway_service.py"),
        "--port", str(gateway_port),
        "--backend-url", backend_url,
        "--project", "riccardo-blog-test-v1",
        "--location", "us-central1",
        "--gateway-id", "conductor-v3-ingress-gateway",
    ]
    gateway_proc = subprocess.Popen(
        gw_cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    gw_ready = False
    for _ in range(40):
        try:
            r = requests.get(f"{gateway_url}/health", timeout=1.0)
            if r.status_code == 200:
                gw_ready = True
                break
        except Exception:
            time.sleep(0.1)
    if not gw_ready:
        gateway_proc.kill()
        backend_proc.kill()
        raise RuntimeError("Agent Gateway failed to respond on /health")

    yield {"gateway_url": gateway_url, "backend_url": backend_url}

    gateway_proc.terminate()
    backend_proc.terminate()
    try:
        gateway_proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        gateway_proc.kill()
    try:
        backend_proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        backend_proc.kill()


def test_cors_options_preflight(gateway_environment):
    """Verifies preflight OPTIONS requests return HTTP 204 No Content with CORS headers."""
    gw_url = gateway_environment["gateway_url"]
    for path in ["/query", "/streamQuery", "/getAgentCard", "/api/v1/a2ui/chat"]:
        res = requests.options(
            f"{gw_url}{path}",
            headers={
                "Origin": "https://conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization, X-Cloud-Trace-Context",
            },
            timeout=5.0,
        )
        assert res.status_code == 204
        assert res.headers.get("Access-Control-Allow-Origin") == "*"
        assert "OPTIONS" in res.headers.get("Access-Control-Allow-Methods", "")
        assert "Content-Type" in res.headers.get("Access-Control-Allow-Headers", "")


def test_model_armor_dlp_partner_discount(gateway_environment):
    """Verifies confidential partner discount 45% is masked to [CONFIDENTIAL_COMMERCIAL_RATE]."""
    gw_url = gateway_environment["gateway_url"]
    payload = {"prompt": "Please confirm the secret partner discount is 45% for this bid."}
    res = requests.post(f"{gw_url}/query", json=payload, timeout=5.0)
    assert res.status_code == 200
    assert "45%" not in res.text
    assert "[CONFIDENTIAL_COMMERCIAL_RATE]" in res.text


def test_model_armor_dlp_internal_margin(gateway_environment):
    """Verifies internal margin (72%) is masked to [CONFIDENTIAL_COMMERCIAL_RATE]."""
    gw_url = gateway_environment["gateway_url"]
    payload = {"prompt": "Our financial summary: internal margin is 72%."}
    res = requests.post(f"{gw_url}/query", json=payload, timeout=5.0)
    assert res.status_code == 200
    assert "72%" not in res.text
    assert "[CONFIDENTIAL_COMMERCIAL_RATE]" in res.text


def test_model_armor_dlp_ssn(gateway_environment):
    """Verifies Social Security Numbers are masked to [REDACTED_SSN]."""
    gw_url = gateway_environment["gateway_url"]
    payload = {"prompt": "Executive contact SSN is 000-12-3456."}
    res = requests.post(f"{gw_url}/query", json=payload, timeout=5.0)
    assert res.status_code == 200
    assert "000-12-3456" not in res.text
    assert "[REDACTED_SSN]" in res.text


def test_model_armor_dlp_email_pii(gateway_environment):
    """Verifies external emails are sanitized to [REDACTED_PII] while @google.com is preserved."""
    gw_url = gateway_environment["gateway_url"]
    payload = {"prompt": "Contact internal engineer engineer@google.com or external vendor external@acme.com"}
    res = requests.post(f"{gw_url}/query", json=payload, timeout=5.0)
    assert res.status_code == 200
    assert "engineer@google.com" in res.text
    assert "external@acme.com" not in res.text
    assert "[REDACTED_PII]" in res.text


def test_model_armor_dlp_injection_blocked(gateway_environment):
    """Verifies malicious SQL injection is blocked with HTTP 400 (failOpen: false)."""
    gw_url = gateway_environment["gateway_url"]
    payload = {"prompt": "SELECT * FROM users; DROP TABLE accounts; --"}
    res = requests.post(f"{gw_url}/query", json=payload, timeout=5.0)
    assert res.status_code == 400
    assert "BLOCKED_BY_MODEL_ARMOR" in res.text


def test_agent_attestation_and_telemetry(gateway_environment):
    """Verifies agent identity attestation and Cloud Trace context propagation."""
    gw_url = gateway_environment["gateway_url"]
    trace_ctx = "105445aa5ecd4891aab73000d3305580/12345;o=1"
    headers = {"X-Cloud-Trace-Context": trace_ctx}
    res = requests.get(f"{gw_url}/getAgentCard", headers=headers, timeout=5.0)
    assert res.status_code == 200
    assert res.headers.get("X-Agent-Identity") == "conductor-v3-ara@riccardo-blog-test-v1.iam.gserviceaccount.com"
    assert "conductor-v3-ingress-gateway" in res.headers.get("X-Governed-By", "")
    assert "105445aa5ecd4891aab73000d3305580" in res.headers.get("X-Cloud-Trace-Context", "")


def test_streaming_query_chunk_dlp(gateway_environment):
    """Verifies SSE streaming chunks are dynamically sanitized by Model Armor DLP."""
    gw_url = gateway_environment["gateway_url"]
    payload = {"prompt": "Stream secret partner discount is 45% and SSN 000-12-3456"}
    res = requests.post(f"{gw_url}/streamQuery", json=payload, stream=True, timeout=10.0)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")

    stream_content = ""
    for line in res.iter_lines(decode_unicode=True):
        if line:
            stream_content += line + "\n"

    assert "45%" not in stream_content
    assert "000-12-3456" not in stream_content
    assert "[CONFIDENTIAL_COMMERCIAL_RATE]" in stream_content
    assert "[REDACTED_SSN]" in stream_content


def test_decoupled_frontend_traversal(gateway_environment):
    """Verifies decoupled frontend Nginx reverse proxy traversal to Agent Gateway."""
    gw_url = gateway_environment["gateway_url"]
    frontend_headers = {
        "Host": "conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app",
        "X-Forwarded-For": "198.51.100.22",
        "X-User-Email": "analyst@google.com",
    }
    res = requests.post(
        f"{gw_url}/api/v1/a2ui/chat",
        json={"message": "Evaluate enterprise cloud compliance", "action_id": "open_intake"},
        headers=frontend_headers,
        timeout=10.0,
    )
    assert res.status_code == 200
    assert "response" in res.json() or "response_text" in res.json()
    assert res.headers.get("Access-Control-Allow-Origin") == "*"
    assert res.headers.get("X-Agent-Identity") is not None
