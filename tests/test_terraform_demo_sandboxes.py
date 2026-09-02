import subprocess
from pathlib import Path
import pytest


@pytest.fixture
def terraform_dir() -> Path:
    return Path(__file__).parent.parent / "infra" / "terraform" / "demo_sandboxes"


def test_terraform_files_exist_and_readable(terraform_dir: Path) -> None:
    expected_files = [
        "main.tf",
        "variables.tf",
        "outputs.tf",
        "terraform.tfvars.example",
        "test_and_deploy_sandboxes.sh",
    ]
    for filename in expected_files:
        filepath = terraform_dir / filename
        assert filepath.exists(), f"Expected Terraform file [{filename}] missing in {terraform_dir}"
        assert filepath.stat().st_size > 0, f"File [{filename}] should not be empty"


def test_terraform_resource_declarations(terraform_dir: Path) -> None:
    main_tf = (terraform_dir / "main.tf").read_text(encoding="utf-8")
    
    # 1. Verify Core API enablement
    assert "resource \"google_project_service\" \"enabled_apis\"" in main_tf
    for api in ["run.googleapis.com", "container.googleapis.com", "artifactregistry.googleapis.com", "binaryauthorization.googleapis.com", "iam.googleapis.com"]:
        assert api in main_tf

    # 2. Verify Cloud Run concurrency demo service
    assert "resource \"google_cloud_run_v2_service\" \"conductor_demo_service\"" in main_tf
    assert "max_instance_request_concurrency = 80" in main_tf
    assert "gemini-3.5-flash" in main_tf

    # 3. Verify GKE Autopilot multi-cluster mesh
    assert "resource \"google_container_cluster\" \"autopilot_mesh_demo\"" in main_tf
    assert "enable_autopilot = true" in main_tf

    # 4. Verify Artifact Registry SLSA Level 3 immutable repo
    assert "resource \"google_artifact_registry_repository\" \"slsa_repo\"" in main_tf
    assert "immutable_tags = true" in main_tf

    # 5. Verify Workload Identity Pool
    assert "resource \"google_iam_workload_identity_pool\" \"enterprise_pool\"" in main_tf
    assert "disabled                  = false" in main_tf


def test_terraform_outputs_alignment(terraform_dir: Path) -> None:
    outputs_tf = (terraform_dir / "outputs.tf").read_text(encoding="utf-8")
    expected_outputs = [
        "output \"cloud_run_service_url\"",
        "output \"gke_cluster_endpoint\"",
        "output \"artifact_registry_repository_uri\"",
        "output \"workload_identity_pool_name\"",
        "output \"console_verification_urls\"",
    ]
    for out_def in expected_outputs:
        assert out_def in outputs_tf, f"Missing output [{out_def}] in outputs.tf"

    # Ensure URLs match console origin patterns expected by DemoScriptAgentService
    assert "https://console.cloud.google.com/run?project=" in outputs_tf
    assert "https://console.cloud.google.com/kubernetes?project=" in outputs_tf
    assert "https://console.cloud.google.com/artifacts?project=" in outputs_tf
    assert "https://console.cloud.google.com/monitoring?project=" in outputs_tf


def test_shell_script_syntax_and_execution(terraform_dir: Path) -> None:
    script_path = terraform_dir / "test_and_deploy_sandboxes.sh"
    # Verify execution returns 0
    result = subprocess.run(["bash", str(script_path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"Script execution failed with error: {result.stderr}"
    assert "Phase 5: Testing and Validating Demo Sandbox Terraform Infrastructure" in result.stdout
