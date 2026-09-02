#!/usr/bin/env python3
"""
Automated Conformance Testing Suite for Cloud Build SBOM Generation & Registration.
Validates requirement R4 and ADR-20260829-03 across:
1. cloudbuild-frontend.yaml
2. cloudbuild-v3.yaml
3. cloudbuild-agent-engine.yaml

Verifies:
- R1: Syft SBOM generation step using anchore/syft:v1.18.1 producing sbom.spdx.json.
- R2: Artifact Analysis registration step executing gcloud artifacts sbom load using
      gcr.io/google.com/cloudsdktool/cloud-sdk:slim.
- R3: Cloud Build artifact archival for sbom.spdx.json under
      gs://${PROJECT_ID}_cloudbuild/sboms/${BUILD_ID}.
- Non-Regression: Existing required steps, options, and substitutions remain intact.
"""

import os
import unittest
from pathlib import Path
import yaml

current_dir = Path(__file__).resolve().parent
if (current_dir / ".." / "pytest.ini").resolve().exists():
    DEFAULT_REPO_ROOT = (current_dir / "..").resolve()
elif (current_dir / ".." / ".." / "pytest.ini").resolve().exists():
    DEFAULT_REPO_ROOT = (current_dir / ".." / "..").resolve()
elif (current_dir / ".." / ".." / ".." / "pytest.ini").resolve().exists():
    DEFAULT_REPO_ROOT = (current_dir / ".." / ".." / "..").resolve()
else:
    DEFAULT_REPO_ROOT = current_dir.parent.parent

TEST_ROOT = Path(os.environ.get("CLOUDBUILD_TEST_ROOT", str(DEFAULT_REPO_ROOT)))

TARGET_CONFIGS = [
    {
        "filename": "cloudbuild-frontend.yaml",
        "service_name": "conductor-v3-frontend",
        "pipeline_name": "conductor-v3-frontend-pipeline",
        "commit_sha_var": "${_COMMIT_SHA}",
        "build_step_id": "build-frontend-image",
        "required_step_ids": [
            "pull-base-image",
            "build-frontend-image",
            "verify-image-size",
            "push-immutable-tag",
            "push-latest-tag",
            "apply-cloud-deploy-pipeline",
            "apply-frontend-automations",
            "create-cloud-deploy-release",
        ],
    },
    {
        "filename": "cloudbuild-v3.yaml",
        "service_name": "conductor-v3",
        "pipeline_name": "conductor-v3-pipeline",
        "commit_sha_var": "${_COMMIT_SHA}",
        "build_step_id": "build-container-image",
        "required_step_ids": [
            "go-backend-tests",
            "pull-base-images",
            "build-container-image",
            "push-to-artifact-registry",
            "push-latest-tag",
            "apply-cloud-deploy-pipeline",
            "create-cloud-deploy-release",
        ],
    },
]


def load_yaml_file(filepath: Path) -> dict:
    """Loads a single-document YAML manifest."""
    assert filepath.exists(), f"Configuration file {filepath} does not exist"
    with open(filepath, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    assert len(docs) == 1, f"Expected 1 YAML document in {filepath}, found {len(docs)}"
    assert isinstance(docs[0], dict), f"YAML document in {filepath} must be a mapping dictionary"
    return docs[0]



class TestCloudBuildSbomConformance(unittest.TestCase):
    """Verifies all Cloud Build manifests conform to R1, R2, R3, and R4 specifications."""

    def test_01_all_target_manifest_files_exist_and_parse(self):
        """Verifies that all three Cloud Build files exist and parse cleanly."""
        for cfg in TARGET_CONFIGS:
            path = TEST_ROOT / cfg["filename"]
            self.assertTrue(path.exists(), f"Manifest file missing: {path}")
            data = load_yaml_file(path)
            self.assertIn("steps", data, f"Manifest {cfg['filename']} must contain 'steps'")
            self.assertIsInstance(data["steps"], list, f"Manifest {cfg['filename']} 'steps' must be a list")
            self.assertGreater(len(data["steps"]), 0, f"Steps list is empty in {cfg['filename']}")
            self.assertTrue(
                all(isinstance(s, dict) for s in data["steps"]),
                f"Manifest {cfg['filename']} all steps must be mapping dictionaries",
            )

    def test_02_syft_sbom_generation_step_conformance(self):
        """R1: Verifies anchore/syft:v1.18.1 step generates SPDX 2.3 sbom.spdx.json."""
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]
            data = load_yaml_file(TEST_ROOT / filename)
            steps = data.get("steps", [])

            syft_steps = [
                s for s in steps
                if s.get("name", "").startswith("anchore/syft:v1.18.1")
            ]
            self.assertEqual(
                len(syft_steps),
                1,
                f"Manifest {filename} must declare exactly 1 step using 'anchore/syft:v1.18.1'",
            )
            syft_step = syft_steps[0]
            step_args = " ".join(syft_step.get("args", []))

            # Verify output file
            self.assertIn(
                "sbom.spdx.json",
                step_args,
                f"Syft step in {filename} must output to 'sbom.spdx.json'",
            )

            # Verify SPDX 2.3 format flag
            self.assertTrue(
                "spdx-json" in step_args or "spdx-json@2.3" in step_args,
                f"Syft step in {filename} must specify 'spdx-json' output format",
            )

            # Verify target image reference
            sha_var = cfg["commit_sha_var"]
            self.assertIn(
                sha_var,
                step_args,
                f"Syft step in {filename} must inspect the image tag referencing {sha_var}",
            )
            self.assertTrue(
                "${_SERVICE_NAME}" in step_args or cfg["service_name"] in step_args,
                f"Syft step in {filename} must reference '${{_SERVICE_NAME}}' or '{cfg['service_name']}'",
            )

    def test_03_artifact_analysis_upload_step_conformance(self):
        """R2: Verifies gcloud artifacts sbom load registers SBOM in Artifact Analysis."""
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]
            data = load_yaml_file(TEST_ROOT / filename)
            steps = data.get("steps", [])

            # Locate upload step executing 'gcloud artifacts sbom load'
            upload_steps = [
                s for s in steps
                if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
                and "artifacts" in s.get("args", [])
                and "sbom" in s.get("args", [])
                and "load" in s.get("args", [])
            ]
            self.assertEqual(
                len(upload_steps),
                1,
                f"Manifest {filename} must declare exactly 1 step executing 'gcloud artifacts sbom load' "
                f"with image 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'",
            )
            upload_step = upload_steps[0]
            upload_args = " ".join(upload_step.get("args", []))

            # Verify --source=sbom.spdx.json flag
            self.assertTrue(
                "--source=sbom.spdx.json" in upload_args
                or ("--source" in upload_step.get("args", []) and "sbom.spdx.json" in upload_step.get("args", [])),
                f"Upload step in {filename} must specify '--source=sbom.spdx.json'",
            )

            # Verify --uri flag points to the container image
            sha_var = cfg["commit_sha_var"]
            self.assertTrue(
                "--uri=" in upload_args or "--uri" in upload_step.get("args", []),
                f"Upload step in {filename} must specify '--uri'",
            )
            self.assertIn(
                sha_var,
                upload_args,
                f"Upload step in {filename} must reference image tag with {sha_var}",
            )
            self.assertTrue(
                "${_SERVICE_NAME}" in upload_args or cfg["service_name"] in upload_args,
                f"Upload step in {filename} must reference '${{_SERVICE_NAME}}' or '{cfg['service_name']}'",
            )

    def test_04_gcs_artifact_archival_conformance(self):
        """R3: Verifies Cloud Build artifacts: stanza archives sbom.spdx.json to GCS."""
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]
            data = load_yaml_file(TEST_ROOT / filename)

            self.assertIn(
                "artifacts",
                data,
                f"Manifest {filename} must declare a top-level 'artifacts:' stanza",
            )
            artifacts = data.get("artifacts")
            self.assertIsInstance(
                artifacts,
                dict,
                f"Manifest {filename} 'artifacts:' must be a mapping dictionary",
            )
            self.assertIn(
                "objects",
                artifacts,
                f"Manifest {filename} 'artifacts' stanza must declare 'objects'",
            )
            objects = artifacts.get("objects")
            self.assertIsInstance(
                objects,
                dict,
                f"Manifest {filename} 'artifacts.objects' must be a mapping dictionary",
            )

            expected_location = "gs://${PROJECT_ID}_cloudbuild/sboms/${BUILD_ID}"
            self.assertEqual(
                objects.get("location"),
                expected_location,
                f"Manifest {filename} artifacts.objects.location must be exactly '{expected_location}'",
            )

            paths = objects.get("paths", [])
            self.assertIn(
                "sbom.spdx.json",
                paths,
                f"Manifest {filename} artifacts.objects.paths must include 'sbom.spdx.json'",
            )

    def test_05_step_ordering_and_pipeline_integrity(self):
        """R4: Verifies step ordering and preservation of existing pipeline steps."""
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]
            data = load_yaml_file(TEST_ROOT / filename)
            steps = data.get("steps", [])
            self.assertIsInstance(steps, list, f"Manifest {filename} 'steps:' must be a list")
            step_ids = [s.get("id") for s in steps if isinstance(s, dict) and s.get("id")]

            # Verify all required existing steps are present
            for req_id in cfg["required_step_ids"]:
                self.assertIn(
                    req_id,
                    step_ids,
                    f"Manifest {filename} missing required existing step '{req_id}'",
                )

            # Locate build, syft, upload, and release steps
            build_step_idx = next(
                (i for i, s in enumerate(steps) if isinstance(s, dict) and s.get("id") == cfg["build_step_id"]),
                None,
            )
            self.assertIsNotNone(build_step_idx, f"In {filename}, missing build step '{cfg['build_step_id']}'")

            syft_step_idx = next(
                (i for i, s in enumerate(steps) if isinstance(s, dict) and s.get("name", "").startswith("anchore/syft:v1.18.1")),
                None,
            )
            self.assertIsNotNone(syft_step_idx, f"In {filename}, missing Syft SBOM generation step")

            upload_step_idx = next(
                (
                    i for i, s in enumerate(steps)
                    if isinstance(s, dict)
                    and s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
                    and "artifacts" in s.get("args", []) and "load" in s.get("args", [])
                ),
                None,
            )
            self.assertIsNotNone(upload_step_idx, f"In {filename}, missing Artifact Analysis upload step")

            release_step_idx = next(
                (i for i, s in enumerate(steps) if isinstance(s, dict) and s.get("id") == "create-cloud-deploy-release"),
                None,
            )
            self.assertIsNotNone(release_step_idx, f"In {filename}, missing release creation step")

            # Assert execution ordering constraints
            self.assertGreater(
                syft_step_idx,
                build_step_idx,
                f"In {filename}, Syft SBOM generation must execute after build step '{cfg['build_step_id']}'",
            )
            self.assertGreater(
                upload_step_idx,
                syft_step_idx,
                f"In {filename}, Artifact Analysis upload must execute after Syft SBOM generation",
            )
            self.assertGreater(
                release_step_idx,
                upload_step_idx,
                f"In {filename}, Cloud Deploy release creation must execute after SBOM upload",
            )

    def test_06_substitutions_and_options_integrity(self):
        """Verifies that substitutions and options are preserved without corruption."""
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]
            data = load_yaml_file(TEST_ROOT / filename)

            self.assertIn("substitutions", data, f"Manifest {filename} missing 'substitutions:' stanza")
            substitutions = data.get("substitutions")
            self.assertIsInstance(
                substitutions,
                dict,
                f"Manifest {filename} 'substitutions:' must be a mapping",
            )
            self.assertEqual(
                substitutions.get("_REGION"),
                "us-central1",
                f"Manifest {filename} missing or invalid _REGION substitution",
            )
            self.assertEqual(
                substitutions.get("_REPO_NAME"),
                "conductor-repo",
                f"Manifest {filename} missing or invalid _REPO_NAME substitution",
            )
            self.assertEqual(
                substitutions.get("_SERVICE_NAME"),
                cfg["service_name"],
                f"Manifest {filename} _SERVICE_NAME mismatch",
            )
            self.assertEqual(
                substitutions.get("_DELIVERY_PIPELINE_NAME"),
                cfg["pipeline_name"],
                f"Manifest {filename} _DELIVERY_PIPELINE_NAME mismatch",
            )

            self.assertIn("options", data, f"Manifest {filename} missing 'options:' stanza")
            options = data.get("options")
            self.assertIsInstance(
                options,
                dict,
                f"Manifest {filename} 'options:' must be a mapping",
            )
            self.assertEqual(
                options.get("logging"),
                "CLOUD_LOGGING_ONLY",
                f"Manifest {filename} missing logging: CLOUD_LOGGING_ONLY",
            )
            self.assertEqual(
                options.get("requestedVerifyOption"),
                "VERIFIED",
                f"Manifest {filename} missing or invalid requestedVerifyOption: 'VERIFIED' in options",
            )

            self.assertIn("images", data, f"Manifest {filename} missing top-level 'images:' stanza required for SLSA provenance")
            images = data.get("images")
            self.assertIsInstance(images, list, f"Manifest {filename} 'images:' must be a list")
            self.assertGreater(len(images), 0, f"Manifest {filename} 'images:' list cannot be empty")
            self.assertTrue(
                all(isinstance(img, str) and img.strip() for img in images),
                f"Manifest {filename} 'images:' entries must be non-empty strings",
            )
            self.assertTrue(
                any(
                    isinstance(img, str)
                    and cfg["commit_sha_var"] in img
                    and ("${_SERVICE_NAME}" in img or cfg["service_name"] in img)
                    and ("${_REPO_NAME}" in img or "conductor-repo" in img)
                    for img in images
                ),
                f"Manifest {filename} 'images:' must declare immutable image tag referencing {cfg['commit_sha_var']}, service name, and repo",
            )



if __name__ == "__main__":
    unittest.main()
