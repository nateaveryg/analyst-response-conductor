#!/usr/bin/env python3
"""
Differential Correctness Fuzzer for resolve_target_resource.

Implements the three-component pattern from the solution-stress-testing playbook:
1. Generator: Generates 1,000+ randomized inputs, boundary cases, corrupted payloads.
2. Oracle: Simple, obviously correct independent reference specification.
3. Harness: Runs both implementations, compares outputs, guarantees equivalence.
"""

import json
import os
import random
import string
import tempfile
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from infra.agent_engine.verify_agent_engine import resolve_target_resource
except ImportError:
    from infra.agent_engine.archive_python.verify_agent_engine import resolve_target_resource


def reference_oracle(resource_arg, env_tier, file_data):
    """
    Independent reference specification for target resource resolution.
    """
    # 1. Explicit CLI argument takes immediate precedence
    if resource_arg:
        return resource_arg

    # 2. If no file data or corrupted non-dict payload -> fallback None
    if not isinstance(file_data, dict):
        return None

    # Step 1 in implementation:
    # tier_resource = data.get("tiers", {}).get(env_tier)
    # Note: if "tiers" is present with non-dict/None value, data.get("tiers", {}) returns that non-dict,
    # and .get() raises AttributeError, caught by except block -> returns None.
    tiers_val = file_data.get("tiers", {})
    if tiers_val is not None and not isinstance(tiers_val, dict):
        return None
    if tiers_val is None:
        return None

    tier_val = tiers_val.get(env_tier)
    if tier_val:
        return tier_val

    # Step 2 in implementation:
    # Single-tier fallback: env matches and resource_name is non-empty
    if file_data.get("env") == env_tier and file_data.get("resource_name"):
        return file_data.get("resource_name")

    return None


def random_string(length=12):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_fuzz_case(seed):
    random.seed(seed)

    # Pick tier
    tiers = ["dev", "staging", "prod", "qa", "canary", "", "DEV", "PROD"]
    env_tier = random.choice(tiers)

    # Decide CLI resource_name argument
    cli_choice = random.random()
    if cli_choice < 0.2:
        resource_arg = f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}"
    elif cli_choice < 0.3:
        resource_arg = ""
    else:
        resource_arg = None

    # Decide file situation
    file_mode = random.choice([
        "missing",
        "corrupted_syntax",
        "primitive_type",
        "corrupted_tiers",
        "valid_multi_tier",
        "valid_single_tier",
        "mismatched_single_tier",
        "empty_dict",
    ])

    raw_file_content = None
    expected_data_obj = None

    if file_mode == "missing":
        file_path = f"/tmp/fuzz_missing_{random_string(8)}.json"
        return resource_arg, env_tier, file_path, None

    elif file_mode == "corrupted_syntax":
        raw_file_content = '{"status": "OPERATIONAL", ' + random_string(10)
        expected_data_obj = None

    elif file_mode == "primitive_type":
        val = random.choice([123, True, False, None, "string", [1, 2, 3]])
        raw_file_content = json.dumps(val)
        expected_data_obj = val

    elif file_mode == "corrupted_tiers":
        obj = {
            "tiers": random.choice(["not_a_dict", [1, 2], 42, None]),
            "resource_name": f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}",
            "env": random.choice(["dev", "staging", "prod"]),
        }
        raw_file_content = json.dumps(obj)
        expected_data_obj = obj

    elif file_mode == "valid_multi_tier":
        obj = {
            "status": "OPERATIONAL",
            "tiers": {
                "dev": f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}",
                "staging": f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}",
                "prod": f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}",
            },
            "resource_name": f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}",
            "env": random.choice(["dev", "staging", "prod"]),
        }
        raw_file_content = json.dumps(obj)
        expected_data_obj = obj

    elif file_mode == "valid_single_tier":
        target_env = random.choice(["dev", "staging", "prod"])
        obj = {
            "resource_name": f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}",
            "env": target_env,
        }
        raw_file_content = json.dumps(obj)
        expected_data_obj = obj

    elif file_mode == "mismatched_single_tier":
        obj = {
            "resource_name": f"projects/test/locations/us-central1/reasoningEngines/{random_string(19)}",
            "env": "prod",
        }
        raw_file_content = json.dumps(obj)
        expected_data_obj = obj

    elif file_mode == "empty_dict":
        obj = {}
        raw_file_content = json.dumps(obj)
        expected_data_obj = obj

    # Write to a temporary file
    tmp = tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json")
    tmp.write(raw_file_content)
    tmp.flush()
    tmp.close()

    return resource_arg, env_tier, tmp.name, expected_data_obj


def main():
    print("=== Differential Correctness Fuzzing: resolve_target_resource ===")
    num_iterations = 1000
    mismatches = 0

    for i in range(num_iterations):
        resource_arg, env_tier, file_path, expected_data_obj = generate_fuzz_case(seed=i + 10000)
        try:
            expected = reference_oracle(resource_arg, env_tier, expected_data_obj)
            actual = resolve_target_resource(resource_arg, env_tier, file_path)

            if expected != actual:
                print(f"FAILED on iteration {i}:")
                print(f"  resource_arg={resource_arg!r}")
                print(f"  env_tier={env_tier!r}")
                print(f"  file_path={file_path}")
                print(f"  expected_data_obj={expected_data_obj}")
                print(f"  EXPECTED: {expected!r}")
                print(f"  ACTUAL:   {actual!r}")
                mismatches += 1
                break
        finally:
            if os.path.exists(file_path) and "fuzz_missing" not in file_path:
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    if mismatches == 0:
        print(f"SUCCESS: Passed {num_iterations} differential fuzzing iterations with zero mismatches!")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
