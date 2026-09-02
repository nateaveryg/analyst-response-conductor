#!/usr/bin/env python3
"""
Empirical Mutation Testing and Adversarial Stress Test Suite for Cloud Build SBOM Conformance.
Implements the Solution Stress Testing methodology (SKILL.md) to stress-test the conformance
test suite (tests/test_cloudbuild_sbom_conformance.py) against synthesized counterexamples,
corrupted manifests, edge-case mutations, and out-of-order execution pipelines.

Validates that tests/test_cloudbuild_sbom_conformance.py achieves a 100% mutant kill rate
across:
1. Category 1: Missing or altered Syft image tag (anchore/syft:v1.18.1 vs wrong version/image)
2. Category 2: Wrong output format or filename (missing spdx-json, cyclonedx, wrong file)
3. Category 3: Missing gcloud artifacts sbom load command or wrong arguments (--source, --uri)
4. Category 4: Incorrect GCS bucket path or missing artifacts.objects stanza
5. Category 5: Out-of-order steps (Syft before build, upload before Syft, release before upload)
6. Category 6: Corrupted substitutions or removed options (logging: CLOUD_LOGGING_ONLY)
7. Category 7: Malformed YAML syntax and structural corruption
"""

import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import yaml

import tests.test_cloudbuild_sbom_conformance as tc

ORIGINAL_TEST_ROOT = tc.TEST_ROOT
TARGET_CONFIGS = tc.TARGET_CONFIGS


def run_conformance_test_method(method_name: str, tmp_root: Path):
    """
    Executes a specific test method in TestCloudBuildSbomConformance
    pointing to a mutated root directory.
    """
    tc.TEST_ROOT = tmp_root
    try:
        suite_instance = tc.TestCloudBuildSbomConformance()
        getattr(suite_instance, method_name)()
    finally:
        tc.TEST_ROOT = ORIGINAL_TEST_ROOT


def run_all_conformance_tests(tmp_root: Path):
    """
    Executes all 6 tests in TestCloudBuildSbomConformance pointing to a mutated root.
    Returns (killed: bool, killer_test: str, error_message: str).
    """
    test_methods = [
        "test_01_all_target_manifest_files_exist_and_parse",
        "test_02_syft_sbom_generation_step_conformance",
        "test_03_artifact_analysis_upload_step_conformance",
        "test_04_gcs_artifact_archival_conformance",
        "test_05_step_ordering_and_pipeline_integrity",
        "test_06_substitutions_and_options_integrity",
    ]
    tc.TEST_ROOT = tmp_root
    try:
        suite_instance = tc.TestCloudBuildSbomConformance()
        for method in test_methods:
            try:
                getattr(suite_instance, method)()
            except (AssertionError, Exception) as exc:
                return True, method, str(exc)
        return False, None, "Mutant survived all tests!"
    finally:
        tc.TEST_ROOT = ORIGINAL_TEST_ROOT


def create_clean_sandbox() -> tuple[tempfile.TemporaryDirectory, Path]:
    """Creates a temporary sandbox containing pristine copies of all 3 target manifests."""
    tmpdir = tempfile.TemporaryDirectory()
    sandbox_path = Path(tmpdir.name)
    for cfg in TARGET_CONFIGS:
        shutil.copy(ORIGINAL_TEST_ROOT / cfg["filename"], sandbox_path / cfg["filename"])
    return tmpdir, sandbox_path


def load_manifest(sandbox_path: Path, filename: str) -> dict:
    with open(sandbox_path / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_manifest(sandbox_path: Path, filename: str, data: dict):
    with open(sandbox_path / filename, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


class TestSbomMutationFuzzer(unittest.TestCase):
    """
    Systematic mutation harness verifying that tests/test_cloudbuild_sbom_conformance.py
    detects all corrupted and out-of-spec manifest configurations.
    """

    def test_00_baseline_pristine_manifests_pass(self):
        """Validates that pristine unmodified manifests pass all conformance tests."""
        tmpdir, sandbox = create_clean_sandbox()
        try:
            killed, killer, msg = run_all_conformance_tests(sandbox)
            self.assertFalse(killed, f"Baseline should not fail any tests, failed on {killer}: {msg}")
        finally:
            tmpdir.cleanup()

    def test_category_1_syft_image_tag_mutants(self):
        """
        Synthesizes counterexamples for Syft image tag tampering:
        1. Missing Syft step
        2. Older version tag: anchore/syft:v1.17.0
        3. Floating tag: anchore/syft:latest
        4. Wrong tool: aquasec/trivy:latest
        5. Duplicate Syft step
        """
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]

            # Mutant 1.1: Missing Syft step entirely
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["steps"] = [s for s in data["steps"] if not s.get("name", "").startswith("anchore/syft")]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing Syft step in {filename}")
                self.assertIn(killer, ["test_02_syft_sbom_generation_step_conformance", "test_05_step_ordering_and_pipeline_integrity"])
            finally:
                tmpdir.cleanup()

            # Mutant 1.2: Outdated tag anchore/syft:v1.17.0
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["name"] = "anchore/syft:v1.17.0"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill outdated Syft tag v1.17.0 in {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 1.3: Unpinned tag anchore/syft:latest
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["name"] = "anchore/syft:latest"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill unpinned Syft latest in {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 1.4: Altered scanner aquasec/trivy:latest
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["name"] = "aquasec/trivy:latest"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill trivy scanner mutant in {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 1.5: Duplicate Syft step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                syft_step = next(s for s in data["steps"] if s.get("name", "").startswith("anchore/syft"))
                data["steps"].append(copy.deepcopy(syft_step))
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill duplicate Syft step in {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

    def test_category_2_output_format_and_target_mutants(self):
        """
        Synthesizes counterexamples for output format and filename tampering:
        1. Format altered to cyclonedx-json
        2. Format altered to table
        3. Wrong output filename sbom.json
        4. Target image missing commit SHA variable
        5. Target image missing service name
        """
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]

            # Mutant 2.1: CycloneDX format
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["args"] = [a.replace("spdx-json=", "cyclonedx-json=") for a in s.get("args", [])]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill cyclonedx format mutant in {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 2.2: Table format (missing spdx-json)
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["args"] = ["scan", "some-image", "-o", "table"]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill table format mutant in {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 2.3: Wrong filename sbom.json
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["args"] = [a.replace("sbom.spdx.json", "sbom.json") for a in s.get("args", [])]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill wrong filename mutant in {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 2.4: Target image missing commit SHA variable
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                sha_var = cfg["commit_sha_var"]
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["args"] = [a.replace(sha_var, "latest") for a in s.get("args", [])]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing commit SHA in Syft target for {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 2.5: Target image missing service name
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name", "").startswith("anchore/syft"):
                        s["args"] = [
                            a.replace("${_SERVICE_NAME}", "unrelated-app").replace(cfg["service_name"], "unrelated-app")
                            for a in s.get("args", [])
                        ]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing service name in Syft target for {filename}")
                self.assertEqual(killer, "test_02_syft_sbom_generation_step_conformance")
            finally:
                tmpdir.cleanup()

    def test_category_3_artifact_analysis_upload_step_mutants(self):
        """
        Synthesizes counterexamples for Artifact Analysis upload step tampering:
        1. Missing upload step
        2. Wrong container image (google/cloud-sdk:latest)
        3. Wrong command (artifacts sbom export instead of load)
        4. Missing load argument
        5. Wrong --source flag (--source=other.json)
        6. Missing --source flag entirely
        7. Missing --uri flag entirely
        8. Target --uri missing commit SHA variable
        9. Duplicate upload step
        """
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]

            # Mutant 3.1: Missing upload step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["steps"] = [
                    s for s in data["steps"]
                    if not (s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", []))
                ]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing upload step in {filename}")
                self.assertIn(killer, ["test_03_artifact_analysis_upload_step_conformance", "test_05_step_ordering_and_pipeline_integrity"])
            finally:
                tmpdir.cleanup()

            # Mutant 3.2: Wrong container image
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", []):
                        s["name"] = "google/cloud-sdk:latest"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill wrong cloud-sdk container image in {filename}")
                self.assertEqual(killer, "test_03_artifact_analysis_upload_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 3.3: Wrong command (export instead of load)
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", []):
                        s["args"] = [a if a != "load" else "export" for a in s.get("args", [])]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill export vs load command mutant in {filename}")
                self.assertEqual(killer, "test_03_artifact_analysis_upload_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 3.4: Wrong --source=other.json
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", []):
                        s["args"] = [a.replace("sbom.spdx.json", "other.json") for a in s.get("args", [])]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill wrong --source mutant in {filename}")
                self.assertEqual(killer, "test_03_artifact_analysis_upload_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 3.5: Missing --source argument entirely
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", []):
                        s["args"] = [a for a in s.get("args", []) if not a.startswith("--source")]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing --source argument in {filename}")
                self.assertEqual(killer, "test_03_artifact_analysis_upload_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 3.6: Missing --uri argument entirely
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                for s in data["steps"]:
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", []):
                        s["args"] = [a for a in s.get("args", []) if not a.startswith("--uri")]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing --uri argument in {filename}")
                self.assertEqual(killer, "test_03_artifact_analysis_upload_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 3.7: Target --uri missing commit SHA variable
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                sha_var = cfg["commit_sha_var"]
                for s in data["steps"]:
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", []):
                        s["args"] = [a.replace(sha_var, "unpinned") for a in s.get("args", [])]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing commit SHA in upload --uri for {filename}")
                self.assertEqual(killer, "test_03_artifact_analysis_upload_step_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 3.8: Duplicate upload step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                up_step = next(
                    s for s in data["steps"]
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", [])
                )
                data["steps"].append(copy.deepcopy(up_step))
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill duplicate upload step in {filename}")
                self.assertEqual(killer, "test_03_artifact_analysis_upload_step_conformance")
            finally:
                tmpdir.cleanup()

    def test_category_4_gcs_artifact_archival_mutants(self):
        """
        Synthesizes counterexamples for GCS artifact archival tampering:
        1. Missing artifacts: top-level stanza
        2. Missing objects: under artifacts:
        3. Wrong GCS bucket path (gs://wrong-bucket/...)
        4. Missing ${BUILD_ID} in path
        5. Wrong path (paths: ['other.json'])
        6. Empty paths list (paths: [])
        7. Null artifacts: stanza
        8. Null objects: stanza under artifacts
        """
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]

            # Mutant 4.1: Missing artifacts stanza
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data.pop("artifacts", None)
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing artifacts stanza in {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 4.2: Missing objects under artifacts
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["artifacts"] = {"images": ["some-image"]}
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing objects key in {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 4.3: Wrong GCS bucket path
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["artifacts"]["objects"]["location"] = "gs://wrong-bucket/sboms/${BUILD_ID}"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill wrong GCS bucket path in {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 4.4: Missing ${BUILD_ID} in location
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["artifacts"]["objects"]["location"] = "gs://${PROJECT_ID}_cloudbuild/sboms/latest"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing ${{BUILD_ID}} in {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 4.5: Wrong path in paths list
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["artifacts"]["objects"]["paths"] = ["wrong-output.json"]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing sbom.spdx.json in paths for {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 4.6: Empty paths list
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["artifacts"]["objects"]["paths"] = []
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill empty paths list in {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 4.7: Null artifacts stanza
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["artifacts"] = None
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null artifacts stanza in {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

            # Mutant 4.8: Null objects stanza under artifacts
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["artifacts"]["objects"] = None
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null objects under artifacts in {filename}")
                self.assertEqual(killer, "test_04_gcs_artifact_archival_conformance")
            finally:
                tmpdir.cleanup()

    def test_category_5_step_ordering_and_integrity_mutants(self):
        """
        Synthesizes counterexamples for pipeline step ordering and non-regression:
        1. Out-of-order: Syft step placed BEFORE container build step
        2. Out-of-order: Upload step placed BEFORE Syft step
        3. Out-of-order: Release creation step placed BEFORE upload step
        4. Removed existing required build step
        5. Removed existing release step
        """
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]

            # Mutant 5.1: Syft step before container build step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                steps = data["steps"]
                syft_idx = next(i for i, s in enumerate(steps) if s.get("name", "").startswith("anchore/syft"))
                syft_step = steps.pop(syft_idx)
                steps.insert(0, syft_step)  # Place at index 0 (before build)
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill Syft-before-build mutant in {filename}")
                self.assertEqual(killer, "test_05_step_ordering_and_pipeline_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 5.2: Upload step before Syft step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                steps = data["steps"]
                syft_idx = next(i for i, s in enumerate(steps) if s.get("name", "").startswith("anchore/syft"))
                up_idx = next(
                    i for i, s in enumerate(steps)
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", [])
                )
                # Swap Syft and Upload steps
                steps[syft_idx], steps[up_idx] = steps[up_idx], steps[syft_idx]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill Upload-before-Syft mutant in {filename}")
                self.assertEqual(killer, "test_05_step_ordering_and_pipeline_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 5.3: Release step before Upload step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                steps = data["steps"]
                up_idx = next(
                    i for i, s in enumerate(steps)
                    if s.get("name") == "gcr.io/google.com/cloudsdktool/cloud-sdk:slim" and "sbom" in s.get("args", [])
                )
                rel_idx = next(i for i, s in enumerate(steps) if s.get("id") == "create-cloud-deploy-release")
                # Swap Release and Upload steps
                steps[up_idx], steps[rel_idx] = steps[rel_idx], steps[up_idx]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill Release-before-Upload mutant in {filename}")
                self.assertEqual(killer, "test_05_step_ordering_and_pipeline_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 5.4: Removed required existing build step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["steps"] = [s for s in data["steps"] if s.get("id") != cfg["build_step_id"]]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill removed build step in {filename}")
                self.assertEqual(killer, "test_05_step_ordering_and_pipeline_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 5.5: Removed required existing release step
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["steps"] = [s for s in data["steps"] if s.get("id") != "create-cloud-deploy-release"]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill removed release step in {filename}")
                self.assertEqual(killer, "test_05_step_ordering_and_pipeline_integrity")
            finally:
                tmpdir.cleanup()

    def test_category_6_substitutions_and_options_mutants(self):
        """
        Synthesizes counterexamples for substitutions and options tampering:
        1. Altered _REGION (europe-west1)
        2. Missing _REGION
        3. Altered _REPO_NAME
        4. Altered _SERVICE_NAME
        5. Altered _DELIVERY_PIPELINE_NAME
        6. Altered logging option (LEGACY)
        7. Missing logging option
        8. Missing options stanza entirely
        9. Missing requestedVerifyOption
        10. Altered requestedVerifyOption (NOT_VERIFIED)
        11. Null options stanza
        12. Lowercase requestedVerifyOption (verified)
        13. Null substitutions stanza
        14. Missing images stanza
        15. Null images stanza
        16. Empty images list
        17. Altered images missing commit SHA tag
        18. Images list containing null element
        19. Images list containing non-string integer
        20. Images tag with commit SHA but unrelated service name
        21. Null requestedVerifyOption value
        22. Unverified enum requestedVerifyOption: VERIFY_UNSPECIFIED
        """
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]

            # Mutant 6.1: Altered _REGION
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["substitutions"]["_REGION"] = "europe-west1"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill altered _REGION in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.2: Missing _REGION
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["substitutions"].pop("_REGION", None)
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing _REGION in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.3: Altered _REPO_NAME
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["substitutions"]["_REPO_NAME"] = "tampered-repo"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill altered _REPO_NAME in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.4: Altered _SERVICE_NAME
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["substitutions"]["_SERVICE_NAME"] = "wrong-service"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill altered _SERVICE_NAME in {filename}")
                self.assertIn(killer, ["test_02_syft_sbom_generation_step_conformance", "test_03_artifact_analysis_upload_step_conformance", "test_06_substitutions_and_options_integrity"])
            finally:
                tmpdir.cleanup()

            # Mutant 6.5: Altered _DELIVERY_PIPELINE_NAME
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["substitutions"]["_DELIVERY_PIPELINE_NAME"] = "wrong-pipeline"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill altered _DELIVERY_PIPELINE_NAME in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.6: Altered logging option (LEGACY)
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"]["logging"] = "LEGACY"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill altered logging option in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.7: Missing logging option
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"].pop("logging", None)
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing logging option in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.8: Missing options stanza entirely
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data.pop("options", None)
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing options stanza in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.9: Missing requestedVerifyOption
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"].pop("requestedVerifyOption", None)
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing requestedVerifyOption in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.10: Altered requestedVerifyOption
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"]["requestedVerifyOption"] = "NOT_VERIFIED"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill altered requestedVerifyOption in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.11: Null options stanza
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"] = None
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null options stanza in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.12: Lowercase requestedVerifyOption
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"]["requestedVerifyOption"] = "verified"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill lowercase requestedVerifyOption in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.13: Null substitutions stanza
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["substitutions"] = None
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null substitutions stanza in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.14: Missing images stanza (critical for SLSA Level 3 provenance)
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data.pop("images", None)
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing images stanza in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.15: Null images stanza
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["images"] = None
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null images stanza in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.16: Empty images list
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["images"] = []
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill empty images list in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.17: Altered images missing commit SHA tag
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["images"] = ["us-central1-docker.pkg.dev/proj/repo/image:latest"]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill altered images without commit SHA tag in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.18: Images list containing null element
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["images"] = [None]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null element in images in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.19: Images list containing non-string integer
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["images"] = [12345]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill integer element in images in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.20: Images tag with commit SHA but unrelated service name
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["images"] = [f"us-central1-docker.pkg.dev/riccardo-blog-test-v1/conductor-repo/unrelated-service:{cfg['commit_sha_var']}"]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill images tag with unrelated service name in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.21: Null requestedVerifyOption value
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"]["requestedVerifyOption"] = None
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null requestedVerifyOption in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

            # Mutant 6.22: Unverified enum requestedVerifyOption: VERIFY_UNSPECIFIED
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["options"]["requestedVerifyOption"] = "VERIFY_UNSPECIFIED"
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill VERIFY_UNSPECIFIED in {filename}")
                self.assertEqual(killer, "test_06_substitutions_and_options_integrity")
            finally:
                tmpdir.cleanup()

    def test_category_7_manifest_syntax_and_structure_mutants(self):
        """
        Synthesizes counterexamples for syntax and top-level schema errors:
        1. Corrupted/unparseable YAML syntax
        2. Empty steps list
        3. Missing manifest file
        4. Zero-byte empty manifest file
        5. Multi-document YAML manifest
        6. Steps list containing null element
        """
        for cfg in TARGET_CONFIGS:
            filename = cfg["filename"]

            # Mutant 7.1: Corrupted YAML
            tmpdir, sandbox = create_clean_sandbox()
            try:
                with open(sandbox / filename, "w", encoding="utf-8") as f:
                    f.write("steps: [ unclosed bracket\n  - name: test\n")
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill corrupted YAML in {filename}")
                self.assertEqual(killer, "test_01_all_target_manifest_files_exist_and_parse")
            finally:
                tmpdir.cleanup()

            # Mutant 7.2: Empty steps list
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["steps"] = []
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill empty steps list in {filename}")
                self.assertEqual(killer, "test_01_all_target_manifest_files_exist_and_parse")
            finally:
                tmpdir.cleanup()

            # Mutant 7.3: Missing manifest file
            tmpdir, sandbox = create_clean_sandbox()
            try:
                (sandbox / filename).unlink()
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill missing file in {filename}")
                self.assertEqual(killer, "test_01_all_target_manifest_files_exist_and_parse")
            finally:
                tmpdir.cleanup()

            # Mutant 7.4: Zero-byte empty manifest file
            tmpdir, sandbox = create_clean_sandbox()
            try:
                with open(sandbox / filename, "w", encoding="utf-8") as f:
                    pass
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill zero-byte file in {filename}")
                self.assertEqual(killer, "test_01_all_target_manifest_files_exist_and_parse")
            finally:
                tmpdir.cleanup()

            # Mutant 7.5: Multi-document YAML manifest
            tmpdir, sandbox = create_clean_sandbox()
            try:
                with open(sandbox / filename, "w", encoding="utf-8") as f:
                    f.write("steps:\n  - name: test1\n---\nsteps:\n  - name: test2\n")
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill multi-document YAML in {filename}")
                self.assertEqual(killer, "test_01_all_target_manifest_files_exist_and_parse")
            finally:
                tmpdir.cleanup()

            # Mutant 7.6: Steps list containing null element
            tmpdir, sandbox = create_clean_sandbox()
            try:
                data = load_manifest(sandbox, filename)
                data["steps"] = [None]
                save_manifest(sandbox, filename, data)
                killed, killer, msg = run_all_conformance_tests(sandbox)
                self.assertTrue(killed, f"Failed to kill null element in steps in {filename}")
                self.assertEqual(killer, "test_01_all_target_manifest_files_exist_and_parse")
            finally:
                tmpdir.cleanup()



if __name__ == "__main__":
    unittest.main()
