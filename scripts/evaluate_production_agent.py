#!/usr/bin/env python3
"""Conductor v3 Production Agent Evaluation Runner.

Evaluates the Vertex AI Agent Engine against the authoritative golden evaluation
dataset during Google Cloud Deploy canary rollout verify phases. Computes quantitative
metrics for groundedness, hallucination rate, and tool-call correctness, logs results
to Vertex AI Experiments and a JSON scorecard, and enforces automated quality gates.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("conductor_agent_eval")

# Default Configuration Constants
DEFAULT_AGENT_ENGINE_ID = (
    "projects/riccardo-blog-test-v1/locations/us-central1/reasoningEngines/1423301859237429248"
)
DEFAULT_PROJECT_ID = "riccardo-blog-test-v1"
DEFAULT_LOCATION = "us-central1"
DEFAULT_EXPERIMENT_NAME = "conductor-v3-prod-canary-eval"
DEFAULT_MIN_GROUNDEDNESS = 0.80
DEFAULT_MAX_HALLUCINATION_RATE = 0.05
DEFAULT_MIN_TOOL_CALL_ACCURACY = 0.90

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "can", "will", "just", "don", "should", "now", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "having", "do",
    "does", "did", "doing", "this", "that", "these", "those", "it", "its",
    "of", "as", "which", "would", "could", "may", "might", "must", "what",
    "who", "whom",
}


def normalize_text(text: Any) -> str:
    """Normalize text by lowering case, removing punctuation and normalizing whitespace."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if not text.strip():
        return ""
    text = text.lower()
    # Strip ellipses and consecutive dots
    text = re.sub(r"\.{2,}", " ", text)
    # Replace non-word, non-hyphen, non-slash, non-dot chars with space
    text = re.sub(r"[^\w\s\-\.\/]", " ", text)
    # Strip sentence-ending periods after words
    text = re.sub(r"(?<=\w)\.(?=\s|$)", " ", text)
    return " ".join(text.split())


def compute_groundedness_score(
    response_text: Any,
    reference_context: Any,
    expected_substrings: Optional[List[str]] = None,
) -> float:
    """Compute quantitative groundedness score in range [0.0, 1.0].

    Groundedness measures the proportion of factual claims in the agent's
    response supported by the authoritative reference context.
    """
    if response_text is None or reference_context is None:
        return 0.0
    response_text_str = str(response_text)
    reference_context_str = str(reference_context)
    if not response_text_str.strip() or not reference_context_str.strip():
        return 0.0

    norm_resp = normalize_text(response_text_str)
    norm_ref = normalize_text(reference_context_str)

    # 1. Key entity and substring containment score
    if isinstance(expected_substrings, str):
        expected_substrings = [expected_substrings]
    elif not isinstance(expected_substrings, (list, tuple, set)):
        expected_substrings = []

    valid_substrings = [
        str(s).strip() for s in expected_substrings
        if s is not None and str(s).strip() and normalize_text(str(s))
    ]
    has_substrings = len(valid_substrings) > 0
    substring_score = 0.0
    if has_substrings:
        found_count = sum(
            1 for sub in valid_substrings if normalize_text(sub) in norm_resp
        )
        substring_score = found_count / len(valid_substrings)

    # 2. Reference context token overlap (unigram support filtered for stopwords)
    ref_tokens = {tok for tok in norm_ref.split() if tok not in STOPWORDS}
    resp_tokens = [tok for tok in norm_resp.split() if tok not in STOPWORDS]

    if not resp_tokens:
        return 0.0

    supported_tokens = sum(
        1 for tok in resp_tokens
        if tok in ref_tokens or (len(tok) >= 4 and tok in norm_ref)
    )
    token_support_ratio = supported_tokens / len(resp_tokens)

    # If expected substrings were provided, blend entity match (60%) with token support (40%)
    # If no expected substrings were provided, base groundedness entirely on token support ratio
    if has_substrings:
        groundedness = (substring_score * 0.60) + (min(1.0, token_support_ratio * 1.25) * 0.40)
    else:
        groundedness = min(1.0, token_support_ratio * 1.25)

    return round(min(1.0, max(0.0, groundedness)), 4)


def compute_hallucination_rate(
    response_text: Any,
    reference_context: Any,
    forbidden_hallucinations: Optional[List[str]] = None,
) -> float:
    """Compute quantitative hallucination rate in range [0.0, 1.0].

    Hallucination rate measures the frequency of unsupported, fabricated,
    or explicitly forbidden assertions present in the response text.
    0.0 represents zero detected hallucinations (perfect score).
    """
    if response_text is None:
        return 0.0
    response_text_str = str(response_text)
    if not response_text_str.strip():
        return 0.0
    if reference_context is None:
        return 1.0
    reference_context_str = str(reference_context)
    if not reference_context_str.strip():
        return 1.0

    norm_resp = normalize_text(response_text_str)
    norm_ref = normalize_text(reference_context_str)
    ref_lower = reference_context_str.lower()

    # 1. Check for explicit forbidden hallucinations (sanitizing empty / whitespace entries)
    if isinstance(forbidden_hallucinations, str):
        forbidden_hallucinations = [forbidden_hallucinations]
    elif not isinstance(forbidden_hallucinations, (list, tuple, set)):
        forbidden_hallucinations = []

    valid_forbidden = [
        str(fh).strip() for fh in forbidden_hallucinations
        if fh is not None and str(fh).strip() and normalize_text(str(fh))
    ]
    if valid_forbidden:
        detected_forbidden = [
            fh for fh in valid_forbidden if normalize_text(fh) in norm_resp
        ]
        if detected_forbidden:
            penalty = len(detected_forbidden) / len(valid_forbidden)
            return round(min(1.0, max(0.20, penalty)), 4)

    # 2. Entity and numeric identifier check: verify specific identifiers/numbers exist in context
    resp_entities = set(re.findall(r"\b[A-Za-z0-9_\-\.\/]{4,}\b", response_text_str))
    common_words = {
        "that", "with", "from", "this", "have", "were", "which", "their",
        "about", "would", "there", "could", "other", "after", "first",
        "these", "those", "being", "under", "where", "while", "every",
        "between", "through", "should", "during", "before", "against",
    }
    specific_identifiers = {
        e for e in resp_entities if e.lower() not in common_words and not e.isalpha()
    }
    if specific_identifiers:
        unsupported = sum(
            1 for e in specific_identifiers
            if e.lower() not in ref_lower and normalize_text(e) not in norm_ref
        )
        if unsupported > 0:
            return round(min(1.0, unsupported / len(specific_identifiers)), 4)

    # 3. Overall content token ungroundedness check
    resp_tokens = [tok for tok in norm_resp.split() if tok not in STOPWORDS]
    if resp_tokens:
        ref_tokens = {tok for tok in norm_ref.split() if tok not in STOPWORDS}
        unsupported_tokens = sum(
            1 for tok in resp_tokens
            if tok not in ref_tokens and (len(tok) < 4 or tok not in norm_ref)
        )
        unsupported_ratio = unsupported_tokens / len(resp_tokens)
        if unsupported_ratio > 0.40:
            return round(min(1.0, (unsupported_ratio - 0.40) / 0.60), 4)

    return 0.0


def _param_values_match(val1: Any, val2: Any) -> bool:
    """Compare two parameter values for semantic equivalence."""
    if val1 == val2:
        return True
    if val1 is None or val2 is None:
        return val1 == val2

    # JSON string deserialization if value is a serialized JSON object or array
    if isinstance(val1, str):
        s1 = val1.strip()
        if (s1.startswith("{") and s1.endswith("}")) or (s1.startswith("[") and s1.endswith("]")):
            try:
                parsed1 = json.loads(s1)
                if isinstance(parsed1, (dict, list)):
                    val1 = parsed1
            except Exception:
                pass

    if isinstance(val2, str):
        s2 = val2.strip()
        if (s2.startswith("{") and s2.endswith("}")) or (s2.startswith("[") and s2.endswith("]")):
            try:
                parsed2 = json.loads(s2)
                if isinstance(parsed2, (dict, list)):
                    val2 = parsed2
            except Exception:
                pass

    # Re-check identity / exact equality after JSON deserialization
    if val1 == val2:
        return True

    # Numeric equivalence (e.g. 1 vs 1.0 vs "1.00")
    try:
        if isinstance(val1, (int, float, str)) and isinstance(val2, (int, float, str)):
            # Avoid treating bools as numeric (bool is a subclass of int in Python)
            if not isinstance(val1, bool) and not isinstance(val2, bool):
                s1 = str(val1).strip()
                s2 = str(val2).strip()
                if s1 and s2 and not (s1.isalpha() or s2.isalpha()):
                    import math
                    f1 = float(s1)
                    f2 = float(s2)
                    if not (math.isnan(f1) or math.isnan(f2)):
                        if abs(f1 - f2) < 1e-6:
                            return True
    except (ValueError, TypeError, OverflowError):
        pass

    # String comparison (case-insensitive and trimmed)
    if isinstance(val1, str) and isinstance(val2, str):
        return val1.strip().lower() == val2.strip().lower()

    # Dictionary comparison (recursive, normalized key matching for snake_case, camelCase, kebab-case)
    if isinstance(val1, dict) and isinstance(val2, dict):
        if len(val1) != len(val2):
            return False
        val2_norm = {
            str(k).strip().replace("_", "").replace("-", "").lower(): k for k in val2
        }
        for k1, v1 in val1.items():
            k1_norm = str(k1).strip().replace("_", "").replace("-", "").lower()
            if k1_norm not in val2_norm:
                return False
            matching_key_2 = val2_norm[k1_norm]
            if not _param_values_match(v1, val2[matching_key_2]):
                return False
        return True

    # List comparison (order-independent if elements can match 1-to-1)
    if isinstance(val1, list) and isinstance(val2, list):
        if len(val1) != len(val2):
            return False
        if all(_param_values_match(x, y) for x, y in zip(val1, val2)):
            return True
        used_indices = set()
        for item1 in val1:
            matched = False
            for idx, item2 in enumerate(val2):
                if idx not in used_indices and _param_values_match(item1, item2):
                    used_indices.add(idx)
                    matched = True
                    break
            if not matched:
                return False
        return True

    return str(val1).strip().lower() == str(val2).strip().lower()


def compute_tool_call_accuracy(
    actual_tool_calls: List[Dict[str, Any]],
    expected_tool_calls: List[Dict[str, Any]],
) -> float:
    """Compute tool-call accuracy score in range [0.0, 1.0].

    Validates tool name invocations and parameter dictionary equivalence.
    Uses 1-to-1 matching so each actual tool call is only credited once.
    """
    if not isinstance(actual_tool_calls, list):
        actual_tool_calls = [actual_tool_calls] if actual_tool_calls else []
    if not isinstance(expected_tool_calls, list):
        expected_tool_calls = [expected_tool_calls] if expected_tool_calls else []

    if not expected_tool_calls and not actual_tool_calls:
        return 1.0
    if not expected_tool_calls and actual_tool_calls:
        # Extraneous unexpected tool calls
        return max(0.0, 1.0 - (0.25 * len(actual_tool_calls)))
    if expected_tool_calls and not actual_tool_calls:
        return 0.0

    def _sanitize_tool_call(tc: Any) -> Dict[str, Any]:
        if not isinstance(tc, dict):
            return {"tool_name": str(tc) if tc is not None else "", "parameters": {}}
        raw_name = tc.get("tool_name")
        raw_name = str(raw_name).strip() if raw_name is not None else ""
        raw_params = tc.get("parameters")
        if isinstance(raw_params, str) and (raw_params.strip().startswith("{") and raw_params.strip().endswith("}")):
            try:
                raw_params = json.loads(raw_params)
            except Exception:
                raw_params = {}
        elif not isinstance(raw_params, dict):
            raw_params = {}
        return {"tool_name": raw_name, "parameters": raw_params}

    sanitized_actual = [_sanitize_tool_call(a) for a in actual_tool_calls]
    sanitized_expected = [_sanitize_tool_call(e) for e in expected_tool_calls]

    total_expected = len(sanitized_expected)

    # Precompute pairwise similarity scores: (score, exp_idx, act_idx)
    candidate_matches: List[Tuple[float, int, int]] = []
    for exp_idx, exp in enumerate(sanitized_expected):
        exp_name = exp.get("tool_name", "").strip().lower()
        if not exp_name:
            continue
        exp_params = exp.get("parameters", {})

        for act_idx, act in enumerate(sanitized_actual):
            act_name = act.get("tool_name", "").strip().lower()
            if not act_name:
                continue
            act_params = act.get("parameters", {})

            if act_name == exp_name:
                name_score = 0.50
                # Compare parameters
                if not exp_params and not act_params:
                    param_score = 0.50
                elif exp_params and act_params:
                    # Match parameter keys (allowing for snake_case vs camelCase vs kebab-case)
                    act_key_map = {
                        str(k).replace("_", "").replace("-", "").lower(): k for k in act_params
                    }
                    param_matches = 0
                    for k, v in exp_params.items():
                        norm_k = str(k).replace("_", "").replace("-", "").lower()
                        if norm_k in act_key_map:
                            act_k = act_key_map[norm_k]
                            if _param_values_match(act_params[act_k], v):
                                param_matches += 1
                    param_score = 0.50 * (param_matches / max(len(exp_params), len(act_params)))
                else:
                    param_score = 0.0
                total_pair_score = name_score + param_score
                candidate_matches.append((total_pair_score, exp_idx, act_idx))

    # Sort descending by pair score for optimal greedy 1-to-1 matching
    candidate_matches.sort(key=lambda x: x[0], reverse=True)

    matched_exp_indices = set()
    used_act_indices = set()
    matched_tools_score = 0.0

    for score, exp_idx, act_idx in candidate_matches:
        if exp_idx not in matched_exp_indices and act_idx not in used_act_indices:
            matched_exp_indices.add(exp_idx)
            used_act_indices.add(act_idx)
            matched_tools_score += score

    accuracy = matched_tools_score / total_expected

    # Penalize extra unrequested tool calls
    extraneous_count = len(sanitized_actual) - len(used_act_indices)
    if extraneous_count > 0:
        accuracy = max(0.0, accuracy - (0.10 * extraneous_count))

    return round(min(1.0, max(0.0, accuracy)), 4)


def query_agent_engine(
    scenario: Dict[str, Any],
    agent_engine_id: str,
    project_id: str,
    location: str,
    mock_mode: bool = True,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Query the Vertex AI Agent Engine or return realistic mock responses."""
    if not isinstance(scenario, dict):
        scenario = {}

    if mock_mode:
        mock_data = scenario.get("mock_response") or {}
        if not isinstance(mock_data, dict):
            mock_data = {"content": str(mock_data), "tool_calls": []}
        content = mock_data.get("content") or ""
        tool_calls = mock_data.get("tool_calls") or mock_data.get("toolCalls") or []
        if not tool_calls:
            fc = mock_data.get("function_call") or mock_data.get("functionCall") or mock_data.get("tool_call")
            if fc and isinstance(fc, dict):
                tool_calls = [{
                    "tool_name": fc.get("name") or fc.get("tool_name") or "",
                    "parameters": fc.get("args") or fc.get("parameters") or {},
                }]
        return content, tool_calls

    # Live Vertex AI Reasoning Engine execution
    from google.cloud import aiplatform_v1

    logger.info("Querying live Vertex AI Reasoning Engine: %s", agent_engine_id)
    client_options = {"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    client = aiplatform_v1.ReasoningEngineExecutionServiceClient(client_options=client_options)
    prompt_text = scenario.get("prompt", "")

    # 1. Attempt ADK streaming query (async_stream_query)
    try:
        req = {
            "name": agent_engine_id,
            "class_method": "async_stream_query",
            "input": {
                "message": {"role": "user", "parts": [{"text": prompt_text}]},
                "user_id": "conductor_canary_evaluator",
            },
        }
        stream = client.stream_query_reasoning_engine(request=req, timeout=30.0)
        content_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []

        for chunk in stream:
            raw_data = getattr(chunk, "data", None)
            if not raw_data:
                continue
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8")
            try:
                parsed = json.loads(raw_data)
                # Check for parts inside content
                parts = parsed.get("content", {}).get("parts", [])
                for p in parts:
                    if isinstance(p, dict):
                        text_val = p.get("text", "")
                        if text_val:
                            try:
                                inner_obj = json.loads(text_val)
                                if isinstance(inner_obj, dict):
                                    if "response" in inner_obj:
                                        content_parts.append(str(inner_obj["response"]))
                                    else:
                                        content_parts.append(text_val)
                                    inner_tc = inner_obj.get("tool_calls") or inner_obj.get("toolCalls")
                                    if inner_tc and isinstance(inner_tc, list):
                                        tool_calls.extend(inner_tc)
                                    else:
                                        inner_fc = inner_obj.get("function_call") or inner_obj.get("functionCall")
                                        if inner_fc and isinstance(inner_fc, dict):
                                            tool_calls.append({
                                                "tool_name": inner_fc.get("name") or inner_fc.get("tool_name") or "",
                                                "parameters": inner_fc.get("args") or inner_fc.get("parameters") or {},
                                            })
                                else:
                                    content_parts.append(text_val)
                            except (json.JSONDecodeError, TypeError):
                                content_parts.append(text_val)
                        fc = p.get("function_call") or p.get("functionCall")
                        if fc and isinstance(fc, dict):
                            tool_calls.append({
                                "tool_name": fc.get("name") or fc.get("tool_name") or "",
                                "parameters": fc.get("args") or fc.get("parameters") or {},
                            })
                # Check for actions
                actions = parsed.get("actions", {})
                action_tc = actions.get("tool_calls") or actions.get("toolCalls")
                if action_tc and isinstance(action_tc, list):
                    tool_calls.extend(action_tc)
            except Exception:
                content_parts.append(str(raw_data))

        if content_parts or tool_calls:
            return "\n".join(content_parts), tool_calls
    except Exception as adk_exc:
        logger.warning(
            "ADK stream query failed (%s); attempting standard unary query fallback.",
            adk_exc,
        )

    # 2. Attempt standard unary query fallback
    try:
        request = {
            "name": agent_engine_id,
            "input": {"prompt": prompt_text},
        }
        response = client.query_reasoning_engine(request=request, timeout=30.0)
        output = response.output

        # If output is a protobuf Struct or mapping, convert to dict
        if hasattr(output, "items") and not isinstance(output, dict):
            try:
                from google.protobuf.json_format import MessageToDict
                output = MessageToDict(output)
            except Exception:
                try:
                    output = dict(output.items())
                except Exception:
                    pass

        if isinstance(output, dict):
            content = output.get("content") or output.get("response") or str(output)
            tool_calls = output.get("tool_calls") or output.get("toolCalls") or []
            if not tool_calls:
                fc = output.get("function_call") or output.get("functionCall") or output.get("tool_call")
                if fc and isinstance(fc, dict):
                    tool_calls = [{
                        "tool_name": fc.get("name") or fc.get("tool_name") or "",
                        "parameters": fc.get("args") or fc.get("parameters") or {},
                    }]
        else:
            content = str(output)
            tool_calls = []

        # If content is a JSON-encoded string, unpack inner fields
        if isinstance(content, str) and (content.strip().startswith("{") and content.strip().endswith("}")):
            try:
                inner_obj = json.loads(content)
                if isinstance(inner_obj, dict):
                    if "response" in inner_obj:
                        content = str(inner_obj["response"])
                    inner_tc = inner_obj.get("tool_calls") or inner_obj.get("toolCalls")
                    if inner_tc and isinstance(inner_tc, list):
                        tool_calls.extend(inner_tc)
                    else:
                        inner_fc = inner_obj.get("function_call") or inner_obj.get("functionCall")
                        if inner_fc and isinstance(inner_fc, dict):
                            tool_calls.append({
                                "tool_name": inner_fc.get("name") or inner_fc.get("tool_name") or "",
                                "parameters": inner_fc.get("args") or inner_fc.get("parameters") or {},
                            })
            except (json.JSONDecodeError, TypeError):
                pass

        return content, tool_calls
    except Exception as unary_exc:
        # In live mode, DO NOT silently fall back to mock data!
        logger.error("Live Reasoning Engine query failed for %s: %s", agent_engine_id, unary_exc)
        raise RuntimeError(
            f"Live Vertex AI Agent Engine query failed on {agent_engine_id}: {unary_exc}"
        ) from unary_exc


def log_experiment_metrics(
    experiment_name: str,
    run_id: str,
    metrics: Dict[str, float],
    params: Dict[str, Any],
    project_id: str,
    location: str,
    mock_mode: bool = True,
) -> bool:
    """Log evaluation run metrics to Vertex AI Experiments."""
    if mock_mode:
        logger.info(
            "Mock mode active: recording metrics to Vertex AI Experiments '%s' (run: %s)",
            experiment_name,
            run_id,
        )
        return True

    try:
        from google.cloud import aiplatform
        aiplatform.init(project=project_id, location=location, experiment=experiment_name)
        with aiplatform.start_run(run=run_id):
            aiplatform.log_metrics(metrics)
            aiplatform.log_params(params)
        logger.info(
            "Successfully logged evaluation metrics to Vertex AI Experiment '%s' (run: %s)",
            experiment_name,
            run_id,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Unable to log to live Vertex AI Experiments (%s). Scorecard recorded locally.",
            exc,
        )
        return False


def extract_reasoning_engine_id(agent_engine_path: Any) -> str:
    """Extract numeric or short identifier from full Reasoning Engine resource path."""
    if agent_engine_path is None:
        return ""
    str_path = str(agent_engine_path).strip()
    if not str_path:
        return ""
    parts = str_path.rstrip("/").split("/")
    return parts[-1] if parts else str_path


def build_evaluation_run_payload(
    agent_engine_id: str = DEFAULT_AGENT_ENGINE_ID,
    run_id: Optional[str] = None,
    canary_phase: str = "canary-25",
    metrics: Optional[Dict[str, float]] = None,
    total_items: int = 12,
    passed_items: int = 12,
    quality_gate_passed: bool = True,
    dataset_version: str = "1.0",
    dataset_path: str = "data/golden_eval_dataset.json",
    evaluation_experiment_name: Optional[str] = None,
    candidate_name: str = "conductor-agent",
    project_id: str = DEFAULT_PROJECT_ID,
    location: str = DEFAULT_LOCATION,
) -> Dict[str, Any]:
    """Construct a valid Vertex AI Agent Platform EvaluationRun payload.

    Binds the EvaluationRun to the specified Reasoning Engine via agent_run_config
    and includes indexing labels required for the Agent Engine Console UI.
    """
    if metrics is None:
        metrics = {}
    if not run_id:
        timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_id = f"eval-{canary_phase}-{timestamp_str}"

    clean_project = str(project_id).strip().strip("/") if project_id else DEFAULT_PROJECT_ID
    clean_location = str(location).strip().strip("/") if location else DEFAULT_LOCATION

    # Normalize agent_engine_id to canonical resource path if a short, numeric, or partial path is passed
    str_engine_id = str(agent_engine_id).strip().rstrip("/") if agent_engine_id is not None else DEFAULT_AGENT_ENGINE_ID
    if not str_engine_id:
        str_engine_id = DEFAULT_AGENT_ENGINE_ID

    if str_engine_id and not str_engine_id.startswith("projects/"):
        if str_engine_id.startswith("locations/"):
            canonical_agent_engine = f"projects/{clean_project}/{str_engine_id}"
        elif str_engine_id.startswith("reasoningEngines/"):
            canonical_agent_engine = f"projects/{clean_project}/locations/{clean_location}/{str_engine_id}"
        else:
            canonical_agent_engine = f"projects/{clean_project}/locations/{clean_location}/reasoningEngines/{str_engine_id}"
    else:
        canonical_agent_engine = str_engine_id or DEFAULT_AGENT_ENGINE_ID

    engine_id_num = extract_reasoning_engine_id(canonical_agent_engine)
    state = "SUCCEEDED" if quality_gate_passed else "FAILED"
    display_name = f"conductor-v3-{canary_phase}-{run_id}"

    eval_metrics = [
        {
            "metric": "groundedness",
            "metric_config": {
                "predefined_metric_spec": {
                    "metric_spec_name": "groundedness",
                }
            },
        },
        {
            "metric": "hallucination_rate",
            "metric_config": {
                "predefined_metric_spec": {
                    "metric_spec_name": "hallucination_rate",
                }
            },
        },
        {
            "metric": "tool_call_accuracy",
            "metric_config": {
                "predefined_metric_spec": {
                    "metric_spec_name": "tool_call_accuracy",
                }
            },
        },
    ]

    summary_metrics_dict = {
        "groundedness": float(metrics.get("average_groundedness", metrics.get("groundedness", 0.0))),
        "hallucination_rate": float(metrics.get("average_hallucination_rate", metrics.get("hallucination_rate", 0.0))),
        "tool_call_accuracy": float(metrics.get("average_tool_call_accuracy", metrics.get("tool_call_accuracy", 0.0))),
        "quality_gate_passed": 1.0 if quality_gate_passed else 0.0,
    }

    eval_set_path = f"projects/{clean_project}/locations/{clean_location}/evaluationSets/conductor-v3-golden-dataset"
    failed_items_count = max(0, total_items - passed_items)

    payload: Dict[str, Any] = {
        "display_name": display_name,
        "displayName": display_name,
        "agent_engine": canonical_agent_engine,
        "agentEngine": canonical_agent_engine,
        "labels": {
            "vertex-ai-evaluation-agent-engine-id": engine_id_num,
            "vertex-ai-evaluation-agent-engine-location": clean_location,
            "canary_phase": canary_phase,
            "quality_gate_passed": "true" if quality_gate_passed else "false",
            "pipeline": "conductor-v3",
        },
        "data_source": {
            "evaluation_set": eval_set_path,
            "evaluationSet": eval_set_path,
        },
        "dataSource": {
            "evaluation_set": eval_set_path,
            "evaluationSet": eval_set_path,
        },
        "inference_configs": {
            candidate_name: {
                "agent_run_config": {
                    "agent_engine": canonical_agent_engine,
                    "agentEngine": canonical_agent_engine,
                },
                "agentRunConfig": {
                    "agent_engine": canonical_agent_engine,
                    "agentEngine": canonical_agent_engine,
                },
            }
        },
        "inferenceConfigs": {
            candidate_name: {
                "agent_run_config": {
                    "agent_engine": canonical_agent_engine,
                    "agentEngine": canonical_agent_engine,
                },
                "agentRunConfig": {
                    "agent_engine": canonical_agent_engine,
                    "agentEngine": canonical_agent_engine,
                },
            }
        },
        "evaluation_config": {
            "metrics": eval_metrics,
        },
        "evaluationConfig": {
            "metrics": eval_metrics,
        },
        "evaluation_results": {
            "summary_metrics": {
                "metrics": summary_metrics_dict,
                "total_items": total_items,
                "failed_items": failed_items_count,
                "totalItems": total_items,
                "failedItems": failed_items_count,
            }
        },
        "evaluationResults": {
            "summaryMetrics": {
                "metrics": summary_metrics_dict,
                "total_items": total_items,
                "failed_items": failed_items_count,
                "totalItems": total_items,
                "failedItems": failed_items_count,
            }
        },
        "state": state,
        "metadata": {
            "agent_engine_id": canonical_agent_engine,
            "canary_phase": canary_phase,
            "run_id": run_id,
            "dataset_path": dataset_path,
            "dataset_version": dataset_version,
            "quality_gate_passed": str(quality_gate_passed).lower(),
            "groundedness": str(summary_metrics_dict["groundedness"]),
            "hallucination_rate": str(summary_metrics_dict["hallucination_rate"]),
            "tool_call_accuracy": str(summary_metrics_dict["tool_call_accuracy"]),
        },
    }

    if evaluation_experiment_name and str(evaluation_experiment_name).strip():
        str_exp_name = str(evaluation_experiment_name).strip().rstrip("/")
        if not str_exp_name.startswith("projects/"):
            if str_exp_name.startswith("locations/"):
                canonical_exp = f"projects/{clean_project}/{str_exp_name}"
            elif str_exp_name.startswith("evaluationExperiments/"):
                canonical_exp = f"projects/{clean_project}/locations/{clean_location}/{str_exp_name}"
            else:
                canonical_exp = f"projects/{clean_project}/locations/{clean_location}/evaluationExperiments/{str_exp_name}"
        else:
            canonical_exp = str_exp_name
        payload["evaluation_experiment"] = canonical_exp
        payload["evaluationExperiment"] = canonical_exp

    return payload


def publish_evaluation_run(
    project_id: str,
    location: str,
    payload: Optional[Dict[str, Any]],
    mock_mode: bool = True,
    api_endpoint: Optional[str] = None,
    timeout: float = 30.0,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Publish an EvaluationRun resource to Vertex AI Agent Platform Evaluation API (v1beta1).

    Supports dual logging alongside Vertex AI Experiments. Provides resilient
    fallback handling in mock mode and restricted environments.
    """
    if not isinstance(payload, dict):
        payload = {}

    clean_project = str(project_id).strip().strip("/") if project_id else DEFAULT_PROJECT_ID
    clean_location = str(location).strip().strip("/") if location else DEFAULT_LOCATION

    run_name = payload.get("display_name") or payload.get("displayName") or "evaluation-run"
    resource_name = f"projects/{clean_project}/locations/{clean_location}/evaluationRuns/{run_name}"

    if mock_mode:
        logger.info(
            "Mock mode active: registered Vertex AI EvaluationRun resource '%s'",
            resource_name,
        )
        mock_response = dict(payload)
        mock_response["name"] = resource_name
        return True, mock_response

    env_endpoint = os.getenv("VERTEX_EVALUATION_ENDPOINT")
    raw_endpoint = api_endpoint if (api_endpoint and str(api_endpoint).strip()) else env_endpoint
    if not raw_endpoint or not str(raw_endpoint).strip():
        raw_endpoint = f"https://{clean_location}-aiplatform.googleapis.com"
    endpoint_str = str(raw_endpoint).strip().rstrip("/")
    if not (endpoint_str.startswith("http://") or endpoint_str.startswith("https://")):
        endpoint_str = f"https://{endpoint_str}"
    # Strip any trailing /v1beta1 or /v1 to prevent duplicate API version path segments
    if endpoint_str.endswith("/v1beta1"):
        endpoint_str = endpoint_str[:-len("/v1beta1")].rstrip("/")
    elif endpoint_str.endswith("/v1"):
        endpoint_str = endpoint_str[:-len("/v1")].rstrip("/")

    url = f"{endpoint_str}/v1beta1/projects/{clean_project}/locations/{clean_location}/evaluationRuns"

    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        session = AuthorizedSession(credentials)
        logger.info("Publishing EvaluationRun to Vertex AI Agent Platform: %s", url)

        resp = session.post(url, json=payload, timeout=timeout)
        if 200 <= resp.status_code < 300:
            try:
                resp_data = resp.json()
            except Exception:
                resp_data = {"name": resource_name, "state": payload.get("state", "SUCCEEDED")}
            if not isinstance(resp_data, dict):
                resp_data = {"name": resource_name, "state": payload.get("state", "SUCCEEDED")}
            logger.info(
                "Successfully registered Vertex AI EvaluationRun: %s",
                resp_data.get("name", url),
            )
            return True, resp_data
        else:
            logger.warning(
                "Vertex AI EvaluationRun API returned HTTP %d: %s. Continuing with local scorecard.",
                resp.status_code,
                resp.text,
            )
            return False, None
    except Exception as exc:
        logger.warning(
            "Unable to publish to live Vertex AI EvaluationRun service (%s). Scorecard recorded locally.",
            exc,
        )
        return False, None


def run_evaluation(
    dataset_path: str,
    output_path: str,
    agent_engine_id: str = DEFAULT_AGENT_ENGINE_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    location: str = DEFAULT_LOCATION,
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    run_id: Optional[str] = None,
    canary_phase: str = "canary-25",
    min_groundedness: float = DEFAULT_MIN_GROUNDEDNESS,
    max_hallucination_rate: float = DEFAULT_MAX_HALLUCINATION_RATE,
    min_tool_call_accuracy: float = DEFAULT_MIN_TOOL_CALL_ACCURACY,
    mock_mode: bool = True,
    scorer_type: str = "custom",
    publish_evaluation_run_enabled: bool = True,
    api_endpoint: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any]]:
    import math

    def _sanitize_threshold(val: Any, default_val: float) -> float:
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return default_val
            return max(0.0, min(1.0, f))
        except (ValueError, TypeError):
            return default_val

    min_groundedness = _sanitize_threshold(min_groundedness, DEFAULT_MIN_GROUNDEDNESS)
    max_hallucination_rate = _sanitize_threshold(max_hallucination_rate, DEFAULT_MAX_HALLUCINATION_RATE)
    min_tool_call_accuracy = _sanitize_threshold(min_tool_call_accuracy, DEFAULT_MIN_TOOL_CALL_ACCURACY)

    logger.info("================================================================")
    logger.info("Starting Conductor v3 Production Agent Evaluation")
    logger.info("Dataset:             %s", dataset_path)
    logger.info("Agent Engine ID:     %s", agent_engine_id)
    logger.info("Canary Phase:        %s", canary_phase)
    logger.info("Mock Mode:           %s", mock_mode)
    logger.info("Scorer Engine:       %s", scorer_type)
    logger.info(
        "Thresholds:          Groundedness >= %.2f | Hallucination <= %.2f | Tool Accuracy >= %.2f",
        min_groundedness,
        max_hallucination_rate,
        min_tool_call_accuracy,
    )
    logger.info("================================================================")

    dataset_path = dataset_path or "data/golden_eval_dataset.json"
    output_path = output_path or "scorecard.json"

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Golden dataset not found at: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if not isinstance(dataset, dict):
        raise ValueError(f"Invalid dataset format in {dataset_path}; expected JSON object with 'scenarios' list")

    scenarios = dataset.get("scenarios", [])
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(f"No scenarios found in dataset {dataset_path}")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not run_id:
        timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_id = f"eval-{canary_phase}-{timestamp_str}"
    elif canary_phase not in run_id:
        run_id = f"{run_id}-{canary_phase}"

    scenario_results: List[Dict[str, Any]] = []
    total_groundedness = 0.0
    total_hallucination = 0.0
    total_tool_accuracy = 0.0
    passed_scenarios_count = 0

    for idx, sc in enumerate(scenarios):
        if not isinstance(sc, dict):
            logger.warning("Skipping non-dict scenario entry at index %d", idx)
            continue
        s_id = sc.get("scenario_id", f"SCENARIO-{idx+1:03d}")
        s_name = sc.get("name", "Unnamed Scenario")
        s_category = sc.get("category", "GENERAL")
        ref_context = sc.get("reference_context", "")
        exp_substrings = sc.get("expected_response_substrings") or sc.get("expected_substrings") or []
        forbidden = sc.get("forbidden_hallucinations") or sc.get("forbidden_claims") or sc.get("forbidden") or []
        exp_tools = sc.get("expected_tool_calls") or sc.get("expected_tools") or []

        try:
            # Query agent
            resp_content, actual_tools = query_agent_engine(
                scenario=sc,
                agent_engine_id=agent_engine_id,
                project_id=project_id,
                location=location,
                mock_mode=mock_mode,
            )

            # Compute metrics
            g_score = compute_groundedness_score(resp_content, ref_context, exp_substrings)
            h_score = compute_hallucination_rate(resp_content, ref_context, forbidden)
            t_score = compute_tool_call_accuracy(actual_tools, exp_tools)
        except Exception as eval_err:
            if not mock_mode and isinstance(eval_err, RuntimeError):
                raise
            logger.error("Error evaluating scenario %s: %s", s_id, eval_err)
            g_score, h_score, t_score = 0.0, 1.0, 0.0
            resp_content, actual_tools = f"Evaluation error: {eval_err}", []

        total_groundedness += g_score
        total_hallucination += h_score
        total_tool_accuracy += t_score

        scenario_passed = (
            g_score >= min_groundedness
            and h_score <= max_hallucination_rate
            and t_score >= min_tool_call_accuracy
        )
        if scenario_passed:
            passed_scenarios_count += 1

        resp_str = str(resp_content) if resp_content is not None else ""
        res_entry = {
            "scenario_id": s_id,
            "name": s_name,
            "category": s_category,
            "groundedness_score": g_score,
            "hallucination_score": h_score,
            "tool_call_accuracy": t_score,
            "passed": scenario_passed,
            "response_snippet": resp_str[:120] + ("..." if len(resp_str) > 120 else ""),
            "actual_tool_calls_count": len(actual_tools) if isinstance(actual_tools, list) else 0,
            "expected_tool_calls_count": len(exp_tools) if isinstance(exp_tools, list) else 0,
        }
        scenario_results.append(res_entry)
        logger.info(
            "[%s] %s | G: %.3f | H: %.3f | T: %.3f | %s",
            s_id,
            s_name[:35].ljust(35),
            g_score,
            h_score,
            t_score,
            "PASS" if scenario_passed else "FAIL",
        )

    if not scenario_results:
        raise ValueError(f"No valid scenarios found in dataset {dataset_path}")

    count = len(scenario_results)
    avg_groundedness = round(total_groundedness / count, 4)
    avg_hallucination = round(total_hallucination / count, 4)
    avg_tool_accuracy = round(total_tool_accuracy / count, 4)

    violations: List[str] = []
    if avg_groundedness < min_groundedness:
        violations.append(
            f"Average Groundedness {avg_groundedness:.4f} is below threshold {min_groundedness:.2f}"
        )
    if avg_hallucination > max_hallucination_rate:
        violations.append(
            f"Average Hallucination Rate {avg_hallucination:.4f} exceeds threshold {max_hallucination_rate:.2f}"
        )
    if avg_tool_accuracy < min_tool_call_accuracy:
        violations.append(
            f"Average Tool-Call Accuracy {avg_tool_accuracy:.4f} is below threshold {min_tool_call_accuracy:.2f}"
        )
    if passed_scenarios_count == 0 and count > 0:
        violations.append("Zero scenarios passed evaluation criteria.")

    quality_gate_passed = len(violations) == 0

    scorecard: Dict[str, Any] = {
        "metadata": {
            "timestamp": now_iso,
            "run_id": run_id,
            "canary_phase": canary_phase,
            "agent_engine_id": agent_engine_id,
            "project_id": project_id,
            "location": location,
            "experiment_name": experiment_name,
            "mock_mode": mock_mode,
            "scorer_type": scorer_type,
            "dataset_path": dataset_path,
            "dataset_version": dataset.get("version", "unknown"),
        },
        "thresholds": {
            "min_groundedness": min_groundedness,
            "max_hallucination_rate": max_hallucination_rate,
            "min_tool_call_accuracy": min_tool_call_accuracy,
        },
        "summary": {
            "total_scenarios": count,
            "passed_scenarios": passed_scenarios_count,
            "failed_scenarios": count - passed_scenarios_count,
            "average_groundedness": avg_groundedness,
            "average_hallucination_rate": avg_hallucination,
            "average_tool_call_accuracy": avg_tool_accuracy,
            "quality_gate_passed": quality_gate_passed,
        },
        "violations": violations,
        "scenarios": scenario_results,
    }

    # Log to Vertex AI Experiments
    experiment_metrics = {
        "average_groundedness": avg_groundedness,
        "average_hallucination_rate": avg_hallucination,
        "average_tool_call_accuracy": avg_tool_accuracy,
        "quality_gate_passed": 1.0 if quality_gate_passed else 0.0,
        "passed_scenarios": float(passed_scenarios_count),
    }
    experiment_params = {
        "canary_phase": canary_phase,
        "agent_engine_id": agent_engine_id,
        "total_scenarios": count,
        "mock_mode": str(mock_mode),
        "scorer_type": scorer_type,
    }
    logged = log_experiment_metrics(
        experiment_name=experiment_name,
        run_id=run_id,
        metrics=experiment_metrics,
        params=experiment_params,
        project_id=project_id,
        location=location,
        mock_mode=mock_mode,
    )
    scorecard["metadata"]["vertex_experiments_logged"] = logged

    # 2. Build and publish Vertex AI EvaluationRun resource (linked to Reasoning Engine)
    eval_run_payload = build_evaluation_run_payload(
        agent_engine_id=agent_engine_id,
        run_id=run_id,
        canary_phase=canary_phase,
        metrics={
            "average_groundedness": avg_groundedness,
            "average_hallucination_rate": avg_hallucination,
            "average_tool_call_accuracy": avg_tool_accuracy,
        },
        total_items=count,
        passed_items=passed_scenarios_count,
        quality_gate_passed=quality_gate_passed,
        dataset_version=str(dataset.get("version", "unknown")),
        dataset_path=dataset_path,
        evaluation_experiment_name=experiment_name,
        project_id=project_id,
        location=location,
    )
    eval_run_logged = False
    eval_run_resp = None
    if publish_evaluation_run_enabled:
        eval_run_logged, eval_run_resp = publish_evaluation_run(
            project_id=project_id,
            location=location,
            payload=eval_run_payload,
            mock_mode=mock_mode,
            api_endpoint=api_endpoint,
        )
    else:
        logger.info("EvaluationRun publishing skipped (disabled via configuration)")
    scorecard["metadata"]["vertex_evaluation_run_logged"] = eval_run_logged
    eval_run_resource_name = (
        eval_run_resp["name"]
        if (eval_run_resp and isinstance(eval_run_resp, dict) and "name" in eval_run_resp)
        else None
    )
    scorecard["metadata"]["evaluation_run_resource_name"] = eval_run_resource_name
    if eval_run_resource_name:
        eval_run_payload["name"] = eval_run_resource_name
    scorecard["evaluation_run"] = eval_run_payload

    # Write output scorecard (after experiments logged to ensure disk consistency)
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)
    logger.info("Evaluation scorecard saved to: %s", output_path)

    logger.info("==================== Summary ====================")
    logger.info("Total Scenarios:         %d", count)
    logger.info("Passed Scenarios:        %d", passed_scenarios_count)
    logger.info("Average Groundedness:    %.4f (Threshold >= %.2f)", avg_groundedness, min_groundedness)
    logger.info("Average Hallucination:   %.4f (Threshold <= %.2f)", avg_hallucination, max_hallucination_rate)
    logger.info("Average Tool Accuracy:   %.4f (Threshold >= %.2f)", avg_tool_accuracy, min_tool_call_accuracy)
    logger.info("Quality Gate Passed:     %s", quality_gate_passed)
    if violations:
        logger.error("Violations detected:")
        for v in violations:
            logger.error("  - %s", v)
    logger.info("=================================================")

    return quality_gate_passed, scorecard


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments with fallback to environment variables."""
    parser = argparse.ArgumentParser(
        description="Conductor v3 Production Agent Evaluation Runner"
    )
    parser.add_argument(
        "--dataset",
        default=os.getenv("EVAL_DATASET_PATH", "data/golden_eval_dataset.json"),
        help="Path to golden evaluation dataset JSON",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("EVAL_SCORECARD_PATH", "scorecard.json"),
        help="Path to output evaluation scorecard JSON",
    )
    parser.add_argument(
        "--agent-engine-id",
        default=os.getenv("AGENT_ENGINE_ID", DEFAULT_AGENT_ENGINE_ID),
        help="Vertex AI Reasoning Engine resource path",
    )
    parser.add_argument(
        "--project",
        default=os.getenv("CLOUD_DEPLOY_PROJECT", os.getenv("PROJECT_ID", DEFAULT_PROJECT_ID)),
        help="Google Cloud Project ID",
    )
    parser.add_argument(
        "--location",
        default=os.getenv("CLOUD_DEPLOY_LOCATION", os.getenv("LOCATION", DEFAULT_LOCATION)),
        help="Google Cloud Location / Region",
    )
    parser.add_argument(
        "--experiment-name",
        default=os.getenv("VERTEX_EXPERIMENT_NAME", DEFAULT_EXPERIMENT_NAME),
        help="Vertex AI Experiment name",
    )
    parser.add_argument(
        "--run-id",
        default=os.getenv("CLOUD_DEPLOY_ROLLOUT_ID", os.getenv("EVAL_RUN_ID")),
        help="Unique evaluation run identifier",
    )
    parser.add_argument(
        "--phase",
        default=os.getenv("CANARY_PHASE", "canary-25"),
        help="Canary rollout phase (canary-25, canary-50, stable)",
    )
    def _get_float_env(var_name: str, default_val: float) -> float:
        val = os.getenv(var_name)
        if val is None or not val.strip():
            return default_val
        try:
            f = float(val.strip())
            import math
            if math.isnan(f) or math.isinf(f):
                return default_val
            return max(0.0, min(1.0, f))
        except (ValueError, TypeError):
            return default_val

    def _get_bool_env(var_name: str, default_val: bool) -> bool:
        val = os.getenv(var_name)
        if val is None or not val.strip():
            return default_val
        return val.strip().lower() in ("true", "1", "yes")

    def _parse_threshold_arg(val: Any) -> float:
        try:
            f = float(val)
            import math
            if math.isnan(f) or math.isinf(f):
                raise argparse.ArgumentTypeError(f"Threshold must be a finite number in [0.0, 1.0], got '{val}'")
            if not (0.0 <= f <= 1.0):
                raise argparse.ArgumentTypeError(f"Threshold must be between 0.0 and 1.0, got '{val}'")
            return f
        except (ValueError, TypeError) as exc:
            raise argparse.ArgumentTypeError(f"Invalid threshold value: '{val}'") from exc

    parser.add_argument(
        "--min-groundedness",
        type=_parse_threshold_arg,
        default=_get_float_env("THRESHOLD_GROUNDEDNESS", DEFAULT_MIN_GROUNDEDNESS),
        help="Minimum required groundedness score",
    )
    parser.add_argument(
        "--max-hallucination-rate",
        type=_parse_threshold_arg,
        default=_get_float_env("THRESHOLD_HALLUCINATION_RATE", DEFAULT_MAX_HALLUCINATION_RATE),
        help="Maximum allowed hallucination rate",
    )
    parser.add_argument(
        "--min-tool-call-accuracy",
        type=_parse_threshold_arg,
        default=_get_float_env("THRESHOLD_TOOL_CALL_ACCURACY", DEFAULT_MIN_TOOL_CALL_ACCURACY),
        help="Minimum required tool-call accuracy",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=_get_bool_env("MOCK_AGENT", True),
        help="Run in mock evaluation mode",
    )
    parser.add_argument(
        "--live",
        action="store_false",
        dest="mock",
        help="Query live Vertex AI Agent Engine endpoint",
    )
    parser.add_argument(
        "--scorer",
        default=os.getenv("SCORER_TYPE", "custom"),
        choices=["custom", "rapid", "managed"],
        help="Evaluation scoring engine",
    )
    parser.add_argument(
        "--publish-evaluation-run",
        dest="publish_evaluation_run",
        action="store_true",
        default=_get_bool_env("PUBLISH_EVALUATION_RUN", True),
        help="Publish EvaluationRun resource to Vertex AI Agent Platform",
    )
    parser.add_argument(
        "--no-publish-evaluation-run",
        dest="publish_evaluation_run",
        action="store_false",
        help="Disable publishing EvaluationRun resource",
    )
    parser.add_argument(
        "--api-endpoint",
        default=os.getenv("VERTEX_EVALUATION_ENDPOINT"),
        help="Vertex AI Evaluation API endpoint URL override",
    )
    return parser.parse_args()


def main() -> None:
    """Main CLI entrypoint."""
    args = parse_args()
    try:
        passed, _ = run_evaluation(
            dataset_path=args.dataset,
            output_path=args.output,
            agent_engine_id=args.agent_engine_id,
            project_id=args.project,
            location=args.location,
            experiment_name=args.experiment_name,
            run_id=args.run_id,
            canary_phase=args.phase,
            min_groundedness=args.min_groundedness,
            max_hallucination_rate=args.max_hallucination_rate,
            min_tool_call_accuracy=args.min_tool_call_accuracy,
            mock_mode=args.mock,
            scorer_type=args.scorer,
            publish_evaluation_run_enabled=args.publish_evaluation_run,
            api_endpoint=args.api_endpoint,
        )
        if passed:
            logger.info("[SUCCESS] Production canary evaluation passed all quality gates.")
            sys.exit(0)
        else:
            logger.error("[FAILURE] Production canary evaluation failed one or more quality gates.")
            sys.exit(1)
    except Exception as exc:
        logger.exception("Evaluation runner encountered fatal error: %s", exc)
        sys.exit(2)


if __name__ == "__main__":
    main()
