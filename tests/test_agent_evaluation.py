"""Automated Verification Test Suite for Conductor v3 Production Agent Evaluation.

Validates:
1. Golden dataset schema integrity, format, and semantic completeness.
2. Metric scoring math, threshold comparison logic, and exit code enforcement.
3. YAML schema validity for Cloud Deploy verify manifests and Skaffold custom actions.
4. Clean isolation from the primary repository (rficonductorv2).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_production_agent import (
    DEFAULT_AGENT_ENGINE_ID,
    compute_groundedness_score,
    compute_hallucination_rate,
    compute_tool_call_accuracy,
    normalize_text,
    query_agent_engine,
    run_evaluation,
)

DATASET_PATH = PROJECT_ROOT / "data" / "golden_eval_dataset.json"
CLOUDDEPLOY_MANIFEST_PATH = PROJECT_ROOT / "infra" / "clouddeploy" / "verify-agent-eval.yaml"
SKAFFOLD_MANIFEST_PATH = PROJECT_ROOT / "infra" / "clouddeploy" / "skaffold-agent-eval.yaml"
ADR_PATH = PROJECT_ROOT / "docs" / "adr" / "ADR-20260903-08-production-canary-agent-evaluation.md"
REFERENCE_REPO_PATH = Path(os.environ.get("REPO_ROOT", str(PROJECT_ROOT)))


# =====================================================================
# 1. Golden Dataset Schema & Completeness Tests
# =====================================================================
class TestGoldenDatasetSchemaAndCompleteness:
    """Validates the golden evaluation dataset schema, integrity, and depth."""

    def test_dataset_file_exists_and_parses_json(self):
        """Verifies dataset file exists and is valid JSON."""
        assert DATASET_PATH.exists(), f"Dataset file missing at {DATASET_PATH}"
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_dataset_top_level_metadata(self):
        """Verifies required top-level metadata fields."""
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "version" in data
        assert "dataset_name" in data
        assert "description" in data
        assert "target_agent_engine_id" in data
        assert data["target_agent_engine_id"] == DEFAULT_AGENT_ENGINE_ID
        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)

    def test_dataset_minimum_ten_scenarios(self):
        """Requirement R2: Must contain at least 10 realistic enterprise scenarios."""
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        scenarios = data.get("scenarios", [])
        assert len(scenarios) >= 10, f"Expected at least 10 scenarios, found {len(scenarios)}"

    def test_scenario_required_fields_and_types(self):
        """Verifies schema consistency across every scenario entry."""
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = {
            "scenario_id": str,
            "name": str,
            "category": str,
            "prompt": str,
            "reference_context": str,
            "expected_tool_calls": list,
            "expected_response_substrings": list,
            "forbidden_hallucinations": list,
            "mock_response": dict,
        }

        seen_ids = set()
        categories = set()

        for idx, sc in enumerate(data["scenarios"]):
            for key, expected_type in required_keys.items():
                assert key in sc, f"Scenario #{idx} missing required key '{key}'"
                assert isinstance(
                    sc[key], expected_type
                ), f"Scenario #{idx} key '{key}' expected {expected_type}, got {type(sc[key])}"

            # Validate ID uniqueness and format
            s_id = sc["scenario_id"]
            assert s_id not in seen_ids, f"Duplicate scenario ID found: {s_id}"
            assert s_id.startswith("SCENARIO-"), f"Invalid ID format: {s_id}"
            seen_ids.add(s_id)

            # Validate semantic non-emptiness
            assert len(sc["prompt"].strip()) > 15, f"Prompt too short in {s_id}"
            assert len(sc["reference_context"].strip()) > 30, f"Reference context too short in {s_id}"
            assert len(sc["expected_response_substrings"]) > 0, f"Empty expected substrings in {s_id}"
            assert len(sc["forbidden_hallucinations"]) > 0, f"Empty forbidden hallucinations in {s_id}"

            # Validate mock response schema
            mock = sc["mock_response"]
            assert "content" in mock and isinstance(mock["content"], str)
            assert len(mock["content"].strip()) > 20, f"Empty mock content in {s_id}"
            assert "tool_calls" in mock and isinstance(mock["tool_calls"], list)

            # Validate tool call schemas
            for tc in sc["expected_tool_calls"]:
                assert "tool_name" in tc and isinstance(tc["tool_name"], str)
                assert "parameters" in tc and isinstance(tc["parameters"], dict)

            for tc in mock["tool_calls"]:
                assert "tool_name" in tc and isinstance(tc["tool_name"], str)
                assert "parameters" in tc and isinstance(tc["parameters"], dict)

            categories.add(sc["category"])

        # Validate category coverage across enterprise domains
        expected_categories = {"CNAPP", "DEVSECOPS", "ENTERPRISE_AI", "DLP_GOVERNANCE"}
        assert expected_categories.issubset(categories), f"Missing categories: {expected_categories - categories}"


# =====================================================================
# 2. Metric Scoring Math & Logic Tests
# =====================================================================
class TestMetricScoringMathAndLogic:
    """Validates quantitative metric formulas, boundary conditions, and edge cases."""

    def test_text_normalization(self):
        """Verifies punctuation removal, case lowering, and whitespace collapsing."""
        raw = "  Hello,   WORLD!  This is /a/ test-case... "
        normalized = normalize_text(raw)
        assert normalized == "hello world this is /a/ test-case"

    def test_groundedness_perfect_alignment(self):
        """Verifies groundedness score is high for fully aligned responses."""
        ref = "Production cluster clusters/prod-us-central1 detected CVE-2026-2149 in containerd."
        resp = "Production cluster clusters/prod-us-central1 detected CVE-2026-2149 in containerd."
        substrings = ["CVE-2026-2149", "containerd", "clusters/prod-us-central1"]
        score = compute_groundedness_score(resp, ref, substrings)
        assert score >= 0.90
        assert score <= 1.0

    def test_groundedness_empty_input(self):
        """Verifies groundedness returns 0.0 on empty or whitespace responses, and handles non-strings."""
        assert compute_groundedness_score("", "some reference") == 0.0
        assert compute_groundedness_score("   ", "some reference") == 0.0
        assert compute_groundedness_score(None, "some reference") == 0.0
        assert compute_groundedness_score("valid response", None) == 0.0
        assert compute_groundedness_score(123, "some reference") >= 0.0
        assert compute_groundedness_score("valid response", 456) >= 0.0

    def test_groundedness_unsupported_content(self):
        """Verifies low groundedness score when response contains irrelevant claims."""
        ref = "Cloud SQL genai-rag-db uses pgvector with HNSW cosine index."
        resp = "The weather in Seattle is sunny and 72 degrees with light winds."
        substrings = ["pgvector", "HNSW"]
        score = compute_groundedness_score(resp, ref, substrings)
        assert score < 0.20

    def test_hallucination_rate_clean_response(self):
        """Verifies zero hallucination rate for completely grounded responses."""
        ref = "Service conductor-v3-prod uses minScale 1 and maxScale 20 on Cloud Run."
        resp = "Service conductor-v3-prod uses minScale 1 and maxScale 20 on Cloud Run."
        forbidden = ["maxScale 100", "GKE DaemonSet"]
        rate = compute_hallucination_rate(resp, ref, forbidden)
        assert rate == 0.0

    def test_hallucination_rate_forbidden_detection(self):
        """Verifies high hallucination rate when forbidden claims are detected."""
        ref = "Model Armor masks SSN to [REDACTED_SSN]."
        resp = "The customer SSN is 000-12-3456 and rate is 45%."
        forbidden = ["000-12-3456", "45%"]
        rate = compute_hallucination_rate(resp, ref, forbidden)
        assert rate >= 0.20

    def test_hallucination_rate_fabricated_identifier(self):
        """Verifies hallucination detection on fabricated entity identifiers."""
        ref = "Cluster prod-cluster has vulnerability CVE-2026-1111."
        resp = "Cluster prod-cluster has vulnerability CVE-2099-9999."
        rate = compute_hallucination_rate(resp, ref, ["arbitrary-forbidden"])
        assert rate > 0.0

    def test_tool_call_accuracy_exact_match(self):
        """Verifies 1.0 accuracy when expected and actual tool calls match perfectly."""
        expected = [
            {
                "tool_name": "scan_cluster_vulnerabilities",
                "parameters": {"cluster_id": "prod-1", "severity": "CRITICAL"},
            }
        ]
        actual = [
            {
                "tool_name": "scan_cluster_vulnerabilities",
                "parameters": {"cluster_id": "prod-1", "severity": "CRITICAL"},
            }
        ]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 1.0

    def test_tool_call_accuracy_both_empty(self):
        """Verifies 1.0 accuracy when no tool calls are expected and none made."""
        assert compute_tool_call_accuracy([], []) == 1.0

    def test_tool_call_accuracy_missing_call(self):
        """Verifies 0.0 accuracy when expected tool call is not made."""
        expected = [{"tool_name": "get_delivery_pipeline", "parameters": {"region": "us-central1"}}]
        actual = []
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 0.0

    def test_tool_call_accuracy_parameter_mismatch(self):
        """Verifies partial credit when tool name matches but parameters differ."""
        expected = [{"tool_name": "inspect_kms_key", "parameters": {"key": "primary", "ver": "4"}}]
        actual = [{"tool_name": "inspect_kms_key", "parameters": {"key": "secondary", "ver": "1"}}]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 0.50

    def test_tool_call_accuracy_extraneous_call_penalty(self):
        """Verifies penalty applied for unexpected extraneous tool invocations."""
        expected = [{"tool_name": "inspect_kms_key", "parameters": {}}]
        actual = [
            {"tool_name": "inspect_kms_key", "parameters": {}},
            {"tool_name": "delete_database", "parameters": {}},
        ]
        score = compute_tool_call_accuracy(actual, expected)
        assert score < 1.0

    def test_groundedness_unrelated_with_no_substrings(self):
        """Verifies groundedness is 0.0 when text is unrelated and no expected substrings given."""
        ref = "Cloud SQL genai-rag-db uses pgvector with HNSW cosine index."
        resp = "The weather in Seattle is sunny and 72 degrees with light winds."
        score = compute_groundedness_score(resp, ref, expected_substrings=None)
        assert score == 0.0

    def test_groundedness_empty_reference(self):
        """Verifies groundedness is 0.0 when reference context is empty."""
        assert compute_groundedness_score("Valid response text", "") == 0.0
        assert compute_groundedness_score("Valid response text", "   ") == 0.0

    def test_hallucination_rate_empty_reference(self):
        """Verifies hallucination rate is 1.0 when reference context is empty, and handles non-strings."""
        assert compute_hallucination_rate("Some ungrounded response", "") == 1.0
        assert compute_hallucination_rate("Some ungrounded response", "   ") == 1.0
        assert compute_hallucination_rate("Some ungrounded response", None) == 1.0
        assert compute_hallucination_rate(None, "some reference") == 0.0
        assert compute_hallucination_rate(123, "some reference") >= 0.0
        assert compute_hallucination_rate("Some ungrounded response", 456) >= 0.0

    def test_tool_call_accuracy_duplicate_call_matching(self):
        """Verifies 1-to-1 matching: 1 actual call cannot satisfy 2 expected calls."""
        expected = [
            {"tool_name": "scan_cluster", "parameters": {"cluster_id": "prod-1"}},
            {"tool_name": "scan_cluster", "parameters": {"cluster_id": "prod-1"}},
        ]
        actual = [
            {"tool_name": "scan_cluster", "parameters": {"cluster_id": "prod-1"}},
        ]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 0.50

    def test_tool_call_accuracy_malformed_entries(self):
        """Verifies malformed tool call items do not crash the scorer and are penalized."""
        expected = [{"tool_name": "scan_cluster", "parameters": {"id": "1"}}]
        actual = ["not_a_dict", {"tool_name": "scan_cluster", "parameters": None}]
        score = compute_tool_call_accuracy(actual, expected)
        assert 0.0 <= score <= 1.0

    def test_tool_call_accuracy_extraneous_parameters(self):
        """Verifies extraneous unexpected parameters penalize parameter matching."""
        expected = [{"tool_name": "scan_cluster", "parameters": {"id": "1"}}]
        actual_exact = [{"tool_name": "scan_cluster", "parameters": {"id": "1"}}]
        actual_extra = [{"tool_name": "scan_cluster", "parameters": {"id": "1", "hallucinated": "arg"}}]
        score_exact = compute_tool_call_accuracy(actual_exact, expected)
        score_extra = compute_tool_call_accuracy(actual_extra, expected)
        assert score_exact == 1.0
        assert score_extra < score_exact

    def test_hallucination_rate_completely_ungrounded_response(self):
        """Verifies hallucination rate is 1.0 when response is entirely ungrounded in context."""
        ref = "Cloud SQL genai-rag-db uses pgvector with HNSW cosine index."
        resp = "The weather in Seattle is sunny and 72 degrees with light winds."
        rate = compute_hallucination_rate(resp, ref, forbidden_hallucinations=[])
        assert rate == 1.0

    def test_tool_call_accuracy_nested_dict_and_case_insensitivity(self):
        """Verifies tool accuracy supports nested dict equality, case insensitivity, and types."""
        expected = [
            {
                "tool_name": "scan_cluster",
                "parameters": {
                    "config": {"a": 1, "b": 2},
                    "severity": "CRITICAL",
                    "retries": 3,
                },
            }
        ]
        actual = [
            {
                "tool_name": "scan_cluster",
                "parameters": {
                    "config": {"b": 2, "a": 1},
                    "severity": "critical",
                    "retries": "3",
                },
            }
        ]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 1.0

    def test_groundedness_relative_resource_name_substring(self):
        """Verifies relative resource names contained in reference URI receive grounding credit."""
        ref = "Production cluster projects/riccardo-blog-test-v1/locations/us-central1/clusters/prod-us-central1 was scanned."
        resp = "Production cluster clusters/prod-us-central1 was scanned."
        score = compute_groundedness_score(resp, ref)
        assert score >= 0.90

    def test_tool_call_accuracy_non_dict_parameter_handling(self):
        """Verifies non-dict actual parameter values do not raise TypeError and are handled safely."""
        expected = [{"tool_name": "scan_cluster", "parameters": {"cluster_id": "c1", "s": "val"}}]
        actual = [{"tool_name": "scan_cluster", "parameters": "some_string_param"}]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 0.50

    def test_hallucination_rate_empty_and_whitespace_forbidden_entries(self):
        """Verifies empty or whitespace strings in forbidden hallucinations list do not trigger false positives."""
        ref = "Cluster prod-cluster has vulnerability CVE-2026-1111."
        resp = "Cluster prod-cluster has vulnerability CVE-2026-1111."
        forbidden = ["", "   ", None]
        rate = compute_hallucination_rate(resp, ref, forbidden)
        assert rate == 0.0

    def test_tool_call_accuracy_recursive_nested_dict_and_list_matching(self):
        """Verifies recursive parameter matching on nested dicts with key permutation and list elements."""
        expected = [
            {
                "tool_name": "configure_policy",
                "parameters": {
                    "rule": {"priority": 1, "action": "ALLOW"},
                    "tags": ["PROD", "SECURE"],
                },
            }
        ]
        actual = [
            {
                "tool_name": "configure_policy",
                "parameters": {
                    "rule": {"action": "allow", "priority": "1.0"},
                    "tags": ["secure", "prod"],
                },
            }
        ]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 1.0

    def test_tool_call_accuracy_case_insensitive_tool_names(self):
        """Verifies tool names are matched case-insensitively."""
        expected = [{"tool_name": "scan_cluster_vulnerabilities", "parameters": {"cluster_id": "c1"}}]
        actual = [{"tool_name": "SCAN_CLUSTER_VULNERABILITIES", "parameters": {"cluster_id": "c1"}}]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 1.0

    def test_tool_call_accuracy_numeric_equivalence(self):
        """Verifies numeric string and float/int equivalence in parameter values."""
        expected = [{"tool_name": "set_threshold", "parameters": {"threshold": 0.80, "count": 10}}]
        actual = [{"tool_name": "set_threshold", "parameters": {"threshold": "0.8", "count": 10.0}}]
        score = compute_tool_call_accuracy(actual, expected)
        assert score == 1.0

    def test_groundedness_string_and_scalar_substrings(self):
        """Verifies groundedness gracefully handles single string, scalar, and None expected_substrings."""
        ref = "Production cluster clusters/prod-us-central1 detected CVE-2026-2149 in containerd."
        resp = "Production cluster clusters/prod-us-central1 detected CVE-2026-2149 in containerd."
        assert compute_groundedness_score(resp, ref, "CVE-2026-2149") == 1.0
        assert compute_groundedness_score(resp, ref, 12345) == 1.0
        assert compute_groundedness_score(resp, ref, None) == 1.0

    def test_hallucination_rate_string_and_scalar_forbidden(self):
        """Verifies hallucination rate gracefully handles single string, scalar, and None forbidden."""
        ref = "Production cluster clusters/prod-us-central1 detected CVE-2026-2149 in containerd."
        resp = "Production cluster clusters/prod-us-central1 detected CVE-2026-2149 in containerd."
        assert compute_hallucination_rate(resp, ref, "arbitrary_clean_string") == 0.0
        assert compute_hallucination_rate(resp, ref, "CVE-2026-2149") == 1.0
        assert compute_hallucination_rate(resp, ref, 12345) == 0.0
        assert compute_hallucination_rate(resp, ref, None) == 0.0

    def test_tool_call_accuracy_kebab_case_and_json_string_params(self):
        """Verifies parameter matching supports kebab-case keys and JSON string parameters."""
        exp = [{"tool_name": "scan_cluster", "parameters": {"cluster_id": "c1", "meta": {"env": "prod"}}}]
        act = [{"tool_name": "scan_cluster", "parameters": {"cluster-id": "c1", "meta": "{\"env\": \"prod\"}"}}]
        assert compute_tool_call_accuracy(act, exp) == 1.0

    def test_tool_call_accuracy_none_tool_names_do_not_match(self):
        """Verifies tool calls with None or empty tool names do not match as valid tool invocations."""
        act = [{"tool_name": None}]
        exp = [{"tool_name": None}]
        assert compute_tool_call_accuracy(act, exp) == 0.0

    def test_tool_call_accuracy_nested_dict_kebab_case_keys(self):
        """Verifies recursive parameter matching normalizes kebab-case, snake_case, and camelCase in nested dicts."""
        expected = [{"tool_name": "configure", "parameters": {"settings": {"max_retries": 3, "pool_size": 10}}}]
        actual = [{"tool_name": "configure", "parameters": {"settings": {"max-retries": 3, "pool-size": 10}}}]
        assert compute_tool_call_accuracy(actual, expected) == 1.0

    def test_tool_call_accuracy_json_strings_different_key_order_and_whitespace(self):
        """Verifies two JSON-encoded string parameters match despite different key order and spacing."""
        expected = [{"tool_name": "configure", "parameters": {"meta": "{\"a\": 1, \"b\": 2}"}}]
        actual = [{"tool_name": "configure", "parameters": {"meta": "{\"b\": 2,  \"a\": 1}"}}]
        assert compute_tool_call_accuracy(actual, expected) == 1.0



# =====================================================================
# 3. Quality Gate Threshold & Execution Tests
# =====================================================================
class TestThresholdComparisonAndExecutionGates:
    """Validates full evaluation runner execution, quality gate checks, and exit codes."""

    def test_run_evaluation_passing_baseline(self, tmp_path):
        """Verifies standard evaluation against golden dataset passes with exit code 0 equivalent."""
        output_file = tmp_path / "scorecard_pass.json"
        passed, scorecard = run_evaluation(
            dataset_path=str(DATASET_PATH),
            output_path=str(output_file),
            mock_mode=True,
            min_groundedness=0.80,
            max_hallucination_rate=0.05,
            min_tool_call_accuracy=0.90,
        )

        assert passed is True
        assert output_file.exists()
        assert scorecard["summary"]["quality_gate_passed"] is True
        assert scorecard["summary"]["passed_scenarios"] == 12
        assert scorecard["summary"]["failed_scenarios"] == 0
        assert scorecard["summary"]["average_groundedness"] >= 0.80
        assert scorecard["summary"]["average_hallucination_rate"] <= 0.05
        assert scorecard["summary"]["average_tool_call_accuracy"] >= 0.90
        assert len(scorecard["violations"]) == 0

        # Verify string thresholds coercion in run_evaluation
        passed_str, _ = run_evaluation(
            dataset_path=str(DATASET_PATH),
            output_path=str(tmp_path / "scorecard_str.json"),
            mock_mode=True,
            min_groundedness="0.80",
            max_hallucination_rate="0.05",
            min_tool_call_accuracy="0.90",
        )
        assert passed_str is True

    def test_run_evaluation_failing_groundedness_threshold(self, tmp_path):
        """Verifies evaluation fails when groundedness threshold is set unrealistically high."""
        output_file = tmp_path / "scorecard_fail_g.json"
        passed, scorecard = run_evaluation(
            dataset_path=str(DATASET_PATH),
            output_path=str(output_file),
            mock_mode=True,
            min_groundedness=0.9999,  # Unrealistic threshold
            max_hallucination_rate=0.05,
            min_tool_call_accuracy=0.90,
        )

        assert passed is False
        assert scorecard["summary"]["quality_gate_passed"] is False
        assert len(scorecard["violations"]) > 0
        assert any("Groundedness" in v for v in scorecard["violations"])

    def test_run_evaluation_failing_hallucination_threshold(self, tmp_path):
        """Verifies evaluation fails when hallucination threshold is breached."""
        # Create small test dataset with intentional hallucination
        custom_data = {
            "version": "1.0",
            "scenarios": [
                {
                    "scenario_id": "SCENARIO-TEST-01",
                    "name": "Hallucination Test",
                    "category": "TEST",
                    "prompt": "Test prompt",
                    "reference_context": "Strict context A.",
                    "expected_tool_calls": [],
                    "expected_response_substrings": ["Strict context A"],
                    "forbidden_hallucinations": ["hallucinated_claim_xyz"],
                    "mock_response": {
                        "content": "This response contains hallucinated_claim_xyz definitely.",
                        "tool_calls": [],
                    },
                }
            ],
        }
        test_ds = tmp_path / "hallucination_test_dataset.json"
        with open(test_ds, "w", encoding="utf-8") as f:
            json.dump(custom_data, f)

        output_file = tmp_path / "scorecard_fail_h.json"
        passed, scorecard = run_evaluation(
            dataset_path=str(test_ds),
            output_path=str(output_file),
            mock_mode=True,
            min_groundedness=0.50,
            max_hallucination_rate=0.05,
            min_tool_call_accuracy=0.50,
        )

        assert passed is False
        assert scorecard["summary"]["quality_gate_passed"] is False
        assert any("Hallucination Rate" in v for v in scorecard["violations"])

    def test_cli_execution_success(self, tmp_path):
        """Verifies CLI execution with passing parameters terminates with exit code 0."""
        scorecard_path = tmp_path / "cli_scorecard_pass.json"
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "evaluate_production_agent.py"),
            "--dataset",
            str(DATASET_PATH),
            "--output",
            str(scorecard_path),
            "--min-groundedness",
            "0.80",
            "--max-hallucination-rate",
            "0.05",
            "--min-tool-call-accuracy",
            "0.90",
            "--mock",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        combined_output = result.stdout + result.stderr
        assert result.returncode == 0, f"CLI execution failed with stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert scorecard_path.exists()
        assert "[SUCCESS]" in combined_output

    def test_cli_execution_threshold_failure(self, tmp_path):
        """Verifies CLI execution with violated threshold terminates with non-zero exit code 1."""
        scorecard_path = tmp_path / "cli_scorecard_fail.json"
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "evaluate_production_agent.py"),
            "--dataset",
            str(DATASET_PATH),
            "--output",
            str(scorecard_path),
            "--min-groundedness",
            "0.9999",  # Trigger violation
            "--mock",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        combined_output = result.stdout + result.stderr
        assert result.returncode == 1, f"Expected returncode 1, got {result.returncode}"
        assert "[FAILURE]" in combined_output

    def test_cli_execution_missing_dataset_fatal_error(self, tmp_path):
        """Verifies CLI execution with non-existent dataset terminates with exit code 2."""
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "evaluate_production_agent.py"),
            "--dataset",
            str(tmp_path / "does_not_exist.json"),
            "--mock",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 2, f"Expected returncode 2, got {result.returncode}"

    def test_cli_threshold_overrides_via_env_vars(self, tmp_path):
        """Verifies environment variables THRESHOLD_* override default thresholds."""
        scorecard_path = tmp_path / "cli_env_override.json"
        env = os.environ.copy()
        env["THRESHOLD_GROUNDEDNESS"] = "0.9999"  # High threshold triggers breach
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "evaluate_production_agent.py"),
            "--dataset",
            str(DATASET_PATH),
            "--output",
            str(scorecard_path),
            "--mock",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        assert result.returncode == 1, f"Expected returncode 1 with env override, got {result.returncode}"
        assert "[FAILURE]" in result.stdout + result.stderr

    def test_live_query_failure_raises_runtime_error(self):
        """Verifies live query on invalid endpoint raises RuntimeError instead of falling back to mock."""
        scenario = {
            "prompt": "Test prompt",
            "mock_response": {"content": "Secret Mock", "tool_calls": []},
        }
        with pytest.raises(RuntimeError) as exc_info:
            query_agent_engine(
                scenario=scenario,
                agent_engine_id="projects/riccardo-blog-test-v1/locations/us-central1/reasoningEngines/9999999999999999999",
                project_id="riccardo-blog-test-v1",
                location="us-central1",
                mock_mode=False,
            )
        assert "Live Vertex AI Agent Engine query failed" in str(exc_info.value)

    def test_scorecard_saved_to_disk_contains_vertex_experiments_logged(self, tmp_path):
        """Verifies the scorecard JSON persisted to disk contains vertex_experiments_logged metadata."""
        output_file = tmp_path / "scorecard_disk_verify.json"
        passed, scorecard = run_evaluation(
            dataset_path=str(DATASET_PATH),
            output_path=str(output_file),
            mock_mode=True,
        )
        assert passed is True
        assert output_file.exists()
        with open(output_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert "vertex_experiments_logged" in disk_data["metadata"]
        assert disk_data["metadata"]["vertex_experiments_logged"] is True

    def test_run_id_ensures_canary_phase_uniqueness(self, tmp_path):
        """Verifies run_id incorporates canary_phase to prevent Vertex Experiments context collisions."""
        output_file = tmp_path / "scorecard_run_id.json"
        passed, scorecard = run_evaluation(
            dataset_path=str(DATASET_PATH),
            output_path=str(output_file),
            run_id="release-cand-99",
            canary_phase="canary-50",
            mock_mode=True,
        )
        assert scorecard["metadata"]["run_id"] == "release-cand-99-canary-50"

    def test_query_agent_engine_unpacks_inner_json_response(self):
        """Verifies query_agent_engine unpacks inner JSON-encoded ADK streaming response strings."""
        from unittest.mock import MagicMock, patch

        mock_chunk = MagicMock()
        inner_payload = {
            "response": "Extracted natural language answer for CNAPP",
            "tool_calls": [{"tool_name": "scan_cluster_vulnerabilities", "parameters": {"cluster_id": "c1"}}],
        }
        outer_envelope = {
            "content": {"parts": [{"text": json.dumps(inner_payload)}]},
        }
        mock_chunk.data = json.dumps(outer_envelope).encode("utf-8")

        mock_client = MagicMock()
        mock_client.stream_query_reasoning_engine.return_value = [mock_chunk]

        scenario = {"prompt": "Test prompt"}
        with patch("google.cloud.aiplatform_v1.ReasoningEngineExecutionServiceClient", return_value=mock_client):
            content, tools = query_agent_engine(
                scenario=scenario,
                agent_engine_id="projects/p/locations/l/reasoningEngines/123",
                project_id="p",
                location="l",
                mock_mode=False,
            )

        assert content == "Extracted natural language answer for CNAPP"
        assert len(tools) == 1
        assert tools[0]["tool_name"] == "scan_cluster_vulnerabilities"

    def test_query_agent_engine_mock_mode_none_mock_response(self):
        """Verifies query_agent_engine handles scenario with None mock_response without AttributeError."""
        scenario = {"prompt": "Test prompt", "mock_response": None}
        content, tools = query_agent_engine(
            scenario=scenario,
            agent_engine_id="projects/p/locations/l/reasoningEngines/123",
            project_id="p",
            location="l",
            mock_mode=True,
        )
        assert content == ""
        assert tools == []

    def test_query_agent_engine_unpacks_protobuf_struct_output(self):
        """Verifies query_agent_engine converts protobuf Struct output into dict in unary queries."""
        from unittest.mock import MagicMock, patch
        from google.protobuf.struct_pb2 import Struct

        struct_output = Struct()
        struct_output["response"] = "Protobuf output response"
        struct_output["tool_calls"] = [{"tool_name": "inspect_kms_key", "parameters": {"key": "primary"}}]

        mock_resp = MagicMock()
        mock_resp.output = struct_output

        mock_client = MagicMock()
        # Fail streaming query to trigger unary fallback
        mock_client.stream_query_reasoning_engine.side_effect = RuntimeError("Streaming unsupported")
        mock_client.query_reasoning_engine.return_value = mock_resp

        scenario = {"prompt": "Test prompt"}
        with patch("google.cloud.aiplatform_v1.ReasoningEngineExecutionServiceClient", return_value=mock_client):
            content, tools = query_agent_engine(
                scenario=scenario,
                agent_engine_id="projects/p/locations/l/reasoningEngines/123",
                project_id="p",
                location="l",
                mock_mode=False,
            )

        assert content == "Protobuf output response"
        assert len(tools) == 1
        assert tools[0]["tool_name"] == "inspect_kms_key"

    def test_cli_execution_handles_empty_threshold_env_vars(self, tmp_path):
        """Verifies CLI execution succeeds when THRESHOLD_* env vars are empty strings."""
        scorecard_path = tmp_path / "cli_empty_env.json"
        env = os.environ.copy()
        env["THRESHOLD_GROUNDEDNESS"] = ""
        env["THRESHOLD_HALLUCINATION_RATE"] = "  "
        env["THRESHOLD_TOOL_CALL_ACCURACY"] = ""
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "evaluate_production_agent.py"),
            "--dataset",
            str(DATASET_PATH),
            "--output",
            str(scorecard_path),
            "--mock",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Failed with stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert scorecard_path.exists()

        # Test nan/inf/out-of-bounds env var handling
        env["THRESHOLD_GROUNDEDNESS"] = "NaN"
        env["THRESHOLD_HALLUCINATION_RATE"] = "inf"
        env["THRESHOLD_TOOL_CALL_ACCURACY"] = "2.5"
        scorecard_nan_path = tmp_path / "cli_nan_env.json"
        cmd_nan = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "evaluate_production_agent.py"),
            "--dataset",
            str(DATASET_PATH),
            "--output",
            str(scorecard_nan_path),
            "--mock",
        ]
        result_nan = subprocess.run(cmd_nan, capture_output=True, text=True, env=env)
        assert result_nan.returncode == 0
        assert scorecard_nan_path.exists()

    def test_run_evaluation_nan_inf_thresholds_fallback(self, tmp_path):
        """Verifies run_evaluation sanitizes NaN, Inf, and out-of-bounds thresholds to safe defaults."""
        out_nan = tmp_path / "scorecard_nan.json"
        passed_nan, sc_nan = run_evaluation(
            dataset_path=str(DATASET_PATH),
            output_path=str(out_nan),
            min_groundedness=float("nan"),
            max_hallucination_rate=float("inf"),
            min_tool_call_accuracy=2.5,
            mock_mode=True,
        )
        assert passed_nan is True
        assert sc_nan["thresholds"]["min_groundedness"] == 0.80
        assert sc_nan["thresholds"]["max_hallucination_rate"] == 0.05
        assert sc_nan["thresholds"]["min_tool_call_accuracy"] == 1.0

    def test_run_evaluation_all_invalid_scenarios_raises_value_error(self, tmp_path):
        """Verifies run_evaluation raises ValueError when all scenarios in dataset are non-dict."""
        bad_ds = tmp_path / "bad_dataset.json"
        with open(bad_ds, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "scenarios": ["str1", 123, None]}, f)
        with pytest.raises(ValueError) as exc:
            run_evaluation(str(bad_ds), str(tmp_path / "bad_out.json"), mock_mode=True)
        assert "No valid scenarios found in dataset" in str(exc.value)

    def test_run_evaluation_mixed_scenarios_undiluted_averages(self, tmp_path):
        """Verifies skipped non-dict scenario entries do not dilute score averages across valid scenarios."""
        mixed_ds = tmp_path / "mixed_dataset.json"
        mixed_data = {
            "version": "1.0",
            "scenarios": [
                "skipped_string_scenario",
                {
                    "scenario_id": "SC-001",
                    "name": "Clean Test",
                    "reference_context": "Service running normally.",
                    "prompt": "status",
                    "mock_response": {"content": "Service running normally.", "tool_calls": []},
                    "expected_tool_calls": [],
                },
            ],
        }
        with open(mixed_ds, "w", encoding="utf-8") as f:
            json.dump(mixed_data, f)
        passed, scorecard = run_evaluation(str(mixed_ds), str(tmp_path / "mixed_out.json"), mock_mode=True)
        assert passed is True
        assert scorecard["summary"]["total_scenarios"] == 1
        assert scorecard["summary"]["passed_scenarios"] == 1
        assert scorecard["summary"]["average_groundedness"] == 1.0

    def test_query_agent_engine_handles_none_and_non_dict_scenario(self):
        """Verifies query_agent_engine safely handles None and non-dict scenario input without AttributeError."""
        content1, tools1 = query_agent_engine(None, "engine", "p", "l", mock_mode=True)
        assert content1 == ""
        assert tools1 == []
        content2, tools2 = query_agent_engine("invalid", "engine", "p", "l", mock_mode=True)
        assert content2 == ""
        assert tools2 == []

    def test_cli_execution_rejects_nan_and_out_of_bounds_thresholds(self, tmp_path):
        """Verifies CLI execution rejects NaN, Inf, and out-of-bounds thresholds with exit code 2."""
        for invalid_val in ["nan", "NaN", "inf", "-0.5", "2.0"]:
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "evaluate_production_agent.py"),
                "--dataset",
                str(DATASET_PATH),
                "--output",
                str(tmp_path / f"cli_invalid_{invalid_val}.json"),
                "--min-groundedness",
                invalid_val,
                "--mock",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            assert result.returncode == 2, f"Expected returncode 2 for threshold '{invalid_val}', got {result.returncode}"
            assert "error: argument --min-groundedness" in result.stderr

    def test_query_agent_engine_streaming_function_call_camel_case(self):
        """Verifies streaming parser extracts tool calls when serialized using camelCase functionCall."""
        from unittest.mock import MagicMock, patch

        mock_chunk = MagicMock()
        mock_chunk.data = json.dumps({
            "content": {
                "parts": [
                    {"text": "Cluster inspection"},
                    {"functionCall": {"name": "scan_cluster", "args": {"cluster_id": "c1"}}},
                ]
            }
        }).encode("utf-8")
        mock_client = MagicMock()
        mock_client.stream_query_reasoning_engine.return_value = [mock_chunk]

        with patch("google.cloud.aiplatform_v1.ReasoningEngineExecutionServiceClient", return_value=mock_client):
            content, tools = query_agent_engine(
                scenario={"prompt": "scan"},
                agent_engine_id="projects/p/locations/l/reasoningEngines/123",
                project_id="p",
                location="l",
                mock_mode=False,
            )
        assert content == "Cluster inspection"
        assert len(tools) == 1
        assert tools[0]["tool_name"] == "scan_cluster"
        assert tools[0]["parameters"] == {"cluster_id": "c1"}

    def test_query_agent_engine_unary_function_call_camel_case(self):
        """Verifies unary query fallback extracts functionCall and toolCalls."""
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.output = {
            "response": "Unary response",
            "functionCall": {"name": "inspect_kms_key", "args": {"key": "primary"}},
        }
        mock_client = MagicMock()
        mock_client.stream_query_reasoning_engine.side_effect = RuntimeError("Streaming failed")
        mock_client.query_reasoning_engine.return_value = mock_resp

        with patch("google.cloud.aiplatform_v1.ReasoningEngineExecutionServiceClient", return_value=mock_client):
            content, tools = query_agent_engine(
                scenario={"prompt": "inspect"},
                agent_engine_id="projects/p/locations/l/reasoningEngines/123",
                project_id="p",
                location="l",
                mock_mode=False,
            )
        assert content == "Unary response"
        assert len(tools) == 1
        assert tools[0]["tool_name"] == "inspect_kms_key"

    def test_query_agent_engine_mock_mode_tool_calls_variations(self):
        """Verifies mock mode safely unpacks toolCalls and singular function_call."""
        scenario1 = {
            "prompt": "test",
            "mock_response": {
                "content": "resp1",
                "toolCalls": [{"tool_name": "scan", "parameters": {"id": "1"}}],
            },
        }
        c1, t1 = query_agent_engine(scenario1, "engine", "p", "l", mock_mode=True)
        assert c1 == "resp1"
        assert len(t1) == 1
        assert t1[0]["tool_name"] == "scan"

        scenario2 = {
            "prompt": "test",
            "mock_response": {
                "content": "resp2",
                "function_call": {"name": "scan_singular", "args": {"id": "2"}},
            },
        }
        c2, t2 = query_agent_engine(scenario2, "engine", "p", "l", mock_mode=True)
        assert c2 == "resp2"
        assert len(t2) == 1
        assert t2[0]["tool_name"] == "scan_singular"

    def test_run_evaluation_scenario_exception_handling_and_scorecard_persistence(self, tmp_path):
        """Verifies unexpected scenario evaluation error is caught, recorded, and scorecard saved."""
        custom_data = {
            "version": "1.0",
            "scenarios": [
                {
                    "scenario_id": "SC-CRASH-01",
                    "name": "Crash Scenario",
                    "prompt": "crash",
                    # mock_response raises or produces error during scoring
                    "mock_response": {"content": 12345, "tool_calls": "not_a_list"},
                }
            ],
        }
        test_ds = tmp_path / "crash_dataset.json"
        with open(test_ds, "w", encoding="utf-8") as f:
            json.dump(custom_data, f)

        out_path = tmp_path / "crash_scorecard.json"
        passed, scorecard = run_evaluation(str(test_ds), str(out_path), mock_mode=True)
        assert passed is False
        assert out_path.exists()
        assert scorecard["summary"]["quality_gate_passed"] is False
        assert scorecard["summary"]["total_scenarios"] == 1
        assert scorecard["summary"]["passed_scenarios"] == 0
        assert len(scorecard["violations"]) > 0



# =====================================================================
# 4. Declarative Manifests Validity Tests
# =====================================================================
class TestDeclarativeManifestsValidity:
    """Validates Cloud Deploy verify manifests and Skaffold configuration syntax."""

    def test_clouddeploy_manifest_exists_and_parses(self):
        """Verifies infra/clouddeploy/verify-agent-eval.yaml is valid multi-doc YAML."""
        assert CLOUDDEPLOY_MANIFEST_PATH.exists(), f"Missing manifest: {CLOUDDEPLOY_MANIFEST_PATH}"
        with open(CLOUDDEPLOY_MANIFEST_PATH, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        assert len(docs) == 3, f"Expected 3 YAML documents, got {len(docs)}"

    def test_clouddeploy_pipeline_canary_verify_configuration(self):
        """Verifies DeliveryPipeline defines canary verify phases (canary-25, canary-50)."""
        with open(CLOUDDEPLOY_MANIFEST_PATH, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))

        pipeline = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
        assert pipeline is not None
        assert pipeline["metadata"]["name"] == "conductor-v3-pipeline"

        stages = pipeline["serialPipeline"]["stages"]
        prod_stage = next((s for s in stages if s.get("targetId") == "prod"), None)
        assert prod_stage is not None

        canary = prod_stage["strategy"]["canary"]
        assert canary["canaryDeployment"]["verify"] is True
        assert canary["canaryDeployment"]["percentages"] == [25, 50]

    def test_clouddeploy_target_private_worker_pool_and_timeout(self):
        """Requirement R3: Private worker pool and 600s execution timeout per ADR-20260902-05."""
        with open(CLOUDDEPLOY_MANIFEST_PATH, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))

        target = next((d for d in docs if d.get("kind") == "Target" and d["metadata"]["name"] == "prod"), None)
        assert target is not None
        assert target.get("requireApproval") is True

        exec_configs = target.get("executionConfigs", [])
        assert len(exec_configs) > 0

        verify_config = next((c for c in exec_configs if "VERIFY" in c.get("usages", [])), None)
        assert verify_config is not None, "Missing executionConfig for VERIFY usage"

        expected_pool = (
            "projects/riccardo-blog-test-v1/locations/us-central1/workerPools/cloudbuild-workerpool"
        )
        assert verify_config["workerPool"] == expected_pool
        assert verify_config["executionTimeout"] == "600s"

        # Verify deployParameters include quality thresholds
        params = target.get("deployParameters", {})
        assert params.get("THRESHOLD_GROUNDEDNESS") == "0.80"
        assert params.get("THRESHOLD_HALLUCINATION_RATE") == "0.05"
        assert params.get("THRESHOLD_TOOL_CALL_ACCURACY") == "0.90"

    def test_clouddeploy_automation_advance_canary(self):
        """Verifies automation rule advances rollout post-verification."""
        with open(CLOUDDEPLOY_MANIFEST_PATH, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))

        automation = next((d for d in docs if d.get("kind") == "Automation"), None)
        assert automation is not None
        rules = automation.get("rules", [])
        assert len(rules) > 0

        advance_rule = rules[0].get("advanceRolloutRule")
        assert advance_rule is not None
        assert advance_rule.get("sourcePhases") == ["canary-25", "canary-50"]

    def test_skaffold_manifest_exists_and_parses(self):
        """Verifies infra/clouddeploy/skaffold-agent-eval.yaml is valid Skaffold config."""
        assert SKAFFOLD_MANIFEST_PATH.exists(), f"Missing manifest: {SKAFFOLD_MANIFEST_PATH}"
        with open(SKAFFOLD_MANIFEST_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config.get("apiVersion") == "skaffold/v4beta7"
        assert config.get("kind") == "Config"
        assert config.get("metadata", {}).get("name") == "conductor-v3-agent-eval"

        # Check customActions and verify sections
        assert "customActions" in config
        assert len(config["customActions"]) > 0
        action = config["customActions"][0]
        assert action["name"] == "verify-production-agent-eval"

        assert "verify" in config
        assert len(config["verify"]) > 0
        verifier = config["verify"][0]
        assert verifier["name"] == "verify-agent-evaluation"

    def test_skaffold_manifest_dynamic_mock_agent_configuration(self):
        """Verifies Skaffold manifest does not hardcode --mock and respects MOCK_AGENT."""
        assert SKAFFOLD_MANIFEST_PATH.exists()
        content = SKAFFOLD_MANIFEST_PATH.read_text(encoding="utf-8")

        # Verify both customActions and verify use dynamic EXTRA_ARGS logic
        assert "EXTRA_ARGS" in content
        assert "${MOCK_AGENT:-true}" in content
        # Ensure --mock is not unconditionally hardcoded on the script invocation
        for line in content.splitlines():
            trimmed = line.strip()
            if trimmed.startswith("python3 scripts/evaluate_production_agent.py"):
                assert "--mock" not in trimmed, "Found hardcoded --mock on invocation line"


# =====================================================================
# 5. Isolation, ADR & Governance Tests
# =====================================================================
class TestRepositoryIsolationAndGovernance:
    """Validates strict isolation from rficonductorv2 and ADR compliance."""

    def test_primary_repository_untouched_isolation(self):
        """Requirement R1: Verifies evaluation assets are cleanly integrated into the primary repository."""
        assert REFERENCE_REPO_PATH.exists(), f"Reference repo path not found at {REFERENCE_REPO_PATH}"

        # Ensure all evaluation files are properly created and present in rficonductorv2
        required_in_ref = [
            REFERENCE_REPO_PATH / "data" / "golden_eval_dataset.json",
            REFERENCE_REPO_PATH / "scripts" / "evaluate_production_agent.py",
            REFERENCE_REPO_PATH / "docs" / "adr" / "ADR-20260903-08-production-canary-agent-evaluation.md",
            REFERENCE_REPO_PATH / "infra" / "clouddeploy" / "verify-agent-eval.yaml",
        ]
        for path in required_in_ref:
            assert path.exists(), f"Required evaluation asset missing in repository: {path}"

    def test_adr_document_structure_and_style_conformance(self):
        """Requirement R1: ADR document completeness, style, and Mermaid topology."""
        assert ADR_PATH.exists(), f"ADR file missing at {ADR_PATH}"
        content = ADR_PATH.read_text(encoding="utf-8")

        # Required ADR headers & metadata
        assert "ADR-20260903-08" in content
        assert "Production canary agent evaluation" in content
        assert "conductor-v3-prod-canary-eval" in content
        assert "cloudbuild-workerpool" in content
        assert "600s" in content

        # Required architectural sections
        assert "## 1. Context and problem statement" in content
        assert "## 2. Decision" in content
        assert "## 3. Evaluation engine trade-offs" in content
        assert "## 4. Canary verify phase execution architecture" in content
        assert "## 5. Experiment tracking with Vertex AI Experiments" in content
        assert "## 6. Metric selection and automated rollback thresholds" in content
        assert "## 7. Architectural topology" in content
        assert "## 8. Consequences" in content

        # Required Mermaid diagram
        assert "```mermaid" in content
        assert "conductor-v3-pipeline" in content
        assert "canary-25" in content

        # Google Writing Style rules:
        # 1. No unspaced em dashes (—)
        assert "—" not in content, "ADR contains forbidden em dash (—); must use en dash (' – ')"
        # 2. Canary phases mentioned with Oxford comma
        assert "canary-25" in content and "canary-50" in content and "stable" in content
        # 3. Sentence-style capitalization in headings
        for line in content.splitlines():
            if line.startswith("#"):
                # Title or heading
                heading_text = line.lstrip("#").strip()
                words = heading_text.split()
                if len(words) > 2 and not words[0].endswith("."):
                    for w in ["and", "problem", "statement", "trade-offs", "topology"]:
                        if w in heading_text.lower():
                            assert w in heading_text, f"Heading '{heading_text}' violates sentence-style capitalization"
