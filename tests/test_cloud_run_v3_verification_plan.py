"""Test suite validating the Conductor v3 Cloud Run Verification & Promotion Plan deliverable."""

import http.server
import os
import re
import subprocess
import threading
import pytest
import yaml

DOC_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "cloud_run_v3_verification_and_promotion_plan.md")
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "infra", "cloudrun", "verify_cloudrun_v3.sh")


def test_document_exists_and_is_non_empty():
    """AC1: Document docs/cloud_run_v3_verification_and_promotion_plan.md exists and is non-empty."""
    assert os.path.exists(DOC_PATH), f"Deliverable doc missing at {DOC_PATH}"
    size = os.path.getsize(DOC_PATH)
    assert size > 2000, f"Document is too small ({size} bytes)"


def test_identifies_missing_stanzas():
    """AC2: Identifies missing verify stanza in skaffold-v3.yaml and absent Automation resource in clouddeploy-v3.yaml."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "skaffold-v3.yaml" in content
    assert "clouddeploy-v3.yaml" in content
    assert "verify" in content.lower()
    assert "automation" in content.lower()
    assert "promotereleaserule" in content.lower()


def test_verification_tiers_specification():
    """AC3: Verification design details exact container images, probe commands, target endpoints, and failure exit codes for all 3 verification tiers."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Container image
    assert "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" in content

    # Target endpoints
    assert "/healthz" in content
    assert "/version.json" in content
    assert "/query" in content

    # Failure exit codes
    assert "101" in content  # Tier 1 health failure
    assert "102" in content  # Tier 2 version mismatch
    assert "103" in content  # Tier 2 marker mismatch
    assert "104" in content  # Tier 2 unreachable/malformed
    assert "105" in content  # Tier 3 auth token failure
    assert "106" in content  # Tier 3 query failure
    assert "107" in content  # Tier 3 Model Armor DLP leak
    assert "108" in content  # Tier 3 Model Armor injection block failure

    # Model Armor DLP checks
    assert "Model Armor" in content
    assert "000-12-3456" in content
    assert "45%" in content
    assert "DROP TABLE" in content or "injection" in content.lower()


def test_cloud_deploy_automation_syntax():
    """AC4: Promotion plan defines valid Cloud Deploy Automation resource syntax targeting staging with wait: 0s post-verification."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "kind: Automation" in content
    assert "promoteReleaseRule" in content
    assert "wait: 0s" in content
    assert 'destinationTargetId: "staging"' in content or 'destinationTargetId: staging' in content


def test_production_governance_and_canary_percentages():
    """AC5: Production rollout policy retains manual approval (requireApproval: true) and enforces progressive deployment sequence of 25%, 50%, and stable."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "requireApproval: true" in content
    assert "25" in content
    assert "50" in content
    assert "stable" in content.lower()
    assert "canaryDeployment" in content


def test_architecture_flow_and_operational_rollbacks():
    """AC6: Architecture flow diagram (Mermaid) and operational rollback procedures are present."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "```mermaid" in content
    assert "flowchart" in content
    assert "gcloud deploy rollbacks create" in content
    assert "gcloud run services update-traffic" in content
    assert "repairRolloutRule" in content


def test_verification_script_executable():
    """Ensures verify_cloudrun_v3.sh is present and executable."""
    assert os.path.exists(SCRIPT_PATH), f"Script missing at {SCRIPT_PATH}"
    assert os.access(SCRIPT_PATH, os.X_OK), "verify_cloudrun_v3.sh is not executable"


def test_backend_go_verification_tiers_pass():
    """Runs Go unit/integration test for verification tiers."""
    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    res = subprocess.run(
        ["go", "test", "-mod=vendor", "-v", "./internal/api", "-run", "TestInPipelineVerificationTiers"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Go tests failed:\n{res.stdout}\n{res.stderr}"
    assert "PASS: TestInPipelineVerificationTiers" in res.stdout


def _run_prober_with_handler(handler_class, extra_env=None):
    """Helper spinning up an ephemeral mock server to run verify_cloudrun_v3.sh."""
    server = http.server.HTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        res = subprocess.run(
            [SCRIPT_PATH, f"http://127.0.0.1:{port}"],
            capture_output=True,
            text=True,
            env=env,
        )
        return res
    finally:
        server.shutdown()


def test_prober_exit_code_101_health_failure():
    """Tier 1: /healthz returning HTTP 500 must trigger exit code 101."""
    class HealthFailHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(500)
            self.end_headers()
        def log_message(self, *a): pass

    res = _run_prober_with_handler(HealthFailHandler)
    assert res.returncode == 101, f"Expected exit 101, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_102_version_mismatch():
    """Tier 2: /version.json returning mismatched version must trigger exit code 102."""
    class VersionMismatchHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": "3.2.0", "verification_marker": "v3.3.2-verified"}')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(VersionMismatchHandler)
    assert res.returncode == 102, f"Expected exit 102, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_103_marker_mismatch():
    """Tier 2: /version.json returning mismatched marker must trigger exit code 103."""
    class MarkerMismatchHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-unverified"}')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(MarkerMismatchHandler)
    assert res.returncode == 103, f"Expected exit 103, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_104_malformed_json():
    """Tier 2: /version.json returning malformed non-JSON payload must trigger exit code 104."""
    class MalformedHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b"<html>Internal Error</html>")
        def log_message(self, *a): pass

    res = _run_prober_with_handler(MalformedHandler)
    assert res.returncode == 104, f"Expected exit 104, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_105_auth_failure():
    """Tier 3: /query returning HTTP 401 Unauthorized must trigger exit code 105."""
    class AuthFailHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers()
            if self.path == "/version.json":
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
        def do_POST(self):
            self.send_response(401); self.end_headers()
        def log_message(self, *a): pass

    res = _run_prober_with_handler(AuthFailHandler)
    assert res.returncode == 105, f"Expected exit 105, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_106_query_failure():
    """Tier 3: /query returning HTTP 500 must trigger exit code 106."""
    class QueryFailHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers()
            if self.path == "/version.json":
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
        def do_POST(self):
            self.send_response(500); self.end_headers()
        def log_message(self, *a): pass

    res = _run_prober_with_handler(QueryFailHandler)
    assert res.returncode == 106, f"Expected exit 106, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_107_dlp_leak():
    """Tier 3: /query leaking unredacted SSN/rate in 3B must trigger exit code 107."""
    class DLPLeakHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers()
            if self.path == "/version.json":
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
        def do_POST(self):
            self.send_response(200); self.end_headers()
            self.wfile.write(b'Leaked SSN 000-12-3456 here')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(DLPLeakHandler)
    assert res.returncode == 107, f"Expected exit 107, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_108_injection_unblocked():
    """Tier 3: /query returning HTTP 200 instead of HTTP 400 on injection must trigger exit code 108."""
    class InjectionFailHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers()
            if self.path == "/version.json":
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
        def do_POST(self):
            # Returns 200 for all queries, failing to block DROP TABLE
            self.send_response(200); self.end_headers()
            self.wfile.write(b'{"response": "accepted"}')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(InjectionFailHandler)
    assert res.returncode == 108, f"Expected exit 108, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_exit_code_0_success():
    """Prober returns exit code 0 when all 3 tiers pass."""
    class SuccessHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
                self.wfile.write(b'OK')
            elif self.path == "/version.json":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            if "DROP TABLE" in body:
                self.send_response(400); self.end_headers()
                self.wfile.write(b'{"detail": "BLOCKED"}')
            elif "000-12-3456" in body:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"response": "redacted [REDACTED_SSN] and [CONFIDENTIAL_COMMERCIAL_RATE]"}')
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"response": "healthy"}')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(SuccessHandler)
    assert res.returncode == 0, f"Expected exit 0, got {res.returncode}. Output:\n{res.stdout}\nError:\n{res.stderr}"


def test_prober_exit_code_104_json_array_payload():
    """Tier 2: /version.json returning JSON list [1, 2, 3] must trigger exit code 104 without crashing."""
    class JSONArrayHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'[1, 2, 3]')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(JSONArrayHandler)
    assert res.returncode == 104, f"Expected exit 104 for JSON array, got {res.returncode}. Output:\n{res.stdout}\nStderr:\n{res.stderr}"


def test_doc_snippet_tier2_json_array_payload():
    """Validates that the Tier 2 bash snippet in the markdown doc handles JSON arrays with exit code 104."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r"### Tier 2: Deployment identity and version consistency check.*?```bash\n(.*?)```", content, re.DOTALL)
    assert m is not None, "Tier 2 bash snippet missing from document"
    snippet = m.group(1)

    runner_script = f"""
export CLOUD_RUN_SERVICE_URLS="http://127.0.0.1:9"
curl() {{ echo "[1, 2, 3]"; }}
{snippet}
"""
    res = subprocess.run(["bash", "-c", runner_script], capture_output=True, text=True)
    assert res.returncode == 104, f"Doc snippet expected exit 104 for array, got {res.returncode}. Stderr: {res.stderr}"


def test_prober_exit_code_106_on_injection_server_error():
    """Tier 3: /query returning HTTP 500 on injection must trigger exit code 106 (query failure), not 108."""
    class Injection500Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            elif self.path == "/version.json":
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            if "DROP TABLE" in body:
                self.send_response(500); self.end_headers()
                self.wfile.write(b'Internal Server Error')
            elif "000-12-3456" in body:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"response": "redacted [REDACTED_SSN] and [CONFIDENTIAL_COMMERCIAL_RATE]"}')
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"response": "healthy"}')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(Injection500Handler)
    assert res.returncode == 106, f"Expected exit 106 on injection 500 error, got {res.returncode}. Output:\n{res.stdout}"


def test_prober_target_url_whitespace_and_commas():
    """Prober properly strips whitespace and takes the primary URL from comma-separated list."""
    class SuccessHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            elif self.path == "/version.json":
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            if "DROP TABLE" in body:
                self.send_response(400); self.end_headers()
            elif "000-12-3456" in body:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'redacted [REDACTED_SSN] [CONFIDENTIAL_COMMERCIAL_RATE]')
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'healthy')
        def log_message(self, *a): pass

    server = http.server.HTTPServer(("127.0.0.1", 0), SuccessHandler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        env = os.environ.copy()
        env["CLOUD_RUN_SERVICE_URLS"] = f"  http://127.0.0.1:{port}  ,  http://dummy-backup:8080 "
        res = subprocess.run([SCRIPT_PATH], capture_output=True, text=True, env=env)
        assert res.returncode == 0, f"Expected exit 0, got {res.returncode}. Output:\n{res.stdout}\nStderr:\n{res.stderr}"
    finally:
        server.shutdown()


def test_prober_exit_code_104_null_version_payload():
    """Tier 2: /version.json returning null version field must trigger exit code 104."""
    class NullVersionHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": null, "verification_marker": "v3.3.2-verified"}')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(NullVersionHandler)
    assert res.returncode == 104, f"Expected exit 104 for null version, got {res.returncode}. Output:\n{res.stdout}"


def test_doc_snippet_tier2_null_version_payload():
    """Validates that the Tier 2 bash snippet in the markdown doc handles null fields with exit code 104."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r"### Tier 2: Deployment identity and version consistency check.*?```bash\n(.*?)```", content, re.DOTALL)
    assert m is not None, "Tier 2 bash snippet missing from document"
    snippet = m.group(1)

    runner_script = f"""
export CLOUD_RUN_SERVICE_URLS="http://127.0.0.1:9"
curl() {{ echo '{{"version": null, "verification_marker": "v3.3.2-verified"}}'; }}
{snippet}
"""
    res = subprocess.run(["bash", "-c", runner_script], capture_output=True, text=True)
    assert res.returncode == 104, f"Doc snippet expected exit 104 for null field, got {res.returncode}. Stderr: {res.stderr}"


def test_prober_exit_code_108_on_injection_status_201():
    """Tier 3: /query returning HTTP 201 Created on injection must trigger exit code 108 (security gating failure)."""
    class Injection201Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            elif self.path == "/version.json":
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            if "DROP TABLE" in body:
                self.send_response(201); self.end_headers()
                self.wfile.write(b'{"status": "created"}')
            elif "000-12-3456" in body:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"response": "redacted [REDACTED_SSN] and [CONFIDENTIAL_COMMERCIAL_RATE]"}')
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"response": "healthy"}')
        def log_message(self, *a): pass

    res = _run_prober_with_handler(Injection201Handler)
    assert res.returncode == 108, f"Expected exit 108 on injection 201 response, got {res.returncode}. Output:\n{res.stdout}"


def test_doc_snippet_tier1_unbound_variable_safety():
    """Validates that the Tier 1 bash snippet in the markdown doc handles unset CLOUD_RUN_SERVICE_URLS without crashing."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r"### Tier 1: Service health readiness probe.*?```bash\n(.*?)```", content, re.DOTALL)
    assert m is not None, "Tier 1 bash snippet missing from document"
    snippet = m.group(1)

    # Run with CLOUD_RUN_SERVICE_URLS unset under set -u
    runner_script = f"""
unset CLOUD_RUN_SERVICE_URLS || true
curl() {{ echo "200"; }}
{snippet}
"""
    res = subprocess.run(["bash", "-c", runner_script], capture_output=True, text=True)
    assert res.returncode == 0, f"Doc snippet crashed on unset CLOUD_RUN_SERVICE_URLS: {res.stderr}"


def test_prober_target_url_whitespace_only_fallback():
    """Prober properly falls back to default URL when passed whitespace-only argument."""
    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200); self.end_headers()
            elif self.path == "/version.json":
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            if "DROP TABLE" in body:
                self.send_response(400); self.end_headers()
            elif "000-12-3456" in body:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'redacted [REDACTED_SSN] [CONFIDENTIAL_COMMERCIAL_RATE]')
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'healthy')
        def log_message(self, *a): pass

    server = http.server.HTTPServer(("127.0.0.1", 0), HealthHandler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        env = os.environ.copy()
        env["CLOUD_RUN_SERVICE_URLS"] = f"http://127.0.0.1:{port}"
        # Pass whitespace only as first argument
        res = subprocess.run([SCRIPT_PATH, "   "], capture_output=True, text=True, env=env)
        assert res.returncode == 0, f"Expected exit 0 for whitespace fallback, got {res.returncode}. Output:\n{res.stdout}\nStderr:\n{res.stderr}"
    finally:
        server.shutdown()


def test_skaffold_embedded_prober_matches_canonical_script():
    """Validates that the embedded base64 prober in skaffold-v3.yaml matches infra/cloudrun/verify_cloudrun_v3.sh byte-for-byte."""
    import base64
    skaffold_path = os.path.join(os.path.dirname(__file__), "..", "skaffold-v3.yaml")
    with open(skaffold_path, "r", encoding="utf-8") as f:
        sk_text = f.read()

    b64_lines = []
    capturing = False
    for line in sk_text.splitlines():
        if "PROBER_B64_EOF" in line:
            if capturing:
                break
            else:
                capturing = True
                continue
        if capturing:
            b64_lines.append(line.strip())
    b64_data = "".join(b64_lines)
    decoded = base64.b64decode(b64_data).decode("utf-8")

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        canonical = f.read()

    assert decoded == canonical, "Embedded base64 prober in skaffold-v3.yaml is out of sync with infra/cloudrun/verify_cloudrun_v3.sh"


def test_prober_authenticates_all_tiers_when_token_provided():
    """Verifies that when OIDC_TOKEN is provided, all 3 tiers (readiness, version, query) pass auth headers and succeed."""
    class PrivateServiceHandler(http.server.BaseHTTPRequestHandler):
        def check_auth(self):
            auth = self.headers.get("Authorization", "")
            return auth == "Bearer valid-test-token"

        def do_GET(self):
            if not self.check_auth():
                self.send_response(401); self.end_headers()
                self.wfile.write(b"Unauthorized")
                return
            if self.path in ("/healthz", "/health"):
                self.send_response(200); self.end_headers()
                self.wfile.write(b"OK")
            elif self.path == "/version.json":
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"version": "3.3.2", "verification_marker": "v3.3.2-verified"}')
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            if not self.check_auth():
                self.send_response(401); self.end_headers()
                return
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            if "DROP TABLE" in body:
                self.send_response(400); self.end_headers()
            elif "000-12-3456" in body:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'redacted [REDACTED_SSN] [CONFIDENTIAL_COMMERCIAL_RATE]')
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"response": "healthy"}')
        def log_message(self, *a): pass

    server = http.server.HTTPServer(("127.0.0.1", 0), PrivateServiceHandler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        env = os.environ.copy()
        env["OIDC_TOKEN"] = "valid-test-token"
        res = subprocess.run([SCRIPT_PATH, f"http://127.0.0.1:{port}"], capture_output=True, text=True, env=env)
        assert res.returncode == 0, f"Expected exit 0 with OIDC_TOKEN on private service, got {res.returncode}. Output:\n{res.stdout}"
    finally:
        server.shutdown()


def test_prober_exit_code_105_when_require_auth_and_no_token():
    """When REQUIRE_AUTH=true and neither OIDC_TOKEN nor gcloud token is available, prober must exit with code 105."""
    env = os.environ.copy()
    env["REQUIRE_AUTH"] = "true"
    env.pop("OIDC_TOKEN", None)
    # Point to nonexistent gcloud binary to guarantee token generation cannot succeed
    env["PATH"] = "/usr/bin:/bin"
    res = subprocess.run([SCRIPT_PATH, "http://127.0.0.1:9"], capture_output=True, text=True, env=env)
    assert res.returncode == 105, f"Expected exit 105 when REQUIRE_AUTH=true without token, got {res.returncode}. Output:\n{res.stdout}"


def test_cloud_run_v3_parameterized_template_structure_and_directives():
    """Asserts that infra/cloudrun/service-v3.yaml.template exists and defines all required # from-param directives."""
    tpl_path = os.path.join(os.path.dirname(__file__), "..", "infra", "cloudrun", "service-v3.yaml.template")
    assert os.path.exists(tpl_path), f"Parameterized template missing at {tpl_path}"

    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()

    docs = list(yaml.safe_load_all(content))
    assert len(docs) == 1, "service-v3.yaml.template must contain a single document"
    svc = docs[0]
    assert svc.get("apiVersion") == "serving.knative.dev/v1"
    assert svc.get("kind") == "Service"

    # Verify all 7 dynamic fields have post-render comment directives.
    # Note: labels.env must occur at least twice (metadata.labels.env and spec.template.metadata.labels.env).
    directives = [
        (r"#\s*from-param:\s*\$\{name\}", 1),
        (r"#\s*from-param:\s*\$\{labels\.env\}", 2),
        (r"#\s*from-param:\s*\$\{maxScale\}", 1),
        (r"#\s*from-param:\s*\$\{apphub-display-name\}", 1),
        (r"#\s*from-param:\s*\$\{apphub-description\}", 1),
        (r"#\s*from-param:\s*\$\{ENVIRONMENT\}", 1),
        (r"#\s*from-param:\s*\$\{AGENT_DISPLAY_NAME\}", 1),
    ]
    for d, min_count in directives:
        matches = re.findall(d, content)
        assert len(matches) >= min_count, (
            f"Directive '{d}' in service-v3.yaml.template found {len(matches)} times, expected >= {min_count}"
        )


def test_cloud_run_v3_deploy_parameters_and_private_worker_pool():
    """Asserts clouddeploy-v3.yaml declares delivery pipeline, canary strategy, target deployParameters, and routes through cloudbuild-workerpool."""
    cd_path = os.path.join(os.path.dirname(__file__), "..", "clouddeploy-v3.yaml")
    assert os.path.exists(cd_path)
    with open(cd_path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))

    # Pipeline validation
    pipeline = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
    assert pipeline is not None, "DeliveryPipeline kind not found in clouddeploy-v3.yaml"
    assert pipeline["metadata"]["name"] == "conductor-v3-pipeline"
    stages = [s["targetId"] for s in pipeline["serialPipeline"]["stages"]]
    assert stages == ["dev", "staging", "prod"]

    prod_stage = next(s for s in pipeline["serialPipeline"]["stages"] if s["targetId"] == "prod")
    assert prod_stage["strategy"]["canary"]["canaryDeployment"]["percentages"] == [25, 50]
    assert prod_stage["strategy"]["canary"]["canaryDeployment"]["verify"] is True

    targets = {d["metadata"]["name"]: d for d in docs if d.get("kind") == "Target"}
    assert {"dev", "staging", "prod"}.issubset(set(targets.keys()))

    expected_params = {
        "dev": {
            "name": "conductor-v3-dev",
            "labels.env": "dev",
            "maxScale": "5",
            "apphub-display-name": "The Conductor v3 - Development",
            "apphub-description": "Dev environment for Go serverless multi-agent platform",
            "ENVIRONMENT": "development",
            "AGENT_DISPLAY_NAME": "The Conductor v3 (Dev)",
        },
        "staging": {
            "name": "conductor-v3-staging",
            "labels.env": "staging",
            "maxScale": "10",
            "apphub-display-name": "The Conductor v3 - Staging",
            "apphub-description": "Staging pre-production environment for Go serverless multi-agent platform",
            "ENVIRONMENT": "staging",
            "AGENT_DISPLAY_NAME": "The Conductor v3 (Staging)",
        },
        "prod": {
            "name": "conductor-v3-prod",
            "labels.env": "prod",
            "maxScale": "20",
            "apphub-display-name": "The Conductor v3 - Production",
            "apphub-description": "Production environment for Go serverless multi-agent platform",
            "ENVIRONMENT": "production",
            "AGENT_DISPLAY_NAME": "The Conductor v3 (Production)",
        },
    }

    expected_pool = "projects/riccardo-blog-test-v1/locations/us-central1/workerPools/cloudbuild-workerpool"
    expected_sa = "105792947502-compute@developer.gserviceaccount.com"
    expected_storage = "gs://us-central1.deploy-artifacts.riccardo-blog-test-v1.appspot.com"

    for env_name, exp_p in expected_params.items():
        t = targets[env_name]
        assert "deployParameters" in t, f"Target {env_name} missing deployParameters"
        for k, v in exp_p.items():
            assert t["deployParameters"].get(k) == v, f"Target {env_name} deployParameters[{k}] mismatch"

        exec_configs = t.get("executionConfigs", [])
        assert len(exec_configs) > 0, f"Target {env_name} missing executionConfigs"
        cfg = exec_configs[0]
        assert cfg.get("workerPool") == expected_pool, f"Target {env_name} workerPool mismatch"
        assert cfg.get("serviceAccount") == expected_sa, f"Target {env_name} serviceAccount mismatch"
        assert cfg.get("artifactStorage") == expected_storage, f"Target {env_name} artifactStorage mismatch"
        assert cfg.get("executionTimeout") == "600s", f"Target {env_name} executionTimeout mismatch"
        usages = cfg.get("usages", [])
        assert {"RENDER", "DEPLOY", "VERIFY"}.issubset(set(usages))

    assert targets["prod"].get("requireApproval") is True, "Target 'prod' must have requireApproval: true"


def test_skaffold_v3_references_parameterized_template_cleanly():
    """Asserts that skaffold-v3.yaml references service-v3.yaml.template across all profiles."""
    sk_path = os.path.join(os.path.dirname(__file__), "..", "skaffold-v3.yaml")
    with open(sk_path, "r", encoding="utf-8") as f:
        sk = yaml.safe_load(f)

    assert "infra/cloudrun/service-v3.yaml.template" in sk.get("manifests", {}).get("rawYaml", [])
    for p in sk.get("profiles", []):
        if p.get("name") in ["dev", "staging", "prod"]:
            assert p.get("manifests", {}).get("rawYaml", []) == ["infra/cloudrun/service-v3.yaml.template"]


def test_cloud_run_v3_template_deploy_parameter_coverage():
    """Asserts that all template variables defined via # from-param: have an exact 1:1 match across all delivery targets."""
    tpl_path = os.path.join(os.path.dirname(__file__), "..", "infra", "cloudrun", "service-v3.yaml.template")
    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()

    template_vars = set(re.findall(r"#\s*from-param:\s*\$\{([^}]+)\}", content))
    assert len(template_vars) >= 7, f"Expected at least 7 from-param directives, found {len(template_vars)}"

    cd_path = os.path.join(os.path.dirname(__file__), "..", "clouddeploy-v3.yaml")
    with open(cd_path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))

    targets = {d["metadata"]["name"]: d for d in docs if d.get("kind") == "Target"}
    for env in ["dev", "staging", "prod"]:
        assert env in targets, f"Target '{env}' missing in clouddeploy-v3.yaml"
        dp = targets[env].get("deployParameters", {})
        # Bi-directional set parity
        assert set(dp.keys()) == template_vars, (
            f"Target '{env}' deployParameters mismatch with template. "
            f"Missing: {template_vars - set(dp.keys())}, Orphaned: {set(dp.keys()) - template_vars}"
        )
        for var in template_vars:
            assert str(dp[var]).strip() != "", f"Target '{env}' parameter '{var}' cannot be empty"





