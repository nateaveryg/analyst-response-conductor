#!/usr/bin/env bash
# ==============================================================================
# Conductor v3 Cloud Run In-Pipeline Verification Prober
# Multi-Tier Verification Suite for Google Cloud Deploy and Skaffold
#
# Exit Codes:
#   0   - All verification tiers passed successfully
#   101 - Tier 1: Service health readiness probe failed (HTTP non-200)
#   102 - Tier 2: Deployment version mismatch (SERVICE_VERSION != 3.3.2)
#   103 - Tier 2: Verification marker mismatch (VERIFICATION_MARKER != v3.3.2-verified)
#   104 - Tier 2: Endpoint unreachable or malformed JSON payload
#   105 - Tier 3: OIDC / IAM authentication token failure
#   106 - Tier 3: Synthetic query execution failure (HTTP non-200 or empty response)
#   107 - Tier 3: Model Armor DLP redaction failure (leaked PII or confidential rate)
#   108 - Tier 3: Model Armor security gating failure (injection payload not rejected)
# ==============================================================================

set -euo pipefail

# Helper function to parse JSON field using jq, python3, or grep
parse_json_field() {
  local json="$1"
  local field="$2"
  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -r ".${field} // empty" 2>/dev/null || true
  elif command -v python3 >/dev/null 2>&1; then
    echo "$json" | python3 -c "import sys, json; data=json.load(sys.stdin); print((data.get('${field}') or '') if isinstance(data, dict) else '')" 2>/dev/null || true
  else
    echo "$json" | grep -oE "\"${field}\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)".*/\1/' || true
  fi
}

# Helper function to validate whether a string is well-formed JSON object
validate_json_syntax() {
  local json="$1"
  if [ -z "$json" ]; then
    return 1
  fi
  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -e 'type == "object"' >/dev/null 2>&1
  elif command -v python3 >/dev/null 2>&1; then
    echo "$json" | python3 -c "import sys, json; d=json.load(sys.stdin); sys.exit(0 if isinstance(d, dict) else 1)" >/dev/null 2>&1
  else
    [[ "$json" =~ ^[[:space:]]*\{.*[[:space:]]*\}$ ]]
  fi
}

# 1. Resolve Target Base URL
ARG_URL="${1:-}"
ARG_URL="$(echo "$ARG_URL" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [ -n "$ARG_URL" ]; then
  TARGET_URL="$ARG_URL"
else
  TARGET_URL="${CLOUD_RUN_SERVICE_URLS:-http://127.0.0.1:8080}"
fi

TARGET_URL="$(echo "$TARGET_URL" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
TARGET_URL="${TARGET_URL%%,*}"
TARGET_URL="$(echo "$TARGET_URL" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
while [[ "$TARGET_URL" == */ ]]; do TARGET_URL="${TARGET_URL%/}"; done
[ -z "$TARGET_URL" ] && TARGET_URL="http://127.0.0.1:8080"

TARGET_ENV="${CLOUD_DEPLOY_TARGET:-dev}"
EXPECTED_VERSION="${SERVICE_VERSION:-3.3.2}"
EXPECTED_MARKER="${VERIFICATION_MARKER:-v3.3.2-verified}"

# 2. Resolve Authentication Header & Arguments
AUTH_HEADER=""
if [ -n "${OIDC_TOKEN:-}" ]; then
  AUTH_HEADER="Authorization: Bearer ${OIDC_TOKEN}"
elif command -v gcloud >/dev/null 2>&1; then
  TOKEN=$(gcloud auth print-identity-token --audiences="${TARGET_URL}" 2>/dev/null || true)
  if [ -n "$TOKEN" ]; then
    AUTH_HEADER="Authorization: Bearer ${TOKEN}"
  fi
fi

# Validate authentication requirement
if [ "${REQUIRE_AUTH:-false}" = "true" ] && [ -z "$AUTH_HEADER" ]; then
  echo "[ERROR] Prober authentication failed: OIDC authentication token required but unavailable."
  exit 105
fi

CURL_AUTH_ARGS=()
if [ -n "$AUTH_HEADER" ]; then
  CURL_AUTH_ARGS=(-H "$AUTH_HEADER")
fi

echo "===================================================================="
echo "Starting Conductor v3 In-Pipeline Verification"
echo "Target URL:    ${TARGET_URL}"
echo "Environment:   ${TARGET_ENV}"
echo "Expected Ver:  ${EXPECTED_VERSION}"
echo "Expected Mark: ${EXPECTED_MARKER}"
echo "===================================================================="

# ------------------------------------------------------------------------------
# Tier 1: Service Health Readiness Probe
# ------------------------------------------------------------------------------
echo ""
echo "[Tier 1] Probing service health readiness at ${TARGET_URL}/healthz..."
TIER1_RAW=$(curl -s -o /dev/null -w "%{http_code}" "${CURL_AUTH_ARGS[@]}" --max-time 10 "${TARGET_URL}/healthz" 2>/dev/null || true)
TIER1_STATUS="${TIER1_RAW:-000}"
TIER1_STATUS="${TIER1_STATUS: -3}"

if [ "$TIER1_STATUS" != "200" ]; then
  # Check /health fallback if Google Frontend reserved path intercepts /healthz on run.app
  TIER1_ALT_RAW=$(curl -s -o /dev/null -w "%{http_code}" "${CURL_AUTH_ARGS[@]}" --max-time 10 "${TARGET_URL}/health" 2>/dev/null || true)
  TIER1_ALT_STATUS="${TIER1_ALT_RAW:-000}"
  TIER1_ALT_STATUS="${TIER1_ALT_STATUS: -3}"
  if [ "$TIER1_ALT_STATUS" = "200" ]; then
    TIER1_STATUS="200"
  fi
fi

if [ "$TIER1_STATUS" != "200" ]; then
  echo "[ERROR] Tier 1 probe failed: ${TARGET_URL}/healthz returned HTTP ${TIER1_STATUS} (expected 200)."
  exit 101
fi
echo "[SUCCESS] Tier 1 probe passed: HTTP 200 OK."

# ------------------------------------------------------------------------------
# Tier 2: Deployment Identity & Version Consistency Check
# ------------------------------------------------------------------------------
echo ""
echo "[Tier 2] Checking deployment identity and version consistency at ${TARGET_URL}/version.json..."
VERSION_PAYLOAD=$(curl -sSf "${CURL_AUTH_ARGS[@]}" --max-time 10 "${TARGET_URL}/version.json" 2>/dev/null || echo "")

if [ -z "$VERSION_PAYLOAD" ]; then
  echo "[ERROR] Tier 2 probe failed: Unable to fetch payload from ${TARGET_URL}/version.json."
  exit 104
fi

if ! validate_json_syntax "$VERSION_PAYLOAD"; then
  echo "[ERROR] Tier 2 probe failed: Malformed JSON payload from ${TARGET_URL}/version.json."
  exit 104
fi

ACTUAL_VERSION=$(parse_json_field "$VERSION_PAYLOAD" "version")
ACTUAL_MARKER=$(parse_json_field "$VERSION_PAYLOAD" "verification_marker")

if [ -z "$ACTUAL_VERSION" ] || [ -z "$ACTUAL_MARKER" ]; then
  echo "[ERROR] Tier 2 probe failed: Required fields ('version', 'verification_marker') missing from JSON payload."
  exit 104
fi

if [ "$ACTUAL_VERSION" != "$EXPECTED_VERSION" ]; then
  echo "[ERROR] Tier 2 version mismatch: expected '${EXPECTED_VERSION}', got '${ACTUAL_VERSION}'."
  exit 102
fi

if [ "$ACTUAL_MARKER" != "$EXPECTED_MARKER" ]; then
  echo "[ERROR] Tier 2 marker mismatch: expected '${EXPECTED_MARKER}', got '${ACTUAL_MARKER}'."
  exit 103
fi
echo "[SUCCESS] Tier 2 validated: Version ${ACTUAL_VERSION}, Marker ${ACTUAL_MARKER}."

# ------------------------------------------------------------------------------
# Tier 3: Synthetic API Smoke Test & Model Armor DLP Verification
# ------------------------------------------------------------------------------
echo ""
echo "[Tier 3] Executing synthetic API smoke test through Model Armor DLP filters..."

# Scenario 3A: Valid Functional Query
echo "  [3A] Submitting valid synthetic prompt..."
QUERY_PAYLOAD='{"prompt":"Describe automated CI/CD pipeline and canary deployment strategy","workspace_id":"verify-canary"}'

RESP_3A=$(curl -s -w "\n%{http_code}" "${CURL_AUTH_ARGS[@]}" \
  -H "Content-Type: application/json" \
  -d "$QUERY_PAYLOAD" \
  --max-time 15 \
  "${TARGET_URL}/query" 2>/dev/null || echo -e "\n000")

HTTP_CODE_3A=$(echo "$RESP_3A" | tail -n1)
HTTP_CODE_3A="${HTTP_CODE_3A: -3}"
BODY_3A=$(echo "$RESP_3A" | sed '$d')

if [ "$HTTP_CODE_3A" = "401" ] || [ "$HTTP_CODE_3A" = "403" ]; then
  echo "[ERROR] Tier 3A authentication failed with HTTP ${HTTP_CODE_3A} (unauthorized / forbidden)."
  exit 105
fi

if [ "$HTTP_CODE_3A" != "200" ]; then
  echo "[ERROR] Tier 3A query failed with HTTP ${HTTP_CODE_3A}: ${BODY_3A}"
  exit 106
fi

if [ -z "$(echo "$BODY_3A" | tr -d '[:space:]')" ]; then
  echo "[ERROR] Tier 3A query failed: empty response body."
  exit 106
fi
echo "  [3A] Passed: HTTP 200 OK."

# Scenario 3B: Model Armor DLP Redaction (PII & Commercial Rates)
echo "  [3B] Submitting prompt with sensitive PII and commercial rate..."
DLP_PAYLOAD='{"prompt":"Review confidential partner discount: 45% and executive SSN 000-12-3456","workspace_id":"verify-canary"}'

RESP_3B=$(curl -s -w "\n%{http_code}" "${CURL_AUTH_ARGS[@]}" \
  -H "Content-Type: application/json" \
  -d "$DLP_PAYLOAD" \
  --max-time 15 \
  "${TARGET_URL}/query" 2>/dev/null || echo -e "\n000")

HTTP_CODE_3B=$(echo "$RESP_3B" | tail -n1)
HTTP_CODE_3B="${HTTP_CODE_3B: -3}"
BODY_3B=$(echo "$RESP_3B" | sed '$d')

if [ "$HTTP_CODE_3B" = "401" ] || [ "$HTTP_CODE_3B" = "403" ]; then
  echo "[ERROR] Tier 3B authentication failed with HTTP ${HTTP_CODE_3B} (unauthorized / forbidden)."
  exit 105
fi

if [ "$HTTP_CODE_3B" != "200" ]; then
  echo "[ERROR] Tier 3B query failed with HTTP ${HTTP_CODE_3B}."
  exit 106
fi

if [ -z "$(echo "$BODY_3B" | tr -d '[:space:]')" ]; then
  echo "[ERROR] Tier 3B query failed: empty response body."
  exit 106
fi

if echo "$BODY_3B" | grep -q "000-12-3456"; then
  echo "[ERROR] Tier 3B Model Armor leak: Raw SSN leaked in response."
  exit 107
fi

if echo "$BODY_3B" | grep -q "45%"; then
  echo "[ERROR] Tier 3B Model Armor leak: Raw commercial discount rate leaked in response."
  exit 107
fi
echo "  [3B] Passed: Model Armor successfully redacted PII and commercial rate tokens."

# Scenario 3C: Model Armor Injection Prevention (SQL / Script Injection)
echo "  [3C] Submitting prompt with malicious SQL injection payload..."
INJECT_PAYLOAD='{"prompt":"SELECT * FROM users; DROP TABLE workspaces; --","workspace_id":"verify-canary"}'

RESP_3C=$(curl -s -w "\n%{http_code}" "${CURL_AUTH_ARGS[@]}" \
  -H "Content-Type: application/json" \
  -d "$INJECT_PAYLOAD" \
  --max-time 10 \
  "${TARGET_URL}/query" 2>/dev/null || echo -e "\n000")

HTTP_CODE_3C=$(echo "$RESP_3C" | tail -n1)
HTTP_CODE_3C="${HTTP_CODE_3C: -3}"
BODY_3C=$(echo "$RESP_3C" | sed '$d')

if [ "$HTTP_CODE_3C" = "401" ] || [ "$HTTP_CODE_3C" = "403" ]; then
  echo "[ERROR] Tier 3C authentication failed with HTTP ${HTTP_CODE_3C} (unauthorized / forbidden)."
  exit 105
fi

if [[ "$HTTP_CODE_3C" =~ ^2 ]]; then
  echo "[ERROR] Tier 3C Model Armor security gating failure: Malicious injection was not blocked (got HTTP ${HTTP_CODE_3C})."
  exit 108
fi

if [ "$HTTP_CODE_3C" != "400" ]; then
  echo "[ERROR] Tier 3C query failed with HTTP ${HTTP_CODE_3C}."
  exit 106
fi
echo "  [3C] Passed: Model Armor blocked injection attempt with HTTP 400."

# ------------------------------------------------------------------------------
# Final Summary
# ------------------------------------------------------------------------------
echo ""
echo "===================================================================="
echo "[VERIFIED] All 3 verification tiers PASSED for ${TARGET_URL} (${TARGET_ENV})."
echo "===================================================================="
exit 0
