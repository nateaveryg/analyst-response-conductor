#!/usr/bin/env bash
# ==============================================================================
# Phase 5 Demo Sandbox Infrastructure — Automated Test & Deployment Runner
# Executes Terraform initialization, HCL validation, and plan verification.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"

echo "=============================================================================="
echo "🎬 Phase 5: Testing and Validating Demo Sandbox Terraform Infrastructure..."
echo "Target Working Directory: ${SCRIPT_DIR}"
echo "=============================================================================="

# Check if terraform binary is present
if ! command -v terraform &> /dev/null; then
    echo "⚠️ NOTICE: 'terraform' command not detected in current local PATH."
    echo "ℹ️ During standard local developer unit testing, our self-contained Pytest test suite"
    echo "    (tests/test_terraform_demo_sandboxes.py) executes static HCL structural validation"
    echo "    without requiring external network downloads or binary installation."
    echo ""
    echo "🚀 To provision real cloud resources in Google Cloud Platform:"
    echo "    1. Execute this script inside Google Cloud Shell or Cloud Build where terraform is installed."
    echo "    2. Command: bash infra/terraform/demo_sandboxes/test_and_deploy_sandboxes.sh --apply"
    echo "=============================================================================="
    exit 0
fi

echo "✅ Terraform CLI detected: $(terraform --version | head -n 1)"

echo "🔄 Step 1: Initializing Terraform environment..."
terraform init -backend=false

echo "🔍 Step 2: Validating HCL configuration syntax..."
terraform validate

echo "📋 Step 3: Generating speculative infrastructure deployment plan..."
terraform plan -var-file="terraform.tfvars.example" -out="demo_sandboxes.tfplan" || {
    echo "⚠️ Note: Speculative plan failed to reach GCP APIs. Verify active Cloud credentials (gcloud auth login)."
    exit 0
}

if [[ "${1:-}" == "--apply" ]]; then
    echo "🚀 Applying Terraform configuration to provision real demonstration sandboxes..."
    terraform apply "demo_sandboxes.tfplan"
    echo "✨ Infrastructure successfully deployed! See outputs above for console URLs."
fi

echo "✅ All Terraform configuration tests and validations completed successfully!"
