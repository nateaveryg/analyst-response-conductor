# E2E Test Infra: Conductor v3 Cloud Run Verification

## Test Philosophy
- Opaque-box, requirement-driven verification against live Google Cloud Run endpoints.
- Validates Model Armor DLP security filtering, 12 adversarial attack categories, 10 error resilience edge cases, and full 7-phase E2E functional lifecycle.

## Feature Inventory & Test Mapping
| # | Feature | Test Suite | Assertions |
|---|---------|------------|------------|
| 1 | Model Armor DLP Masking | `test_live_cloud_run_antagonistic_agent.py` Category 2 | Confidential discount 45%, margins -> `[CONFIDENTIAL_COMMERCIAL_RATE]`, SSN -> `[REDACTED_SSN]` |
| 2 | Prompt Injection Defense | `test_live_cloud_run_antagonistic_agent.py` Category 1 | System prompt protection, zero unauthorized disclosure |
| 3 | XSS & SVG Injection | `test_live_cloud_run_antagonistic_agent.py` Category 3 | Neutralized script tags and SVG handlers |
| 4 | SQLi & Path Traversal | `test_live_cloud_run_antagonistic_agent.py` Category 4 | Blocked SQL syntax and traversal payloads |
| 5 | Prototype Pollution | `test_live_cloud_run_antagonistic_agent.py` Category 5 | Safe JSON handling, no prototype pollution |
| 6 | Multi-Tenancy Isolation | `test_live_cloud_run_antagonistic_agent.py` Category 6 | Strict workspace boundary enforcement |
| 7 | Journey Step Chaos | `test_live_cloud_run_antagonistic_agent.py` Category 7 | Graceful handling of out-of-order phase triggers |
| 8 | Mega-Payload Fuzzing | `test_live_cloud_run_antagonistic_agent.py` Category 8 | >128KB payload size limits handled without OOM/crashes |
| 9 | Corrupted JSON Fuzzing | `test_live_cloud_run_antagonistic_agent.py` Category 9 | Malformed syntax rejected with 4xx, 0 panics |
| 10 | HTTP Verb Tampering | `test_live_cloud_run_antagonistic_agent.py` Category 10 | Restricted verbs rejected with 405 Method Not Allowed |
| 11 | Concurrent Burst Fuzzing | `test_live_cloud_run_antagonistic_agent.py` Category 11 | 15-thread concurrent load without 500 crashes |
| 12 | Admin Reconnaissance | `test_live_cloud_run_antagonistic_agent.py` Category 12 | Hidden routes return 404/403, no leakage |
| 13 | Error Resilience (10 scenarios) | `test_live_cloud_run_error_scenarios.py` | 0 unhandled HTTP 500 crashes |
| 14 | E2E Production Lifecycle (7 phases) | `test_live_cloud_run_full_e2e.py` | Phases 1–7 complete successfully |

## Test Architecture
- Test runners:
  - `python3 test_live_cloud_run_antagonistic_agent.py`
  - `python3 test_live_cloud_run_error_scenarios.py`
  - `python3 test_live_cloud_run_full_e2e.py`
- Target Endpoint Configuration:
  - `CLOUD_RUN_SERVICE_URL` or `TARGET_URL` env vars pointing to `conductor-v3-dev`, `conductor-v3-staging`, `conductor-v3-prod`
  - `CLOUD_RUN_AUTH_TOKEN` (optional for public/IAP endpoints)
- Success criteria:
  - Adversarial red-team: 12/12 (100%) passed
  - Error resilience: 10/10 passed, 0 HTTP 500 errors
  - Full E2E: 7/7 phases passed
