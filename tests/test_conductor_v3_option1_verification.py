"""
Conductor v3 (Option 1) Automated Verification Suite.
Verifies:
1. Go Backend Agent Engine client, gRPC/REST endpoints, Model Armor, and governance.
2. Unified Flutter client architecture, models, WebAssembly configuration, and PlutoGrid components.
3. Secure Enterprise Networking (BeyondCorp / IAP / Cloud Armor) Terraform infrastructure.
"""
import hashlib
import json
import os
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")
NETWORKING_DIR = os.path.join(REPO_ROOT, "infra", "terraform", "networking")


class TestConductorV3BackendVerification(unittest.TestCase):
    """Verifies Go backend microservice and Vertex AI Agent Engine integration."""

    def test_go_backend_unit_tests_pass(self):
        """Runs `go test ./...` in the backend directory and confirms 100% pass rate."""
        cmd = ["go", "test", "./..."]
        res = subprocess.run(cmd, cwd=BACKEND_DIR, capture_output=True, text=True)
        self.assertEqual(
            res.returncode,
            0,
            f"Go backend tests failed with output:\n{res.stdout}\n{res.stderr}"
        )
        self.assertIn("github.com/google/rficonductorv2/backend/internal/agentengine", res.stdout)
        self.assertIn("github.com/google/rficonductorv2/backend/internal/api", res.stdout)
        self.assertIn("github.com/google/rficonductorv2/backend/internal/governance", res.stdout)
        self.assertIn("github.com/google/rficonductorv2/backend/internal/rag", res.stdout)

    def test_agent_engine_package_structure(self):
        """Verifies files in backend/internal/agentengine."""
        client_file = os.path.join(BACKEND_DIR, "internal", "agentengine", "client.go")
        types_file = os.path.join(BACKEND_DIR, "internal", "agentengine", "types.go")
        test_file = os.path.join(BACKEND_DIR, "internal", "agentengine", "client_test.go")

        self.assertTrue(os.path.exists(client_file), "client.go must exist")
        self.assertTrue(os.path.exists(types_file), "types.go must exist")
        self.assertTrue(os.path.exists(test_file), "client_test.go must exist")


class TestConductorV3FlutterClientVerification(unittest.TestCase):
    """Verifies Flutter 3.x multi-platform WebAssembly client structure and models."""

    def test_frontend_project_structure(self):
        """Verifies essential Flutter client files and widgets."""
        pubspec = os.path.join(FRONTEND_DIR, "pubspec.yaml")
        main_dart = os.path.join(FRONTEND_DIR, "lib", "main.dart")
        web_index = os.path.join(FRONTEND_DIR, "web", "index.html")

        self.assertTrue(os.path.exists(pubspec), "pubspec.yaml must exist")
        self.assertTrue(os.path.exists(main_dart), "main.dart must exist")
        self.assertTrue(os.path.exists(web_index), "web/index.html must exist")

        with open(pubspec, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("pluto_grid", content)
            self.assertIn("flutter_riverpod", content)
            self.assertIn("flutter_markdown", content)
            self.assertIn("3.3.1", content)

        version_json_path = os.path.join(FRONTEND_DIR, "build", "web", "version.json")
        self.assertTrue(os.path.exists(version_json_path), "version.json must exist")
        with open(version_json_path, "r", encoding="utf-8") as f:
            v_data = json.load(f)
            self.assertEqual(v_data.get("version"), "3.3.1")
            self.assertEqual(v_data.get("build_number"), "2")
            self.assertEqual(v_data.get("verification_marker"), "v3.3.1-verified")

        with open(version_json_path, "rb") as f:
            v_hash = hashlib.md5(f.read()).hexdigest()
        self.assertEqual(v_hash, "ee8df6dc67db7d69e3e8243b3f47388b")

        service_worker_path = os.path.join(FRONTEND_DIR, "build", "web", "flutter_service_worker.js")
        self.assertTrue(os.path.exists(service_worker_path), "flutter_service_worker.js must exist")
        with open(service_worker_path, "r", encoding="utf-8") as f:
            sw_content = f.read()
            self.assertIn(f'"version.json": "{v_hash}"', sw_content)

    def test_flutter_widgets_and_models_exist(self):
        """Verifies custom A2UI, Governance, PlutoGrid, and Workspace widgets."""
        widgets = [
            "journey_stepper.dart",
            "workspace_header.dart",
            "a2ui_card_renderer.dart",
            "pluto_spreadsheet_view.dart",
            "governance_radar_modal.dart",
        ]
        for w in widgets:
            path = os.path.join(FRONTEND_DIR, "lib", "widgets", w)
            self.assertTrue(os.path.exists(path), f"Widget {w} must exist at {path}")

        models = [
            "workspace.dart",
            "a2ui_surface.dart",
            "governance.dart",
            "rfi_questionnaire.dart",
        ]
        for m in models:
            path = os.path.join(FRONTEND_DIR, "lib", "models", m)
            self.assertTrue(os.path.exists(path), f"Model {m} must exist at {path}")


class TestConductorV3SecureNetworkingVerification(unittest.TestCase):
    """Verifies Terraform networking module for BeyondCorp / IAP and Cloud Armor."""

    def test_networking_terraform_files_exist(self):
        """Verifies main.tf, variables.tf, outputs.tf, and deployment script."""
        main_tf = os.path.join(NETWORKING_DIR, "main.tf")
        vars_tf = os.path.join(NETWORKING_DIR, "variables.tf")
        outs_tf = os.path.join(NETWORKING_DIR, "outputs.tf")
        deploy_sh = os.path.join(NETWORKING_DIR, "deploy_secure_networking.sh")

        self.assertTrue(os.path.exists(main_tf), "main.tf must exist")
        self.assertTrue(os.path.exists(vars_tf), "variables.tf must exist")
        self.assertTrue(os.path.exists(outs_tf), "outputs.tf must exist")
        self.assertTrue(os.path.exists(deploy_sh), "deploy_secure_networking.sh must exist")

    def test_networking_resource_declarations(self):
        """Inspects HCL resource declarations for Cloud Armor, IAP, and Serverless NEG."""
        with open(os.path.join(NETWORKING_DIR, "main.tf"), "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("google_compute_security_policy", content)
            self.assertIn("google_compute_region_network_endpoint_group", content)
            self.assertIn("google_compute_backend_service", content)
            self.assertIn("iap {", content)
            self.assertIn("google_iap_web_backend_service_iam_binding", content)
            self.assertIn("roles/iap.httpsResourceAccessor", content)


if __name__ == "__main__":
    unittest.main()
