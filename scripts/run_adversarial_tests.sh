#!/usr/bin/env bash
# ==============================================================================
# Analyst Response Agent (ARA) - Adversarial & UI Resilience Test Runner
# ==============================================================================
# Ensures adversarial and UI resilience tests are executed and validated.
# Exit code 0 indicates all adversarial attack vectors were safely neutralized.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "========================================================================"
echo "🛡️  Running Analyst Response Agent (ARA) Adversarial Test Suite"
echo "========================================================================"

# Determine Python / pytest binary
if [ -f ".venv/bin/pytest" ]; then
    PYTEST_BIN=".venv/bin/pytest"
elif command -v pytest &> /dev/null; then
    PYTEST_BIN="pytest"
else
    echo "❌ Error: pytest not found in .venv or PATH."
    exit 1
fi

echo "📍 Executing: ${PYTEST_BIN} tests/test_ui_adversarial_agent.py -v"
${PYTEST_BIN} tests/test_ui_adversarial_agent.py -v

echo ""
echo "📍 Executing Full Regression Test Suite (including UI & Tenancy):"
${PYTEST_BIN} tests/ -v

echo ""
echo "========================================================================"
echo "✅ All adversarial vectors neutralized and regression tests passed (100%)"
echo "========================================================================"
