"""
Conductor v3 End-to-End Integration Verification Suite.

Validates:
1. Go backend microservice initialization and health lifecycle.
2. Full 7-Phase Analyst Response Agent (ARA) journey executed via A2UI protocol.
3. Flutter WebAssembly client contract parity (Workspaces, A2UI Cards, Governance Radar, RFI Questionnaires).
4. Dual-custody Deficit Attestation Waiver lifecycle and Cryptographic Provenance HMAC verification.
5. Model Armor real-time DLP inspection, PII redaction, and attack blocking.
6. Vertex AI Agent Engine client integration, query synthesis, and automated evaluation scorecards.
7. Multi-format export services (Markdown, CSV, JSON bundles).
"""
import json
import os
import re
import socket
import subprocess
import time
import sys
import unittest
import urllib.request
import urllib.error

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
import infra.frontend.verify_frontend as vf
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
BINARY_PATH = os.path.join(BACKEND_DIR, "conductor-server")


def find_free_port():
    """Finds an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestConductorV3EndToEndIntegration(unittest.TestCase):
    """E2E integration test suite for Conductor v3 Go Backend & Flutter Client contracts."""

    server_process = None
    port = None
    base_url = None

    @classmethod
    def setUpClass(cls):
        """Builds and launches the Go backend server in background."""
        # 1. Compile the binary if needed
        build_cmd = ["go", "build", "-o", BINARY_PATH, "./cmd/server"]
        build_res = subprocess.run(build_cmd, cwd=BACKEND_DIR, capture_output=True, text=True)
        if build_res.returncode != 0:
            raise RuntimeError(f"Failed to build Go backend: {build_res.stderr}")

        cls.port = find_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        # 2. Launch Go server
        env = os.environ.copy()
        env["PORT"] = str(cls.port)
        env["ENVIRONMENT"] = "test"
        env["VERTEX_AI_PROJECT"] = "riccardo-blog-test-v1"
        env["VERTEX_AI_LOCATION"] = "us-central1"
        env["VERTEX_AI_MODEL"] = "gemini-3.5-flash"
        env["SECURITY_SECRET_KEY"] = "conductor-v3-e2e-test-secret-key-32bytes!!"

        cls.server_process = subprocess.Popen(
            [BINARY_PATH],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 3. Wait for /health
        ready = False
        health_url = f"{cls.base_url}/health"
        for _ in range(30):
            try:
                with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.1)

        if not ready:
            cls.tearDownClass()
            raise RuntimeError("Go backend failed to respond on /health within timeout")

    @classmethod
    def tearDownClass(cls):
        """Terminates the Go backend server."""
        if cls.server_process:
            cls.server_process.terminate()
            try:
                cls.server_process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                cls.server_process.kill()

    def _http_get(self, path, headers=None):
        """Helper for HTTP GET."""
        req_headers = {"Accept": "*/*"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(f"{self.base_url}{path}", headers=req_headers, method="GET")
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            ct = resp.headers.get("Content-Type", "")
            if "application/json" in ct:
                return resp.status, json.loads(data) if data else {}
            return resp.status, data

    def _http_post(self, path, payload, headers=None):
        """Helper for HTTP POST."""
        req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if headers:
            req_headers.update(headers)
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}{path}", data=body, headers=req_headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data) if data else {}

    def _http_head(self, path, headers=None):
        """Helper for HTTP HEAD."""
        req_headers = {"Accept": "*/*"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(f"{self.base_url}{path}", headers=req_headers, method="HEAD")
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers

    def _parse_a2ui(self, text):
        """Extracts and parses <a2ui-json> block from agent response text."""
        match = re.search(r"<a2ui-json>([\s\S]*?)</a2ui-json>", text)
        self.assertIsNotNone(match, f"Expected <a2ui-json> block in response:\n{text}")
        return json.loads(match.group(1).strip())

    # --- Test Cases ---

    def test_01_health_and_agent_card(self):
        """Tests health diagnostics, healthz, version.json, and Agent Card protocol metadata (GET & HEAD)."""
        # 1. GET /health
        status, data = self._http_get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "Analyst Response Agent (ARA)")
        self.assertEqual(data.get("version"), "3.3.2")
        self.assertEqual(data.get("verification_marker"), "v3.3.2-verified")

        # 2. GET /healthz
        status, data_z = self._http_get("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(data_z.get("status"), "healthy")
        self.assertEqual(data_z.get("version"), "3.3.2")
        self.assertEqual(data_z.get("verification_marker"), "v3.3.2-verified")

        # 3. GET /version.json
        status, v_data = self._http_get("/version.json")
        self.assertEqual(status, 200)
        self.assertEqual(v_data.get("version"), "3.3.2")
        self.assertEqual(v_data.get("verification_marker"), "v3.3.2-verified")
        self.assertEqual(v_data.get("build_number"), "2")

        # 4. GET /api/v1/agent-card
        status, card = self._http_get("/api/v1/agent-card")
        self.assertEqual(status, 200)
        self.assertEqual(card.get("version"), "3.3.2")
        self.assertEqual(card.get("verification_marker"), "v3.3.2-verified")
        self.assertIn("A2UI", card.get("supportedProtocols", []))
        self.assertIn("VERTEX_REASONING_ENGINE", card.get("supportedProtocols", []))
        self.assertIn("cloud-run", card.get("runtime", ""))

        # 5. GET /.well-known/agent.json
        status, wellknown = self._http_get("/.well-known/agent.json")
        self.assertEqual(status, 200)
        self.assertEqual(wellknown.get("version"), "3.3.2")
        self.assertEqual(wellknown.get("verification_marker"), "v3.3.2-verified")

        # 6. HEAD requests on all metadata & probe endpoints
        for endpoint in [
            "/",
            "/health",
            "/healthz",
            "/ready",
            "/version.json",
            "/api/v1/agent-card",
            "/.well-known/agent.json",
            "/getAgentCard",
            "/api/v1/agent-engine/card",
            "/api/v1/agent-engine/getAgentCard",
            "/api/v1/workspaces",
            "/api/v1/artifacts",
            "/api/v1/governance/scorecard",
            "/api/v1/export/deep-dive-report",
            "/api/v1/stream/telemetry",
            "/main.dart.wasm",
            "/main.dart.js",
        ]:
            h_status, h_headers = self._http_head(endpoint)
            self.assertEqual(h_status, 200, f"Expected HTTP 200 on HEAD {endpoint}")
            self.assertIsNotNone(h_headers.get("Content-Type"), f"Missing Content-Type on HEAD {endpoint}")

    def test_02_workspaces_crud_and_tenancy(self):
        """Tests multi-user workspace isolation and group tenancy contracts."""
        status, workspaces = self._http_get("/api/v1/workspaces")
        self.assertEqual(status, 200)
        self.assertIsInstance(workspaces, list)
        self.assertGreaterEqual(len(workspaces), 1)

        default_ws = workspaces[0]
        self.assertIn("id", default_ws)
        self.assertIn("name", default_ws)
        self.assertIn("current_phase", default_ws)

        # Create new workspace
        new_ws_payload = {
            "name": "Forrester Wave Q3 2026 - Public Cloud Platforms",
            "report_type": "Public Cloud Platforms",
            "description": "E2E automated analyst evaluation",
        }
        status, created_ws = self._http_post(
            "/api/v1/workspaces",
            new_ws_payload,
            headers={"X-Goog-Authenticated-User-Email": "averyn@google.com"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created_ws["name"], new_ws_payload["name"])
        self.assertEqual(created_ws["owner_email"], "averyn@google.com")

    def test_03_a2ui_welcome_briefing_and_phase_progression(self):
        """Tests A2UI Chat welcoming briefing and Phase 1-7 state transitions."""
        # 1. Welcome briefing
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {"message": "Hello", "action_id": "welcome_briefing"},
        )
        self.assertEqual(status, 200)
        surface = self._parse_a2ui(res["response"])
        self.assertEqual(surface["phase"], 1)
        self.assertIn("Document Intake", surface["title"])

        # 2. Phase 1 Intake
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {
                "message": "Start intake",
                "action_id": "submit_criteria_analysis",
                "context_data": {"report_name": "Cloud-Native Application Protection Platform (CNAP)"},
            },
        )
        self.assertEqual(status, 200)
        surface = self._parse_a2ui(res["response"])
        self.assertEqual(surface["phase"], 1)
        self.assertIn("card-evaluation-matrix", surface["card_id"])

        # 3. Phase 3 Kickoff & Workback schedule
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {
                "message": "Generate timeline",
                "action_id": "generate_timeline",
                "context_data": {"submission_deadline": "2026-10-15"},
            },
        )
        self.assertEqual(status, 200)
        surface = self._parse_a2ui(res["response"])
        self.assertEqual(surface["phase"], 3)
        self.assertIn("Workback Schedule", surface["title"])

    def test_04_rfi_spreadsheet_ingestion_and_provenance(self):
        """Tests Phase 4 RFI questionnaire ingestion and hybrid RAG grounding."""
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {
                "message": "Process RFI questionnaire",
                "action_id": "ingest_rfi_spreadsheet",
                "context_data": {"spreadsheet_url": "https://docs.google.com/spreadsheets/d/1rM5FlzejyVY_xWCJxdxnzusNxtpH07w7"},
            },
        )
        self.assertEqual(status, 200)
        surface = self._parse_a2ui(res["response"])
        self.assertEqual(surface["phase"], 4)
        self.assertIn("RAG Ingestion", surface["title"])

        # Validate RFI Markdown & CSV Export
        status, md_data = self._http_get("/api/v1/export/rfi-responses?format=md")
        self.assertEqual(status, 200)
        md_text = md_data.get("markdown", "") if isinstance(md_data, dict) else str(md_data)
        self.assertIn("RFI Technical Responses", md_text)

        status, csv_data = self._http_get("/api/v1/export/rfi-responses?format=csv")
        self.assertEqual(status, 200)
        csv_text = csv_data.get("csv", "") if isinstance(csv_data, dict) else str(csv_data)
        self.assertIn("Worksheet Tab Domain", csv_text)
        self.assertIn("Section Coordinate", csv_text)

    def test_05_demo_script_architect_and_executive_governance(self):
        """Tests Phase 5 AI Demo Script Architect and Phase 6 Executive Review Agent."""
        # 1. Demo Script Architect
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {"message": "Synthesize demo script", "action_id": "invoke_demo_architect"},
        )
        self.assertEqual(status, 200)
        surface = self._parse_a2ui(res["response"])
        self.assertEqual(surface["phase"], 5)
        self.assertIn("Demo Environments", surface["title"])

        # 2. Executive Governance & Deficit Waiver
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {"message": "Run executive governance audit", "action_id": "invoke_executive_governance"},
        )
        self.assertEqual(status, 200)
        surface = self._parse_a2ui(res["response"])
        self.assertEqual(surface["phase"], 6)
        self.assertIn("Executive Review", surface["title"])

    def test_06_governance_radar_and_dual_custody_waiver_signing(self):
        """Tests Governance Radar Scorecard and Dual-Custody signing lifecycle."""
        # 1. Fetch scorecard
        status, radar = self._http_get("/api/v1/governance/scorecard")
        self.assertEqual(status, 200)
        self.assertIn("overall_compliance_score", radar)
        self.assertIn("rag_grounding_fidelity", radar)
        self.assertIn("waivers", radar)
        self.assertGreaterEqual(len(radar["waivers"]), 1)

        waiver_id = radar["waivers"][0]["waiver_id"]

        # 2. Sign as Product GM
        status, signed_gm = self._http_post(
            f"/api/v1/governance/waivers/{waiver_id}/sign",
            {"approver_email": "product-gm@google.com", "role": "PRODUCT_GM"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(signed_gm["product_gm_approver"], "product-gm@google.com")

        # 3. Sign as Legal Counsel -> triggers is_approved = true
        status, signed_legal = self._http_post(
            f"/api/v1/governance/waivers/{waiver_id}/sign",
            {"approver_email": "legal-counsel@google.com", "role": "LEGAL_COUNSEL"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(signed_legal["is_approved"])
        self.assertIsNotNone(signed_legal["manifest_sha256"])

        # 4. Verify Cryptographic Provenance Token
        status, prov = self._http_get(f"/api/v1/governance/provenance/{waiver_id}")
        self.assertEqual(status, 200)
        self.assertTrue(prov["signature_valid"])
        self.assertEqual(prov["audit_compliance"], "VERIFIED_CRYPTO_TOKEN")

    def test_07_model_armor_dlp_and_security_filters(self):
        """Tests Model Armor DLP real-time PII redaction and injection blocking."""
        # 1. External PII Redaction
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {"message": "Please contact external customer john.doe@acme-corp.com regarding evaluation."},
        )
        self.assertEqual(status, 200)
        self.assertNotIn("john.doe@acme-corp.com", res["response"])
        self.assertIn("[REDACTED_PII]", res["response"])

        # 2. Confidential Margin Redaction
        status, res = self._http_post(
            "/api/v1/a2ui/chat",
            {"message": "Google Cloud unreleased internal discount is 42% on compute margin."},
        )
        self.assertEqual(status, 200)
        self.assertNotIn("42%", res["response"])
        self.assertIn("[CONFIDENTIAL_COMMERCIAL_RATE]", res["response"])

        # 3. Malicious SQL Injection Block (interception with 400 Bad Request)
        try:
            status, res = self._http_post(
                "/api/v1/a2ui/chat",
                {"message": "Run query: SELECT * FROM users; DROP TABLE workspaces; --"},
            )
            self.fail("Expected HTTPError 400 Bad Request from Model Armor prompt gating")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            err_data = json.loads(e.read().decode("utf-8"))
            self.assertIn("BLOCKED", err_data.get("detail", ""))

    def test_08_vertex_agent_engine_integration(self):
        """Tests Vertex AI Agent Engine reasoning query and scorecard evaluation."""
        # 1. Agent Engine Query
        status, res = self._http_post(
            "/api/v1/agent-engine/query",
            {
                "prompt": "Evaluate Google Cloud Serverless Cloud Run concurrency architecture",
                "evaluation_type": "FORRESTER_WAVE",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("response", res)
        self.assertEqual(res.get("status"), "success")
        self.assertGreaterEqual(res.get("confidence_score", 0), 0.80)

        # 2. Agent Engine Evaluation
        status, eval_res = self._http_post(
            "/api/v1/agent-engine/evaluate",
            {
                "question": "Does Google Cloud offer sovereign cloud data residency?",
                "generated_answer": "Google Cloud provides Assured Workloads and Sovereign Controls in europe-west3 with EKM/CMEK.",
            },
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(eval_res["overall_quality_score"], 0.85)
        self.assertTrue(eval_res["passed_evaluation"])

    def test_09_version_environment_overrides(self):
        """Attacks container boot: verifies SERVICE_VERSION and VERIFICATION_MARKER override defaults on live server."""
        override_port = find_free_port()
        override_base = f"http://127.0.0.1:{override_port}"

        env = os.environ.copy()
        env["PORT"] = str(override_port)
        env["ENVIRONMENT"] = "test-override"
        env["SERVICE_VERSION"] = "3.3.1-override-custom"
        env["VERIFICATION_MARKER"] = "custom-marker-live-verified"
        env["SECURITY_SECRET_KEY"] = "conductor-v3-e2e-override-key-32b!!"

        proc = subprocess.Popen(
            [BINARY_PATH],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Poll until healthy
            ready = False
            for _ in range(30):
                try:
                    with urllib.request.urlopen(f"{override_base}/health", timeout=1.0) as resp:
                        if resp.status == 200:
                            ready = True
                            break
                except Exception:
                    time.sleep(0.1)

            self.assertTrue(ready, "Live Go backend with overridden environment failed to start")

            # Check /health
            with urllib.request.urlopen(f"{override_base}/health") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data.get("version"), "3.3.1-override-custom")
                self.assertEqual(data.get("verification_marker"), "custom-marker-live-verified")
                self.assertEqual(data.get("environment"), "test-override")

            # Check /healthz
            with urllib.request.urlopen(f"{override_base}/healthz") as resp:
                self.assertEqual(resp.status, 200)
                data_z = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data_z.get("version"), "3.3.1-override-custom")
                self.assertEqual(data_z.get("verification_marker"), "custom-marker-live-verified")

            # Check /version.json
            with urllib.request.urlopen(f"{override_base}/version.json") as resp:
                self.assertEqual(resp.status, 200)
                data_v = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data_v.get("version"), "3.3.1-override-custom")
                self.assertEqual(data_v.get("verification_marker"), "custom-marker-live-verified")

            # Check /api/v1/agent-card
            with urllib.request.urlopen(f"{override_base}/api/v1/agent-card") as resp:
                self.assertEqual(resp.status, 200)
                card = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(card.get("version"), "3.3.1-override-custom")
                self.assertEqual(card.get("verification_marker"), "custom-marker-live-verified")

            # Check /.well-known/agent.json
            with urllib.request.urlopen(f"{override_base}/.well-known/agent.json") as resp:
                self.assertEqual(resp.status, 200)
                wellknown = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(wellknown.get("version"), "3.3.1-override-custom")
                self.assertEqual(wellknown.get("verification_marker"), "custom-marker-live-verified")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_10_post_deployment_frontend_verification_prober(self):
        """Executes the full 6-point Cloud Deploy verify_frontend.py prober against the live Go server."""
        success = vf.run_verification(
            env_tier="dev",
            phase="stable",
            base_url=self.base_url,
            timeout=10,
        )
        self.assertTrue(success, "Post-deployment verify_frontend prober failed against live Go server")


if __name__ == "__main__":
    unittest.main()
