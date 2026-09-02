#!/usr/bin/env bash
# deploy_cloud_run_v3.sh
# Automated build & deployment script for The Conductor v3 (Go Microservice) on Google Cloud Run
# Supports both Google Cloud Deploy (Dev2Prod canary pipeline) and Direct Cloud Run deployment via Artifact Registry.

set -euo pipefail

# Auto-configure ADC access token for gcloud CLI when running on developer Cloudtop / workstation environments
if [ -z "${CLOUDSDK_AUTH_ACCESS_TOKEN:-}" ] && command -v gcloud >/dev/null 2>&1; then
    TOKEN="$(gcloud auth application-default print-access-token 2>/dev/null || true)"
    if [ -n "$TOKEN" ]; then
        export CLOUDSDK_AUTH_ACCESS_TOKEN="$TOKEN"
    fi
fi

# Configuration Environment Variables (Override via environment or replace defaults)
: "${VERTEX_AI_PROJECT:=riccardo-blog-test-v1}"
: "${VERTEX_AI_MODEL:=gemini-3.5-flash}"
: "${REGION:=us-central1}"
: "${REPO_NAME:=conductor-repo}"
: "${SERVICE_NAME:=conductor-v3}"
: "${CLOUD_SQL_INSTANCE:=genai-rag-db-859a1005}"
: "${CLOUD_SQL_CONNECTION_NAME:=${VERTEX_AI_PROJECT}:${REGION}:${CLOUD_SQL_INSTANCE}}"
: "${SERVICE_ACCOUNT_EMAIL:=conductor-agent@${VERTEX_AI_PROJECT}.iam.gserviceaccount.com}"
: "${ENVIRONMENT:=production}"
: "${DEPLOY_METHOD:=direct}"  # 'direct' or 'cloud-deploy'

# Compute immutable image tags
GIT_TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
IMAGE_TAG="${REGION}-docker.pkg.dev/${VERTEX_AI_PROJECT}/${REPO_NAME}/${SERVICE_NAME}:${GIT_TAG}"
LATEST_TAG="${REGION}-docker.pkg.dev/${VERTEX_AI_PROJECT}/${REPO_NAME}/${SERVICE_NAME}:latest"

echo "=========================================================================="
echo "Google Cloud Conductor v3 Dev2Prod Build"
echo "Project:        ${VERTEX_AI_PROJECT}"
echo "Region:         ${REGION}"
echo "Repository:     ${REPO_NAME}"
echo "Service:        ${SERVICE_NAME}"
echo "Image Tag:      ${IMAGE_TAG}"
echo "Deploy Method:  ${DEPLOY_METHOD}"
echo "=========================================================================="

# Ensure Artifact Registry repository exists
gcloud artifacts repositories describe "${REPO_NAME}" \
    --project="${VERTEX_AI_PROJECT}" \
    --location="${REGION}" >/dev/null 2>&1 || \
gcloud artifacts repositories create "${REPO_NAME}" \
    --project="${VERTEX_AI_PROJECT}" \
    --location="${REGION}" \
    --repository-format=docker \
    --description="Docker repository for Conductor v3 Go distroless images" \
    --quiet

# Execute Cloud Build using Dockerfile.v3
echo "Building and pushing Conductor v3 container image via Google Cloud Build..."
gcloud builds submit \
    --project="${VERTEX_AI_PROJECT}" \
    --tag="${IMAGE_TAG}" \
    --substitutions="_DOCKERFILE=Dockerfile.v3" \
    .

# Also tag as latest in Artifact Registry
gcloud artifacts docker tags add "${IMAGE_TAG}" "${LATEST_TAG}" --project="${VERTEX_AI_PROJECT}" --quiet 2>/dev/null || true

if [ "${DEPLOY_METHOD}" = "cloud-deploy" ]; then
    echo "=========================================================================="
    echo "Applying Cloud Deploy Pipeline & Creating Release: conductor-v3-pipeline"
    echo "=========================================================================="
    gcloud deploy apply --file=clouddeploy-v3.yaml --region="${REGION}" --project="${VERTEX_AI_PROJECT}"
    gcloud deploy releases create "release-v3-${GIT_TAG}" \
        --project="${VERTEX_AI_PROJECT}" \
        --region="${REGION}" \
        --delivery-pipeline="conductor-v3-pipeline" \
        --images="${SERVICE_NAME}=${IMAGE_TAG}" \
        --annotations="commit=${GIT_TAG},deployer=deploy_cloud_run_v3_sh"
else
    echo "=========================================================================="
    echo "Deploying ${SERVICE_NAME} directly to Google Cloud Run (${REGION})"
    echo "Model:              ${VERTEX_AI_MODEL}"
    echo "Cloud SQL Instance: ${CLOUD_SQL_CONNECTION_NAME}"
    echo "Agent Registry:     Enabled (functional-type=agent, identity-type=agent-identity)"
    echo "Memory footprint:   512Mi (distroless Go runtime)"
    echo "=========================================================================="

    # Ensure Cloud Run and App Hub / Agent Registry APIs are enabled
    gcloud services enable run.googleapis.com apphub.googleapis.com --project="${VERTEX_AI_PROJECT}" --quiet 2>/dev/null || true

    gcloud alpha run deploy "${SERVICE_NAME}" \
        --project="${VERTEX_AI_PROJECT}" \
        --region="${REGION}" \
        --image="${IMAGE_TAG}" \
        --service-account="${SERVICE_ACCOUNT_EMAIL}" \
        --functional-type="agent" \
        --identity-type="agent-identity" \
        --labels="app=conductor-v3,part-of=analyst-response-agent,runtime=go-cloud-run" \
        --cpu="1000m" \
        --memory="512Mi" \
        --concurrency=100 \
        --timeout=3600 \
        --no-cpu-throttling \
        --cpu-boost \
        --ingress=all \
        --allow-unauthenticated \
        --add-cloudsql-instances="${CLOUD_SQL_CONNECTION_NAME}" \
        --set-env-vars="VERTEX_AI_PROJECT=${VERTEX_AI_PROJECT},VERTEX_AI_LOCATION=${REGION},VERTEX_AI_MODEL=${VERTEX_AI_MODEL},CLOUD_SQL_INSTANCE_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME},ENVIRONMENT=${ENVIRONMENT},AGENT_RUNTIME=go-cloud-run,AGENT_REGISTRY_ENABLED=true,AGENT_FUNCTIONAL_TYPE=agent,AGENT_NAME=conductor-v3" \
        --set-secrets="DATABASE_URL=CONDUCTOR_DATABASE_URL:latest,SECURITY_SECRET_KEY=CONDUCTOR_SECURITY_SECRET_KEY:latest"
fi

echo "=========================================================================="
echo "Conductor v3 deployment script execution finished successfully."
echo "=========================================================================="
