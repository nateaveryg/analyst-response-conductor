#!/usr/bin/env python3
"""
Deep Adversarial Stress and Differential Fuzzing Suite
Target: https://conductor-v3-dev-4izasuhqpq-uc.a.run.app
Author: challenger_remediation_dev
"""

import concurrent.futures
import json
import os
import sys
import time
import requests

TARGET_URL = (
    os.getenv("CLOUD_RUN_SERVICE_URL")
    or os.getenv("TARGET_URL")
    or "https://conductor-v3-dev-4izasuhqpq-uc.a.run.app"
).rstrip("/")

SESSION = requests.Session()
TIMEOUT = 15

def test_novel_dlp_and_pii_vectors():
    print("=" * 80)
    print("CHALLENGER DEEP FUZZ 1: Novel DLP, Suffix, PII & Boundary Permutations")
    print(f"Target: {TARGET_URL}")
    print("=" * 80)

    # Test cases: (input_phrase, should_contain_redaction, forbidden_substrings, description)
    cases = [
        # Decimal percentages
        ("partner discount: 12.34%", True, [": 12.34%", "= 12.34%", "12.34%"], "Decimal percentage in partner discount"),
        ("internal margin = 88.5%", True, [": 88.5%", "= 88.5%", "88.5%"], "Decimal percentage in internal margin"),
        ("confidential discount: 0.5%", True, ["0.5%"], "Small decimal discount"),
        ("confidential discount: 99.99%", True, ["99.99%"], "Large decimal discount"),
        
        # Multiple tokens in single message
        ("partner discount: 25% and internal margin: 60%", True, ["25%", "60%"], "Multi-target rate in single sentence"),
        ("partner discount: 30%, internal margin: 50%, ssn: 987-65-4321", True, ["30%", "50%", "987-65-4321"], "Triple token (discount + margin + SSN)"),

        # Currency rates
        ("unreleased pricing: $123.45/month", True, ["$123.45/month"], "Decimal monthly subscription pricing"),
        ("partner pricing: $75/hour", True, ["$75/hour"], "Hourly pricing format"),
        ("custom seller deal", True, ["custom seller deal"], "Custom seller deal keyword"),

        # Punctuation variations
        ("partner discount: 45%.", True, ["45%."], "Period after percentage"),
        ("partner discount: 45%,", True, ["45%,"], "Comma after percentage"),
        ("partner discount: 45%;", True, ["45%;"], "Semicolon after percentage"),
        ("partner discount: ( 45% )", True, ["( 45% )", "45%"], "Spaces inside parentheses"),

        # Email PII distinctions
        ("contact analyst at external-partner@microsoft.com", True, ["external-partner@microsoft.com"], "Non-Google external email redaction"),
        ("contact analyst at team-lead@google.com", False, [], "Google corp email allowance (@google.com)"),

        # Negative checks: Normal enterprise text should NOT be over-redacted
        ("Our partner ecosystem is expanding rapidly across regions.", False, ["[CONFIDENTIAL_COMMERCIAL_RATE]"], "Non-sensitive mention of partner"),
        ("The overall profit margin increased this quarter.", False, ["[CONFIDENTIAL_COMMERCIAL_RATE]"], "Non-sensitive mention of profit margin"),
        ("We offer a general discount for educational institutions.", False, ["[CONFIDENTIAL_COMMERCIAL_RATE]"], "Non-sensitive mention of discount"),
    ]

    passed_count = 0
    failures = []

    for phrase, expect_redaction, forbidden, desc in cases:
        prompt = f"Audit test: {phrase}."
        payload = {"message": prompt, "action_id": "general_query"}
        try:
            r = SESSION.post(f"{TARGET_URL}/api/v1/a2ui/chat", json=payload, timeout=TIMEOUT)
            if r.status_code != 200:
                failures.append(f"HTTP {r.status_code} on '{desc}'")
                print(f"❌ [HTTP {r.status_code}] {desc}")
                continue
            resp_text = r.json().get("response_text", "")
            
            leak_detected = False
            for f in forbidden:
                if f in resp_text:
                    leak_detected = True
                    break
            
            redaction_present = "[CONFIDENTIAL_COMMERCIAL_RATE]" in resp_text or "[REDACTED_PII]" in resp_text or "[REDACTED_SSN]" in resp_text
            
            if expect_redaction and (not redaction_present or leak_detected):
                print(f"🚨 [FAIL] {desc}")
                print(f"     Input: '{phrase}'")
                print(f"     Output: '{resp_text}'")
                print(f"     Redaction present: {redaction_present}, Leak detected: {leak_detected}")
                failures.append(f"DLP failed on '{desc}'")
            elif not expect_redaction and leak_detected:
                print(f"🚨 [OVER-REDACTION/LEAK] {desc}")
                print(f"     Input: '{phrase}'")
                print(f"     Output: '{resp_text}'")
                failures.append(f"Over-redaction or leak on '{desc}'")
            else:
                passed_count += 1
                icon = "🛡️" if expect_redaction else "✅"
                print(f"{icon} [PASS] {desc}")
                print(f"     Input: '{phrase}'")
                print(f"     Output snippet: '{resp_text[:120]}...'")

        except Exception as e:
            print(f"❌ [ERROR] {desc}: {e}")
            failures.append(f"Exception on '{desc}': {e}")

    print("-" * 80)
    print(f"Deep Fuzz DLP Results: {passed_count}/{len(cases)} Passed")
    print("-" * 80)
    return len(failures) == 0, failures


def test_mixed_adversarial_burst():
    print("\n" + "=" * 80)
    print("CHALLENGER DEEP FUZZ 2: Mixed High-Concurrency Adversarial Storm")
    print(f"Target: {TARGET_URL}")
    print("=" * 80)

    # Concurrently fire 80 requests interleaving DLP queries, readiness, health, invalid inputs, and exports
    tasks = [
        {"type": "health", "url": f"{TARGET_URL}/health", "method": "GET"},
        {"type": "ready", "url": f"{TARGET_URL}/ready", "method": "GET"},
        {"type": "chat_dlp", "url": f"{TARGET_URL}/api/v1/a2ui/chat", "method": "POST", "payload": {"message": "audit partner discount: 45%", "action_id": "general_query"}},
        {"type": "chat_xss", "url": f"{TARGET_URL}/api/v1/a2ui/chat", "method": "POST", "payload": {"message": "<script>alert(1)</script>", "action_id": "general_query"}},
        {"type": "export", "url": f"{TARGET_URL}/api/v1/export/workback-schedule", "method": "GET"},
        {"type": "bad_uuid", "url": f"{TARGET_URL}/api/v1/artifacts/invalid-uuid-123", "method": "GET"},
        {"type": "not_found", "url": f"{TARGET_URL}/api/v1/nonexistent", "method": "GET"},
    ]

    total_requests = 140  # 20 repetitions of all 7 types
    all_reqs = []
    for i in range(20):
        all_reqs.extend(tasks)

    print(f"Blasting {total_requests} interleaved requests across 35 worker threads...")
    start_time = time.time()
    status_codes = {}
    crashes_500 = 0

    def worker(item):
        nonlocal crashes_500
        try:
            if item["method"] == "GET":
                r = SESSION.get(item["url"], timeout=TIMEOUT)
            else:
                r = SESSION.post(item["url"], json=item.get("payload", {}), timeout=TIMEOUT)
            code = r.status_code
            if code >= 500:
                crashes_500 += 1
            return code
        except Exception as ex:
            return 599

    with concurrent.futures.ThreadPoolExecutor(max_workers=35) as executor:
        futures = [executor.submit(worker, item) for item in all_reqs]
        for f in concurrent.futures.as_completed(futures):
            code = f.result()
            status_codes[code] = status_codes.get(code, 0) + 1

    elapsed = time.time() - start_time
    print(f"Completed {total_requests} requests in {elapsed:.2f} seconds.")
    print(f"Status breakdown: {status_codes}")
    print(f"Unhandled 500 crashes: {crashes_500}")

    success = crashes_500 == 0
    print(f"Result: {'✅ PASSED (0 crashes)' if success else '🚨 FAILED (Crashes observed)'}")
    return success, crashes_500


if __name__ == "__main__":
    dlp_ok, dlp_errs = test_novel_dlp_and_pii_vectors()
    burst_ok, crashes = test_mixed_adversarial_burst()

    if dlp_ok and burst_ok:
        print("\n🏆 ALL NOVEL DEEP FUZZ AND BURST CHALLENGES PASSED (100% DEFENSE RATE)")
        sys.exit(0)
    else:
        print(f"\n🚨 FAILURES DETECTED: dlp_errs={dlp_errs}, crashes={crashes}")
        sys.exit(1)
