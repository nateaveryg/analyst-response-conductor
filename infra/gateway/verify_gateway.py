#!/usr/bin/env python3
"""
Agent Platform Agent Gateway Verification & Governance Test Harness.

Executes comprehensive end-to-end verification of Milestone M3 requirements:
1. Declarative Manifest Schema Validation (gateway.yaml, authz_extension.yaml, authz_policy.yaml, route_rules.yaml).
2. Live Client-to-Agent Ingress Routing (/query, /streamQuery, /getAgentCard, /api/v1/*).
3. Inline Model Armor DLP Sanitization:
   - Secret partner discount (45%) & internal margins -> [CONFIDENTIAL_COMMERCIAL_RATE]
   - Social Security Numbers -> [REDACTED_SSN]
   - External emails -> [REDACTED_PII] (preserving @google.com)
   - Attack injection prevention (failOpen: false)
4. Agent Identity Attestation (X-Agent-Identity, X-Governed-By) & Cloud Trace correlation.
5. Zero-CORS preflight handling (OPTIONS -> HTTP 204 No Content with CORS headers).
6. Decoupled integration between simulated Frontend -> Gateway -> Backend Agent Engine.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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


class GatewayVerifier:
    def __init__(self):
        self.backend_port = find_free_port()
        self.gateway_port = find_free_port()
        self.backend_url = f"http://127.0.0.1:{self.backend_port}"
        self.gateway_url = f"http://127.0.0.1:{self.gateway_port}"
        self.backend_proc = None
        self.gateway_proc = None
        self.results = []

    def record(self, test_name: str, passed: bool, detail: str):
        icon = "  ✅ PASS" if passed else "  ❌ FAIL"
        print(f"{icon}: {test_name}")
        print(f"        Detail: {detail}")
        self.results.append({"name": test_name, "passed": passed, "detail": detail})

    def start_services(self):
        print("====================================================================")
        print("  🚀 Launching Go Backend & Agent Gateway for Multi-Tier Verification")
        print("====================================================================")

        # 1. Ensure Go binary is built
        if not os.path.exists(BINARY_PATH):
            print("Compiling Go backend...")
            cmd = ["go", "build", "-o", BINARY_PATH, "./cmd/server"]
            res = subprocess.run(cmd, cwd=BACKEND_DIR, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Go build failed: {res.stderr}")

        # 2. Launch Go backend
        env = os.environ.copy()
        env["PORT"] = str(self.backend_port)
        env["ENVIRONMENT"] = "test"
        env["VERTEX_AI_PROJECT"] = "riccardo-blog-test-v1"
        env["VERTEX_AI_LOCATION"] = "us-central1"
        env["VERTEX_AI_MODEL"] = "gemini-3.5-flash"
        env["SECURITY_SECRET_KEY"] = "conductor-v3-e2e-test-secret-key-32bytes!!"

        self.backend_proc = subprocess.Popen(
            [BINARY_PATH],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for backend health
        backend_ready = False
        for _ in range(30):
            try:
                r = requests.get(f"{self.backend_url}/health", timeout=1.0)
                if r.status_code == 200:
                    backend_ready = True
                    break
            except Exception:
                time.sleep(0.1)

        if not backend_ready:
            raise RuntimeError("Backend failed to start on /health within timeout")
        print(f"  Go Backend active on: {self.backend_url}")

        # 3. Launch Agent Gateway Service
        gw_cmd = [
            PYTHON_BIN,
            os.path.join(GATEWAY_DIR, "gateway_service.py"),
            "--port", str(self.gateway_port),
            "--backend-url", self.backend_url,
            "--project", "riccardo-blog-test-v1",
            "--location", "us-central1",
            "--gateway-id", "conductor-v3-ingress-gateway",
        ]
        self.gateway_proc = subprocess.Popen(
            gw_cmd,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for gateway health
        gateway_ready = False
        for _ in range(40):
            try:
                r = requests.get(f"{self.gateway_url}/health", timeout=1.0)
                if r.status_code == 200:
                    gateway_ready = True
                    break
            except Exception:
                time.sleep(0.1)

        if not gateway_ready:
            raise RuntimeError("Agent Gateway failed to start on /health within timeout")
        print(f"  Agent Gateway active on: {self.gateway_url}")
        print("====================================================================\n")

    def stop_services(self):
        print("\nShutting down test services...")
        if self.gateway_proc:
            self.gateway_proc.terminate()
            try:
                self.gateway_proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.gateway_proc.kill()
        if self.backend_proc:
            self.backend_proc.terminate()
            try:
                self.backend_proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.backend_proc.kill()

    def test_declarative_manifests(self):
        print("--- PHASE 1: Declarative Manifest Validation ---")
        deploy_script = os.path.join(GATEWAY_DIR, "deploy_gateway.py")
        res = subprocess.run(
            [PYTHON_BIN, deploy_script, "--validate-only", "--manifest-dir", GATEWAY_DIR],
            capture_output=True,
            text=True,
        )
        passed = res.returncode == 0
        self.record(
            "Declarative Manifests Syntax & Schema",
            passed,
            "gateway.yaml, authz_extension.yaml, authz_policy.yaml, route_rules.yaml validated" if passed else res.stderr,
        )

        # Verify deployed_gateway.json generated
        res_deploy = subprocess.run(
            [PYTHON_BIN, deploy_script, "--dry-run", "--manifest-dir", GATEWAY_DIR],
            capture_output=True,
            text=True,
        )
        passed_deploy = res_deploy.returncode == 0 and os.path.exists(os.path.join(GATEWAY_DIR, "deployed_gateway.json"))
        self.record(
            "Gateway Deployment Automation & Cloud Deploy Results",
            passed_deploy,
            "deployed_gateway.json & results.json generated successfully",
        )

    def test_cors_preflight(self):
        print("\n--- PHASE 2: Zero-CORS Preflight & Browser Ingress Verification ---")
        endpoints = ["/query", "/streamQuery", "/getAgentCard", "/api/v1/a2ui/chat"]
        for ep in endpoints:
            url = f"{self.gateway_url}{ep}"
            headers = {
                "Origin": "https://conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization, X-Cloud-Trace-Context",
            }
            r = requests.options(url, headers=headers, timeout=5.0)
            passed = (
                r.status_code == 204
                and r.headers.get("Access-Control-Allow-Origin") == "*"
                and "OPTIONS" in r.headers.get("Access-Control-Allow-Methods", "")
                and "Content-Type" in r.headers.get("Access-Control-Allow-Headers", "")
            )
            self.record(
                f"CORS Preflight OPTIONS {ep}",
                passed,
                f"Status: {r.status_code}, Allow-Origin: {r.headers.get('Access-Control-Allow-Origin')}",
            )

    def test_model_armor_dlp(self):
        print("\n--- PHASE 3: Inline Model Armor DLP Policy Enforcement ---")

        # 1. Partner discount 45% masking
        prompt1 = "Please review our terms: the secret partner discount is 45% on enterprise licenses."
        r1 = requests.post(f"{self.gateway_url}/query", json={"prompt": prompt1}, timeout=5.0)
        passed1 = (
            r1.status_code == 200
            and "45%" not in r1.text
            and "[CONFIDENTIAL_COMMERCIAL_RATE]" in r1.text
        )
        self.record(
            "DLP Masking: Secret Partner Discount 45%",
            passed1,
            f"Response sanitized secret partner discount 45% -> [CONFIDENTIAL_COMMERCIAL_RATE]",
        )

        # 2. Internal margin masking
        prompt2 = "Quote summary: internal margin is 72% for this transaction."
        r2 = requests.post(f"{self.gateway_url}/query", json={"prompt": prompt2}, timeout=5.0)
        passed2 = (
            r2.status_code == 200
            and "72%" not in r2.text
            and "[CONFIDENTIAL_COMMERCIAL_RATE]" in r2.text
        )
        self.record(
            "DLP Masking: Internal Commercial Margin (72%)",
            passed2,
            f"Response sanitized internal margin -> [CONFIDENTIAL_COMMERCIAL_RATE]",
        )

        # 3. Social Security Number masking
        prompt3 = "Lead contact information: SSN is 000-12-3456."
        r3 = requests.post(f"{self.gateway_url}/query", json={"prompt": prompt3}, timeout=5.0)
        passed3 = (
            r3.status_code == 200
            and "000-12-3456" not in r3.text
            and "[REDACTED_SSN]" in r3.text
        )
        self.record(
            "DLP Masking: Social Security Number (SSN)",
            passed3,
            f"Response sanitized SSN 000-12-3456 -> [REDACTED_SSN]",
        )

        # 4. External Email PII redaction vs @google.com preservation
        prompt4 = "Contact analyst analyst@google.com or external auditor auditor@competitor.com"
        r4 = requests.post(f"{self.gateway_url}/query", json={"prompt": prompt4}, timeout=5.0)
        passed4 = (
            r4.status_code == 200
            and "analyst@google.com" in r4.text
            and "auditor@competitor.com" not in r4.text
            and "[REDACTED_PII]" in r4.text
        )
        self.record(
            "DLP Masking: External Email PII Redaction",
            passed4,
            "Preserved @google.com email, redacted external address to [REDACTED_PII]",
        )

        # 5. Malicious SQLi injection blocked (failOpen: false)
        prompt5 = "Query: DROP TABLE users; --"
        r5 = requests.post(f"{self.gateway_url}/query", json={"prompt": prompt5}, timeout=5.0)
        passed5 = r5.status_code == 400 and "BLOCKED_BY_MODEL_ARMOR" in r5.text
        self.record(
            "DLP Attack Prevention: SQL Injection Blocked",
            passed5,
            f"Blocked malicious SQL injection payload with HTTP {r5.status_code}",
        )

    def test_streaming_query_dlp(self):
        print("\n--- PHASE 4: SSE Streaming Query & Chunk-Level DLP Inspection ---")
        prompt = "Stream analyst response with confidential partner discount is 45% and SSN 123-45-6789"
        r = requests.post(
            f"{self.gateway_url}/streamQuery",
            json={"prompt": prompt},
            stream=True,
            timeout=10.0,
        )
        chunks = []
        for line in r.iter_lines(decode_unicode=True):
            if line:
                chunks.append(line)

        full_stream_text = "\n".join(chunks)
        passed = (
            r.status_code == 200
            and "text/event-stream" in r.headers.get("content-type", "")
            and len(chunks) > 0
            and "45%" not in full_stream_text
            and "123-45-6789" not in full_stream_text
            and "[CONFIDENTIAL_COMMERCIAL_RATE]" in full_stream_text
            and "[REDACTED_SSN]" in full_stream_text
        )
        self.record(
            "SSE Stream Query & Chunk-Level Model Armor DLP",
            passed,
            f"Streamed {len(chunks)} chunks with real-time DLP redaction",
        )

    def test_attestation_and_telemetry(self):
        print("\n--- PHASE 5: Agent Attestation & Distributed Tracing ---")
        test_trace = "4bf92f3577b34da6a3ce929d0e0e4736/0000000000000001;o=1"
        headers = {
            "X-Cloud-Trace-Context": test_trace,
            "Content-Type": "application/json",
        }
        r = requests.get(f"{self.gateway_url}/getAgentCard", headers=headers, timeout=5.0)

        passed = (
            r.status_code == 200
            and r.headers.get("X-Agent-Identity") == "conductor-v3-ara@riccardo-blog-test-v1.iam.gserviceaccount.com"
            and "conductor-v3-ingress-gateway" in r.headers.get("X-Governed-By", "")
            and "4bf92f3577b34da6a3ce929d0e0e4736" in r.headers.get("X-Cloud-Trace-Context", "")
        )
        self.record(
            "Agent Identity Attestation & Trace Propagation",
            passed,
            f"X-Agent-Identity: {r.headers.get('X-Agent-Identity')}, Trace propagated: {r.headers.get('X-Cloud-Trace-Context')}",
        )

    def test_ingress_route_mapping(self):
        print("\n--- PHASE 6: Ingress Route Mapping & API Reverse Proxy ---")

        # 1. /getAgentCard
        r1 = requests.get(f"{self.gateway_url}/getAgentCard", timeout=5.0)
        data1 = r1.json() if r1.status_code == 200 else {}
        passed1 = r1.status_code == 200 and "Analyst Response Agent" in data1.get("name", "")
        self.record("Route Mapping: /getAgentCard", passed1, f"Agent name: {data1.get('name')}")

        # 2. /query flat payload
        r2 = requests.post(f"{self.gateway_url}/query", json={"prompt": "Explain Google Cloud Run security"}, timeout=5.0)
        passed2 = r2.status_code == 200 and "response" in r2.json()
        self.record("Route Mapping: /query (Flat Payload)", passed2, f"Status: {r2.status_code}")

        # 3. /query nested input envelope
        r3 = requests.post(f"{self.gateway_url}/query", json={"input": {"prompt": "Analyze RFI requirements"}}, timeout=5.0)
        passed3 = r3.status_code == 200 and "response" in r3.json()
        self.record("Route Mapping: /query (Nested Envelope)", passed3, f"Status: {r3.status_code}")

        # 4. /api/v1/workspaces/
        r4 = requests.get(f"{self.gateway_url}/api/v1/workspaces/", timeout=5.0)
        passed4 = r4.status_code == 200 and isinstance(r4.json(), list)
        self.record("Route Mapping: /api/v1/workspaces/", passed4, f"Retrieved {len(r4.json())} workspaces")

        # 5. /health
        r5 = requests.get(f"{self.gateway_url}/health", timeout=5.0)
        passed5 = r5.status_code == 200 and r5.json().get("status") == "healthy"
        self.record("Route Mapping: /health (Operational Probe)", passed5, f"Gateway health: {r5.json().get('status')}")

    def test_decoupled_frontend_integration(self):
        print("\n--- PHASE 7: Decoupled Frontend-to-Gateway-to-Backend Integration ---")
        # Simulates Nginx frontend proxying to Agent Gateway
        frontend_headers = {
            "Host": "conductor-v3-frontend-prod-4izasuhqpq-uc.a.run.app",
            "X-Forwarded-For": "203.0.113.195",
            "X-Forwarded-Proto": "https",
            "X-User-Email": "analyst@google.com",
            "Content-Type": "application/json",
        }
        chat_payload = {
            "message": "Initiate automated questionnaire analysis for enterprise cloud migration",
            "action_id": "open_intake",
        }
        r = requests.post(
            f"{self.gateway_url}/api/v1/a2ui/chat",
            json=chat_payload,
            headers=frontend_headers,
            timeout=10.0,
        )
        passed = (
            r.status_code == 200
            and "action_id" in r.text
            and r.headers.get("Access-Control-Allow-Origin") == "*"
            and r.headers.get("X-Agent-Identity") is not None
        )
        self.record(
            "Decoupled Integration: Frontend -> Gateway -> Agent Engine",
            passed,
            f"End-to-end traversal succeeded with HTTP {r.status_code} and governance attestation",
        )

    def run_all(self) -> bool:
        try:
            self.start_services()
            self.test_declarative_manifests()
            self.test_cors_preflight()
            self.test_model_armor_dlp()
            self.test_streaming_query_dlp()
            self.test_attestation_and_telemetry()
            self.test_ingress_route_mapping()
            self.test_decoupled_frontend_integration()
        finally:
            self.stop_services()

        print("\n" + "=" * 80)
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        print(f"📊 SUMMARY: {passed}/{total} Verification Checks Passed ({(passed/total)*100:.1f}%)")
        print("=" * 80)
        return passed == total


def main():
    verifier = GatewayVerifier()
    success = verifier.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
