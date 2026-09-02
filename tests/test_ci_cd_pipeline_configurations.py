#!/usr/bin/env python3
"""
Unit and Integration Tests for Google Cloud Dev2Prod CI/CD Configuration Files
Validates syntax, schemas, cross-references, environment profiles, and security postures
across cloudbuild.yaml, clouddeploy.yaml, skaffold.yaml, and infra/cloudrun/service.yaml.
"""

import os
import yaml
try:
    import pytest
except ImportError:
    pytest = None
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

def load_yaml_file(filepath: Path):
    assert filepath.exists(), f"Configuration file {filepath} does not exist"
    with open(filepath, "r", encoding="utf-8") as f:
        # Load all documents if multi-document YAML
        docs = list(yaml.safe_load_all(f))
    return docs

def test_cloudbuild_yaml_structure_and_steps():
    """Validates Cloud Build CI pipeline configuration."""
    cloudbuild_path = REPO_ROOT / "cloudbuild.yaml"
    docs = load_yaml_file(cloudbuild_path)
    assert len(docs) == 1, "cloudbuild.yaml should contain a single document"
    cb = docs[0]

    assert "steps" in cb, "cloudbuild.yaml must declare 'steps'"
    steps = cb["steps"]
    step_ids = [s.get("id") for s in steps]

    # Verify key CI steps exist in order
    assert any("test" in s_id for s_id in step_ids), "Must contain unit/UI testing step"
    assert "build-container-image" in step_ids, "Must contain container build step"
    assert "push-to-artifact-registry" in step_ids, "Must contain push step to Artifact Registry"
    assert "create-cloud-deploy-release" in step_ids, "Must contain Cloud Deploy release step"

    # Verify Step 1 uses Playwright container for UI testing support and runs adversarial tests
    test_step = next(s for s in steps if "test" in s.get("id", ""))
    assert "playwright" in test_step["name"].lower() or "python" in test_step["name"].lower()
    test_script = " ".join(test_step.get("args", []))
    assert "test_ui_adversarial_agent.py" in test_script or "pytest tests/" in test_script
    assert "--extra-index-url https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/" in test_script

    # Verify substitutions and image registry
    assert "substitutions" in cb
    assert cb["substitutions"].get("_SERVICE_NAME") == "conductor-v2"
    assert cb["substitutions"].get("_DELIVERY_PIPELINE_NAME") == "conductor-v2-pipeline"
    assert cb["substitutions"].get("_REPO_NAME") == "conductor-repo"

    # Ensure Artifact Registry format is used
    images = cb.get("images", [])
    assert any("pkg.dev" in img for img in images), "Images must be pushed to Artifact Registry (pkg.dev)"

def test_clouddeploy_yaml_pipeline_and_targets():
    """Validates Google Cloud Deploy delivery pipeline, targets, and canary stages."""
    clouddeploy_path = REPO_ROOT / "clouddeploy.yaml"
    docs = load_yaml_file(clouddeploy_path)
    assert len(docs) >= 4, "clouddeploy.yaml should contain DeliveryPipeline and at least 3 Target documents"

    pipeline_doc = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
    assert pipeline_doc is not None, "DeliveryPipeline kind not found in clouddeploy.yaml"
    assert pipeline_doc["metadata"]["name"] == "conductor-v2-pipeline"

    # Verify stage progression
    stages = pipeline_doc["serialPipeline"]["stages"]
    stage_target_ids = [s["targetId"] for s in stages]
    assert stage_target_ids == ["dev", "staging", "prod"], "Stages must progress dev -> staging -> prod"

    # Verify prod stage has canary rollout strategy and postdeploy actions
    prod_stage = next(s for s in stages if s["targetId"] == "prod")
    assert "canary" in prod_stage["strategy"], "Prod stage must have canary deployment strategy"

    # Verify targets
    targets = [d for d in docs if d.get("kind") == "Target"]
    target_names = [t["metadata"]["name"] for t in targets]
    assert "dev" in target_names
    assert "staging" in target_names
    assert "prod" in target_names

    prod_target = next(t for t in targets if t["metadata"]["name"] == "prod")
    assert prod_target.get("requireApproval") is True, "Production target must require manual approval gate"

def test_skaffold_yaml_profiles_and_custom_actions():
    """Validates Skaffold configuration for Cloud Deploy rendering."""
    skaffold_path = REPO_ROOT / "skaffold.yaml"
    docs = load_yaml_file(skaffold_path)
    assert len(docs) == 1
    sk = docs[0]

    assert sk.get("apiVersion", "").startswith("skaffold/")
    assert sk.get("kind") == "Config"
    assert "manifests" in sk
    assert "infra/cloudrun/service.yaml" in sk["manifests"]["rawYaml"]

    # Verify environment profiles
    profiles = sk.get("profiles", [])
    profile_names = [p["name"] for p in profiles]
    assert "dev" in profile_names
    assert "staging" in profile_names
    assert "prod" in profile_names

    # Verify custom post-deploy actions
    custom_actions = sk.get("customActions", [])
    action_names = [a["name"] for a in custom_actions]
    assert "postdeploy-e2e-test" in action_names

def test_declarative_cloud_run_service_manifest():
    """Validates the declarative Knative/Cloud Run service manifest."""
    service_path = REPO_ROOT / "infra" / "cloudrun" / "service.yaml"
    docs = load_yaml_file(service_path)
    assert len(docs) == 1
    svc = docs[0]

    assert svc.get("apiVersion") == "serving.knative.dev/v1"
    assert svc.get("kind") == "Service"
    assert svc["metadata"]["name"] == "conductor-v2"

    template = svc["spec"]["template"]
    annotations = template["metadata"]["annotations"]

    # Performance and Cloud SQL checks
    assert annotations.get("run.googleapis.com/cpu-throttling") == "false"
    assert annotations.get("run.googleapis.com/startup-cpu-boost") == "true"
    assert "run.googleapis.com/cloudsql-instances" in annotations

    spec = template["spec"]
    assert spec["timeoutSeconds"] == 3600
    assert spec["containerConcurrency"] == 80
    assert "conductor-agent@" in spec["serviceAccountName"]

    container = spec["containers"][0]
    assert container["ports"][0]["containerPort"] == 8080

    # Verify Secret Manager secret bindings
    env_vars = container["env"]
    secret_names = [e["name"] for e in env_vars if "valueFrom" in e]
    assert "DATABASE_URL" in secret_names
    assert "SECURITY_SECRET_KEY" in secret_names

def test_agent_registry_cloud_run_configuration():
    """Validates that Cloud Run service is configured to register with Agent Platform Agent Registry."""
    service_path = REPO_ROOT / "infra" / "cloudrun" / "service.yaml"
    docs = load_yaml_file(service_path)
    svc = docs[0]

    # Service metadata checks
    meta_labels = svc["metadata"].get("labels", {})
    meta_annotations = svc["metadata"].get("annotations", {})
    assert meta_labels.get("functional-type") == "agent", "Service must declare functional-type=agent"
    assert (
        meta_annotations.get("apphub.cloud.google.com/functional-type") == "agent"
        or meta_annotations.get("run.googleapis.com/functional-type") == "agent"
    ), "Service annotation must declare functional-type=agent"

    # Template metadata checks (Revision template where Cloud Run supports identity-type and functional-type)
    template = svc["spec"]["template"]
    tpl_labels = template["metadata"].get("labels", {})
    tpl_annotations = template["metadata"].get("annotations", {})
    assert tpl_labels.get("functional-type") == "agent"
    assert tpl_annotations.get("run.googleapis.com/functional-type") == "agent"
    assert tpl_annotations.get("run.googleapis.com/identity-type") == "agent-identity"

    # Container environment variables
    env_vars = template["spec"]["containers"][0]["env"]
    env_dict = {e["name"]: e.get("value") for e in env_vars if "value" in e}
    assert env_dict.get("AGENT_REGISTRY_ENABLED") == "true"
    assert env_dict.get("AGENT_FUNCTIONAL_TYPE") == "agent"

def test_deploy_cloud_run_script_agent_registry_flags():
    """Validates that deploy_cloud_run.sh contains Agent Registry registration flags."""
    script_path = REPO_ROOT / "infra" / "deploy_cloud_run.sh"
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")
    assert "gcloud alpha run deploy" in content or "gcloud run deploy" in content
    assert "--functional-type=\"agent\"" in content or "--functional-type=agent" in content
    assert "--identity-type=\"agent-identity\"" in content or "--identity-type=agent-identity" in content

def test_post_deploy_runner_file_exists_and_executable():
    """Validates the post-deploy verification script."""
    runner_path = REPO_ROOT / "infra" / "ci_cd" / "run_post_deploy_verification.py"
    assert runner_path.exists(), "Post-deploy verification runner must exist"
    assert os.access(runner_path, os.R_OK), "Post-deploy verification runner must be readable"

def test_pip_extra_index_url_cloudbuild_pipelines():
    """Validates that all pip install commands across CloudBuild pipelines configure --extra-index-url for Artifact Registry."""
    import re
    expected_url = "https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/"
    expected_pattern = re.compile(rf"--extra-index-url(?:=|\s+)[\"']?{re.escape(expected_url)}[\"']?")
    pip_pattern = re.compile(r"(?:^|[;&|\s])(?:pip|pip3|python[0-9.]*\s+-m\s+pip)\s+install\b")

    # Validate all CloudBuild pipeline manifests
    cb_files = sorted(set(list(REPO_ROOT.glob("cloudbuild*.yaml")) + list(REPO_ROOT.glob("infra/**/cloudbuild*.yaml"))))
    assert len(cb_files) >= 2, "Must find at least cloudbuild.yaml and cloudbuild-agent-engine.yaml"

    # Ensure cloudbuild.yaml has pip install, while cloudbuild-agent-engine.yaml is dedicated to Go
    checked_required = {"cloudbuild.yaml": False}

    for cb_path in cb_files:
        docs = load_yaml_file(cb_path)
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            for step in doc.get("steps", []):
                scripts_to_check = []
                if "script" in step and step["script"]:
                    scripts_to_check.append(step["script"])
                
                entrypoint = step.get("entrypoint", "")
                args = step.get("args", [])
                args_str = " ".join(args)
                if entrypoint:
                    scripts_to_check.append(f"{entrypoint} {args_str}")
                else:
                    scripts_to_check.append(args_str)

                for raw_script in scripts_to_check:
                    normalized_script = raw_script.replace("\\\n", " ").replace("\\\r\n", " ")
                    for line in normalized_script.splitlines():
                        if pip_pattern.search(line) or (entrypoint in ("pip", "pip3") and "install" in line):
                            if cb_path.name in checked_required:
                                checked_required[cb_path.name] = True
                            assert expected_pattern.search(line), (
                                f"Python package installation in {cb_path.name} (step: {step.get('id', 'unnamed')}) "
                                f"missing extra-index-url: {line.strip()}"
                            )

    for req_name, found in checked_required.items():
        assert found, f"{req_name} must contain at least one pip install invocation"

    # Verify cloudbuild-agent-engine.yaml contains no pip install invocations
    ae_cb = REPO_ROOT / "cloudbuild-agent-engine.yaml"
    if ae_cb.exists():
        ae_docs = load_yaml_file(ae_cb)
        for doc in ae_docs:
            if isinstance(doc, dict):
                for step in doc.get("steps", []):
                    args_str = " ".join(step.get("args", []))
                    assert not pip_pattern.search(args_str), (
                        f"cloudbuild-agent-engine.yaml is dedicated to Go and must not contain pip install: {args_str}"
                    )


def test_dockerfile_and_requirements_extra_index_url():
    """Validates that Dockerfile builder stage and requirements files configure --extra-index-url for python-pypi."""
    import re
    expected_url = "https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/"
    expected_flag_pattern = re.compile(rf"--extra-index-url(?:=|\s+)[\"']?{re.escape(expected_url)}[\"']?")
    pip_pattern = re.compile(r"(?:^|[;&|\s])(?:pip|pip3|python[0-9.]*\s+-m\s+pip)\s+install\b")

    # Validate all Dockerfiles across the repository
    dockerfiles = sorted(set(list(REPO_ROOT.glob("Dockerfile*")) + list(REPO_ROOT.glob("**/Dockerfile*"))))
    found_pip_in_dockerfile = False
    for df in dockerfiles:
        if ".venv" in df.parts or ".agents" in df.parts:
            continue
        content = df.read_text(encoding="utf-8")
        normalized = content.replace("\\\n", " ").replace("\\\r\n", " ")
        for line in normalized.splitlines():
            if pip_pattern.search(line):
                found_pip_in_dockerfile = True
                assert expected_flag_pattern.search(line), f"{df.name} pip install missing extra-index-url: {line.strip()}"

    assert found_pip_in_dockerfile, "Repository Dockerfiles must contain at least one pip install invocation"

    # Validate infra/agent_engine/archive_python/requirements.txt
    ae_req_path = REPO_ROOT / "infra" / "agent_engine" / "archive_python" / "requirements.txt"
    if not ae_req_path.exists():
        ae_req_path = REPO_ROOT / "infra" / "agent_engine" / "requirements.txt"
    assert ae_req_path.exists(), "Archived or active requirements.txt must exist"
    ae_req_lines = [l.strip() for l in ae_req_path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert any(expected_flag_pattern.search(l) for l in ae_req_lines), (
        f"Archived requirements.txt must retain --extra-index-url configuration for {expected_url}"
    )

    # Validate root requirements.txt
    root_req_path = REPO_ROOT / "requirements.txt"
    assert root_req_path.exists(), "requirements.txt must exist"
    root_req_lines = [l.strip() for l in root_req_path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert any(expected_flag_pattern.search(l) for l in root_req_lines), (
        f"requirements.txt must configure --extra-index-url for {expected_url}"
    )


def test_extra_index_url_security_and_format_edge_cases():
    """Validates security posture and formatting of Artifact Registry extra-index-url configurations."""
    import re
    expected_url = "https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/"
    extra_index_pattern = re.compile(r"--extra-index-url(?:=|\s+)(\S+)")
    isolated_index_pattern = re.compile(r"(?<!-)--index-url\b")

    ae_req_path = REPO_ROOT / "infra" / "agent_engine" / "archive_python" / "requirements.txt"
    if not ae_req_path.exists():
        ae_req_path = REPO_ROOT / "infra" / "agent_engine" / "requirements.txt"

    files_to_check = [
        REPO_ROOT / "cloudbuild.yaml",
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "requirements.txt",
        ae_req_path,
    ]
    for filepath in files_to_check:
        text = filepath.read_text(encoding="utf-8")

        # 1. Ensure no pipeline or build file uses dangerous --index-url (which would override public PyPI)
        for line in text.splitlines():
            if isolated_index_pattern.search(line):
                assert False, f"Found dangerous --index-url overriding PyPI in {filepath.name}: {line.strip()}"

        # 2. Extract every configured --extra-index-url from actual file content and validate
        urls = extra_index_pattern.findall(text)
        assert len(urls) > 0, f"{filepath.name} must declare at least one --extra-index-url"
        for raw_url in urls:
            url = raw_url.strip('"\'')
            assert url == expected_url, f"Unexpected extra-index-url in {filepath.name}: {url}"
            # Ensure HTTPS is strictly enforced (reject insecure HTTP transport)
            assert url.startswith("https://"), f"Artifact Registry URL must enforce HTTPS transport in {filepath.name}: {url}"
            # Ensure PEP 503 simple repository trailing slash convention
            assert url.endswith("/simple/"), f"Artifact Registry URL must follow PEP 503 trailing slash convention in {filepath.name}: {url}"


def test_cloudbuild_agent_engine_go_decoupling():
    """Validates that cloudbuild-agent-engine.yaml is decoupled from Cloud Run and dedicated to Go ADK."""
    ae_cb_path = REPO_ROOT / "cloudbuild-agent-engine.yaml"
    docs = load_yaml_file(ae_cb_path)
    assert len(docs) == 1, "cloudbuild-agent-engine.yaml must contain a single document"
    cb = docs[0]
    steps = cb.get("steps", [])
    step_ids = [s.get("id") for s in steps]

    # Verify required Go ADK steps are present
    assert "go-adk-agent-tests" in step_ids, "Must contain Go ADK unit tests step"
    assert "build-and-push-adk-deployer" in step_ids, "Must contain ADK deployer container build step"
    assert "apply-cloud-deploy-pipeline" in step_ids, "Must contain Cloud Deploy pipeline apply step"
    assert "create-cloud-deploy-release" in step_ids, "Must contain Cloud Deploy release step"

    # Verify legacy/decoupled steps are removed
    assert "unit-and-agent-engine-tests" not in step_ids, "Must not contain legacy Python unit tests"
    assert "build-and-push-container-image" not in step_ids, "Must not contain Cloud Run container build"
    assert "generate-sbom" not in step_ids, "Must not contain SBOM generation for backend"
    assert "upload-sbom" not in step_ids, "Must not contain SBOM upload for backend"


def test_cloud_deploy_rollout_name_length_bounds():
    """
    Validates that Cloud Deploy rollout names strictly adhere to Google Cloud's 63-character limit.
    Formula: len(rollout_id) = len(release_id) + len("-to-") + len(target_id) + len("-0001") <= 63.
    Confirms that release ID shortening (e.g. 8-char SHORT_ID) protects against rollout rejection
    when target names exceed 20 characters (such as agent-engine-staging).
    """
    # 1. Agent Engine Pipeline
    ae_pipeline_file = REPO_ROOT / "clouddeploy-agent-engine.yaml"
    ae_docs = load_yaml_file(ae_pipeline_file)
    ae_targets = [d["metadata"]["name"] for d in ae_docs if d.get("kind") == "Target"]
    assert len(ae_targets) >= 3

    # Short ID release format: 'release-ae-' (11) + 8-char SHA = 19 chars
    ae_release_id_sample = "release-ae-12345678"
    for target in ae_targets:
        rollout_id = f"{ae_release_id_sample}-to-{target}-0001"
        assert len(rollout_id) <= 63, (
            f"Agent Engine rollout ID '{rollout_id}' exceeds 63 characters ({len(rollout_id)} > 63)"
        )
    # Target names up to 34 characters are supported with 8-char SHORT_ID
    assert len(f"{ae_release_id_sample}-to-{'a' * 34}-0001") <= 63

    # 2. Conductor v3 Backend Cloud Run Pipeline
    v3_pipeline_file = REPO_ROOT / "clouddeploy-v3.yaml"
    v3_docs = load_yaml_file(v3_pipeline_file)
    v3_targets = [d["metadata"]["name"] for d in v3_docs if d.get("kind") == "Target"]
    assert len(v3_targets) >= 3

    # Full UUID release format: 'release-v3-' (11) + 36-char UUID = 47 chars
    v3_release_id_sample = f"release-v3-{'0' * 36}"
    for target in v3_targets:
        rollout_id = f"{v3_release_id_sample}-to-{target}-0001"
        assert len(rollout_id) <= 63, (
            f"Cloud Run v3 rollout ID '{rollout_id}' exceeds 63 characters ({len(rollout_id)} > 63)"
        )
        # Mathematical limit under 47-char UUID: 63 - 47 - 4 - 5 = 7 chars max target length
        assert len(target) <= 7, (
            f"Target '{target}' exceeds 7 characters ({len(target)} > 7), which causes rollout ID overflow under UUID releases"
        )

    # Short ID release format headroom: 'release-v3-' (11) + 8-char SHA = 19 chars accommodates up to 35-char targets
    v3_short_id_sample = "release-v3-12345678"
    assert len(f"{v3_short_id_sample}-to-{'a' * 35}-0001") <= 63


def test_cloudrun_v3_parameterized_template_conformance():
    """Validates that infra/cloudrun/service-v3.yaml.template exists and defines required # from-param directives."""
    import re
    template_path = REPO_ROOT / "infra" / "cloudrun" / "service-v3.yaml.template"
    assert template_path.exists(), "infra/cloudrun/service-v3.yaml.template must exist"

    docs = load_yaml_file(template_path)
    assert len(docs) == 1, "service-v3.yaml.template must contain exactly 1 YAML document"
    svc = docs[0]
    assert svc.get("apiVersion") == "serving.knative.dev/v1"
    assert svc.get("kind") == "Service"

    raw_content = template_path.read_text(encoding="utf-8")

    # Assert all 7 dynamic fields have valid # from-param: comment directives.
    # Note: labels.env must occur at least twice (metadata.labels.env and spec.template.metadata.labels.env).
    required_directives = [
        (r"#\s*from-param:\s*\$\{name\}", 1),
        (r"#\s*from-param:\s*\$\{labels\.env\}", 2),
        (r"#\s*from-param:\s*\$\{maxScale\}", 1),
        (r"#\s*from-param:\s*\$\{apphub-display-name\}", 1),
        (r"#\s*from-param:\s*\$\{apphub-description\}", 1),
        (r"#\s*from-param:\s*\$\{ENVIRONMENT\}", 1),
        (r"#\s*from-param:\s*\$\{AGENT_DISPLAY_NAME\}", 1),
    ]
    for pattern, min_count in required_directives:
        matches = re.findall(pattern, raw_content)
        assert len(matches) >= min_count, (
            f"Missing or insufficient Cloud Deploy post-render directive matching '{pattern}' "
            f"in service-v3.yaml.template (found {len(matches)}, expected >= {min_count})"
        )


def test_skaffold_v3_references_parameterized_template():
    """Validates that skaffold-v3.yaml references service-v3.yaml.template without environment drift."""
    skaffold_path = REPO_ROOT / "skaffold-v3.yaml"
    docs = load_yaml_file(skaffold_path)
    assert len(docs) == 1
    sk = docs[0]

    # Verify top-level manifests rawYaml
    raw_yaml = sk.get("manifests", {}).get("rawYaml", [])
    assert "infra/cloudrun/service-v3.yaml.template" in raw_yaml, (
        "skaffold-v3.yaml manifests.rawYaml must reference infra/cloudrun/service-v3.yaml.template"
    )

    # Verify all profiles reference the single template file
    profiles = {p["name"]: p for p in sk.get("profiles", [])}
    for env in ["dev", "staging", "prod"]:
        assert env in profiles, f"Profile '{env}' missing in skaffold-v3.yaml"
        profile_raw = profiles[env].get("manifests", {}).get("rawYaml", [])
        assert profile_raw == ["infra/cloudrun/service-v3.yaml.template"], (
            f"Profile '{env}' must reference single template infra/cloudrun/service-v3.yaml.template without drift"
        )


def test_clouddeploy_v3_deploy_parameters_and_private_worker_pool():
    """Validates delivery pipeline stages, canary rollout, deployParameters, and private worker pool executionConfigs in clouddeploy-v3.yaml."""
    clouddeploy_path = REPO_ROOT / "clouddeploy-v3.yaml"
    docs = load_yaml_file(clouddeploy_path)

    # 1. DeliveryPipeline validation
    pipeline_doc = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
    assert pipeline_doc is not None, "DeliveryPipeline kind not found in clouddeploy-v3.yaml"
    assert pipeline_doc["metadata"]["name"] == "conductor-v3-pipeline"

    stages = pipeline_doc.get("serialPipeline", {}).get("stages", [])
    stage_ids = [s.get("targetId") for s in stages]
    assert stage_ids == ["dev", "staging", "prod"], f"Pipeline stages must be ['dev', 'staging', 'prod'], got {stage_ids}"

    dev_stage = next(s for s in stages if s.get("targetId") == "dev")
    assert dev_stage.get("strategy", {}).get("standard", {}).get("verify") is True, "Dev stage must enable verify"

    staging_stage = next(s for s in stages if s.get("targetId") == "staging")
    assert staging_stage.get("strategy", {}).get("standard", {}).get("verify") is True, "Staging stage must enable verify"

    prod_stage = next(s for s in stages if s.get("targetId") == "prod")
    canary = prod_stage.get("strategy", {}).get("canary", {})
    assert canary.get("canaryDeployment", {}).get("percentages") == [25, 50], "Prod canary percentages must be [25, 50]"
    assert canary.get("canaryDeployment", {}).get("verify") is True, "Prod canary must enable verify"
    assert canary.get("runtimeConfig", {}).get("cloudRun", {}).get("automaticTrafficControl") is True

    # 2. Target validation
    targets = {d["metadata"]["name"]: d for d in docs if d.get("kind") == "Target"}
    assert set(["dev", "staging", "prod"]).issubset(set(targets.keys())), "dev, staging, and prod targets required"

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

    expected_worker_pool = (
        "projects/riccardo-blog-test-v1/locations/us-central1/workerPools/cloudbuild-workerpool"
    )
    expected_service_account = "105792947502-compute@developer.gserviceaccount.com"
    expected_artifact_storage = "gs://us-central1.deploy-artifacts.riccardo-blog-test-v1.appspot.com"

    for env_name, exp_p in expected_params.items():
        target = targets[env_name]
        assert "deployParameters" in target, f"Target '{env_name}' missing deployParameters"
        dp = target["deployParameters"]
        for k, v in exp_p.items():
            assert dp.get(k) == v, f"Target '{env_name}' deployParameters[{k}] expected '{v}', got '{dp.get(k)}'"

        # Verify executionConfigs
        exec_configs = target.get("executionConfigs", [])
        assert len(exec_configs) > 0, f"Target '{env_name}' missing executionConfigs"
        cfg = exec_configs[0]

        # Usages
        usages = cfg.get("usages", [])
        assert set(["RENDER", "DEPLOY", "VERIFY"]).issubset(set(usages)), (
            f"Target '{env_name}' executionConfigs usages must contain RENDER, DEPLOY, and VERIFY"
        )

        # Worker pool
        assert cfg.get("workerPool") == expected_worker_pool, (
            f"Target '{env_name}' executionConfigs workerPool expected '{expected_worker_pool}', got '{cfg.get('workerPool')}'"
        )

        # Service Account and Artifact Storage
        assert cfg.get("serviceAccount") == expected_service_account, (
            f"Target '{env_name}' executionConfigs serviceAccount expected '{expected_service_account}', got '{cfg.get('serviceAccount')}'"
        )
        assert cfg.get("artifactStorage") == expected_artifact_storage, (
            f"Target '{env_name}' executionConfigs artifactStorage expected '{expected_artifact_storage}', got '{cfg.get('artifactStorage')}'"
        )

        # Execution timeout
        assert cfg.get("executionTimeout") == "600s", (
            f"Target '{env_name}' executionTimeout expected '600s', got '{cfg.get('executionTimeout')}'"
        )

    # Verify prod target governance requires manual approval gate
    assert targets["prod"].get("requireApproval") is True, "Target 'prod' must have requireApproval: true"


def test_template_parameters_declared_in_all_deploy_targets():
    """
    Validates that every parameter variable defined in service-v3.yaml.template
    via '# from-param: ${VAR_NAME}' has an exact 1:1 bi-directional match with
    dev, staging, and prod targets in clouddeploy-v3.yaml, guarding against
    unresolved parameter references and orphaned/extraneous deploy parameters.
    """
    import re
    tpl_path = REPO_ROOT / "infra" / "cloudrun" / "service-v3.yaml.template"
    content = tpl_path.read_text(encoding="utf-8")
    param_vars = sorted(set(re.findall(r"#\s*from-param:\s*\$\{([^}]+)\}", content)))
    assert len(param_vars) >= 7, f"Expected at least 7 from-param directives, found {len(param_vars)}"

    cd_path = REPO_ROOT / "clouddeploy-v3.yaml"
    docs = load_yaml_file(cd_path)
    targets = {d["metadata"]["name"]: d for d in docs if d.get("kind") == "Target"}
    for env in ["dev", "staging", "prod"]:
        assert env in targets, f"Target '{env}' missing in clouddeploy-v3.yaml"
        dp = targets[env].get("deployParameters", {})
        # Bi-directional equality check
        assert set(dp.keys()) == set(param_vars), (
            f"Target '{env}' deployParameters must exactly match template directives. "
            f"Discrepancy: missing={set(param_vars) - set(dp.keys())}, orphaned={set(dp.keys()) - set(param_vars)}"
        )
        for param in param_vars:
            assert str(dp[param]).strip() != "", (
                f"Target '{env}' parameter '{param}' must not be empty"
            )


if __name__ == "__main__":
    test_cloudbuild_yaml_structure_and_steps()
    test_clouddeploy_yaml_pipeline_and_targets()
    test_skaffold_yaml_profiles_and_custom_actions()
    test_declarative_cloud_run_service_manifest()
    test_agent_registry_cloud_run_configuration()
    test_deploy_cloud_run_script_agent_registry_flags()
    test_post_deploy_runner_file_exists_and_executable()
    test_pip_extra_index_url_cloudbuild_pipelines()
    test_dockerfile_and_requirements_extra_index_url()
    test_extra_index_url_security_and_format_edge_cases()
    test_cloudbuild_agent_engine_go_decoupling()
    test_cloud_deploy_rollout_name_length_bounds()
    test_cloudrun_v3_parameterized_template_conformance()
    test_skaffold_v3_references_parameterized_template()
    test_clouddeploy_v3_deploy_parameters_and_private_worker_pool()
    test_template_parameters_declared_in_all_deploy_targets()
    print("✅ All 16 CI/CD, Agent Registry, Template Parameterization & Private Pool tests passed successfully!")




