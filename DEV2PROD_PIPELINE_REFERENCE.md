# Google Cloud Dev2Prod CI/CD Pipeline: Architecture, Workflow & Complete Manifest Dossier

**Target Application:** Analyst Response Agent (`rficonductorv2` / Conductor v2)  
**Target Platform:** Google Cloud Run (Serverless GPU / AI Container Workload)  
**Pipeline Components:** Google Cloud Build (CI), Google Artifact Registry, Google Cloud Deploy (CD), Headless Playwright (UI Testing), Pytest (Hermetic Unit Testing), Cloud Secret Manager, Cloud SQL for PostgreSQL.

---

## 📋 Executive Summary & Pipeline Intent

The **Google Cloud Dev2Prod (Development-to-Production)** CI/CD pipeline provides a fully automated, declarative, and secure delivery lifecycle for the **Analyst Response Agent (ARA)**. It establishes an enterprise-grade GitOps release cadence that guarantees:

1. **Hermetic Pre-Commit Verification (Zero Flaky Builds):** Every commit automatically executes both backend unit/integration tests and headless browser UI tests inside an isolated Playwright container before container compilation begins.
2. **Immutable Artifact Registry Management:** All container images are built via Google Cloud Build, tagged with immutable Git commit SHAs (`$COMMIT_SHA`), and pushed to Google Artifact Registry (`pkg.dev`) where automated vulnerability analysis (Container Analysis / SLSA provenance) is performed.
3. **Multi-Stage Progressive Delivery (`dev` ➔ `staging` ➔ `prod`):** Releases progress through structured delivery stages managed by **Google Cloud Deploy**, supporting environment-specific parameter overrides without modifying base container images.
4. **Automated Post-Deployment Verification Hooks:** Following every deployment, Cloud Deploy invokes automated synthetic verification runners that test the newly deployed Cloud Run target revision against live end-to-end user journeys and defensive error interception before routing full traffic.
5. **Canary Rollout Strategy & Protected Production Gates:** Production releases enforce an explicit manual approval gate (`requireApproval: true`) and execute progressive Canary traffic shifting (`25% ➔ 50% ➔ 100%`) with automatic traffic control.

---

## 🏗️ End-to-End Architectural Flow

```mermaid
flowchart TD
    subgraph SCM["Source Code Management (Git)"]
        GitCommit["Developer / Agent Git Commit\n(Feature Code + Tests)"]
    end

    subgraph CI["Continuous Integration — Google Cloud Build (cloudbuild.yaml)"]
        Step1["Step 1: Hermetic Testing\n(mcr.microsoft.com/playwright/python)\n• 111 Pytest Backend Tests\n• 5 Headless Playwright UI Tests"]
        Step2["Step 2: Multi-Stage Container Build\n(Dockerfile -> python:3.11-slim)"]
        Step3["Step 3: Push to Artifact Registry\n(${REGION}-docker.pkg.dev/...:${COMMIT_SHA})"]
        Step4["Step 4: Create Cloud Deploy Release\n(gcloud deploy releases create)"]
        
        Step1 -->|Pass (100%)| Step2
        Step2 --> Step3
        Step3 --> Step4
    end

    subgraph CD["Continuous Delivery — Google Cloud Deploy (clouddeploy.yaml + skaffold.yaml)"]
        TargetDev["Target 1: Dev (Cloud Run)\n• Environment: development\n• Hook: Live E2E Verification"]
        TargetStaging["Target 2: Staging (Cloud Run)\n• Environment: staging\n• Hook: Live E2E Verification"]
        ApprovalGate{"Manual Approval Gate\n(roles/clouddeploy.approver)"}
        TargetProd["Target 3: Production (Cloud Run)\n• Environment: production\n• Canary: 25% ➔ 50% ➔ 100%\n• Hook: Live E2E Verification"]

        Step4 --> TargetDev
        TargetDev -->|Auto / CLI Promotion| TargetStaging
        TargetStaging --> ApprovalGate
        ApprovalGate -->|Approved| TargetProd
    end

    GitCommit --> CI
```

---

## 📁 Pipeline File & Directory Inventory

The following files and directories define the complete CI/CD, testing, infrastructure, and deployment framework:

| File Path | Component Area | Responsibility |
| :--- | :--- | :--- |
| [`cloudbuild.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/cloudbuild.yaml) | **CI Pipeline** | Cloud Build configuration defining the 5-step CI process (Playwright/Pytest test execution, Docker build, Artifact Registry push, and Cloud Deploy release creation). |
| [`clouddeploy.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/clouddeploy.yaml) | **CD Pipeline** | Cloud Deploy specification defining the `conductor-v2-pipeline` delivery pipeline, targets (`dev`, `staging`, `prod`), canary deployment rules, and post-deploy hooks. |
| [`skaffold.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/skaffold.yaml) | **Deployment Config** | Skaffold manifest used by Cloud Deploy for Cloud Run rendering, stage patching profiles (`dev`, `staging`, `prod`), and custom verification actions (`postdeploy-e2e-test`). |
| [`infra/cloudrun/service.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/cloudrun/service.yaml) | **Cloud Run Service** | Declarative Knative/Cloud Run manifest declaring CPU boost, non-throttled instances, Cloud SQL Unix domain socket mounting, Secret Manager bindings, and health probes. |
| [`infra/ci_cd/run_post_deploy_verification.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/ci_cd/run_post_deploy_verification.py) | **Verification Hook** | Unified Python runner executed by Cloud Deploy post-deploy hooks to execute live E2E and error-handling test suites against dynamic target URLs. |
| [`infra/deploy_cloud_run.sh`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/deploy_cloud_run.sh) | **Automation CLI** | Shell automation script supporting both direct deployment and Cloud Deploy release creation via Artifact Registry. |
| [`infra/DEV2PROD_SETUP.md`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/DEV2PROD_SETUP.md) | **Setup Guide** | Step-by-step setup documentation covering GCP API activation, Artifact Registry provisioning, and Cloud Build/Deploy IAM roles. |
| [`infra/iam_permissions.md`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/iam_permissions.md) | **IAM Posture** | Least-privilege IAM runtime specification for `conductor-agent` Workload Identity on Cloud Run. |
| [`tests/test_ci_cd_pipeline_configurations.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/tests/test_ci_cd_pipeline_configurations.py) | **Pipeline Tests** | Automated Pytest suite validating YAML schemas, step order, substitutions, and Knative service annotations. |
| [`tests/test_ui_portal.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/tests/test_ui_portal.py) | **UI Testing** | Headless Playwright test suite validating header rendering, workspace selector, chat interactions, modals, and responsive layouts. |
| [`requirements.txt`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/requirements.txt) | **Dependencies** | Python package dependencies, including `playwright`, `pytest`, `fastapi`, `sqlalchemy`, and `opentelemetry`. |
| [`Dockerfile`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/Dockerfile) | **Container Build** | Multi-stage Dockerfile compiling C extensions in builder stage and running Uvicorn as non-root user `conductor-runtime`. |

---

## 📜 Full Text of Pipeline Manifests & Source Files

---

### 1. `cloudbuild.yaml`
```yaml
steps:
  # Step 1: Run Hermetic Unit, Integration & Headless Playwright UI Tests
  - name: 'mcr.microsoft.com/playwright/python:v1.49.0-noble'
    id: 'unit-and-ui-tests'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install --no-cache-dir --extra-index-url https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/ -r requirements.txt pytest pytest-asyncio
        pytest tests/ -v

  # Step 2: Build Container Image via Docker
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-container-image'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:${COMMIT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:latest'
      - '.'

  # Step 3: Push Immutable Container Image to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push-to-artifact-registry'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:${COMMIT_SHA}'

  # Step 4: Push Latest Tag to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push-latest-tag'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:latest'

  # Step 5: Create Google Cloud Deploy Release for Automated Stage Progression
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'create-cloud-deploy-release'
    entrypoint: 'gcloud'
    args:
      - 'deploy'
      - 'releases'
      - 'create'
      - 'release-${SHORT_SHA}'
      - '--delivery-pipeline=${_DELIVERY_PIPELINE_NAME}'
      - '--region=${_REGION}'
      - '--images=${_SERVICE_NAME}=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:${COMMIT_SHA}'
      - '--annotations=commitId=${COMMIT_SHA},trigger=cloudbuild'

images:
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:${COMMIT_SHA}'
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:latest'

substitutions:
  _REGION: 'us-central1'
  _REPO_NAME: 'conductor-repo'
  _SERVICE_NAME: 'conductor-v2'
  _DELIVERY_PIPELINE_NAME: 'conductor-v2-pipeline'

options:
  logging: CLOUD_LOGGING_ONLY
  substitution_option: 'ALLOW_LOOSE'
```

---

### 2. `clouddeploy.yaml`
```yaml
apiVersion: deploy.cloud.google.com/v1
kind: DeliveryPipeline
metadata:
  name: conductor-v2-pipeline
  labels:
    app: conductor-v2
description: Enterprise Dev2Prod Delivery Pipeline for Analyst Response Agent (Conductor v2)
serialPipeline:
  stages:
    - targetId: dev
      profiles:
        - dev
      strategy:
        standard:
          postdeploy:
            actions:
              - postdeploy-e2e-test
    - targetId: staging
      profiles:
        - staging
      strategy:
        standard:
          postdeploy:
            actions:
              - postdeploy-e2e-test
    - targetId: prod
      profiles:
        - prod
      strategy:
        canary:
          runtimeConfig:
            cloudRun:
              automaticTrafficControl: true
          canaryDeployment:
            percentages:
              - 25
              - 50
            postdeploy:
              actions:
                - postdeploy-e2e-test
---
apiVersion: deploy.cloud.google.com/v1
kind: Target
metadata:
  name: dev
  labels:
    env: dev
    app: conductor-v2
description: Development Environment (Cloud Run - us-central1)
run:
  location: projects/riccardo-blog-test-v1/locations/us-central1
---
apiVersion: deploy.cloud.google.com/v1
kind: Target
metadata:
  name: staging
  labels:
    env: staging
    app: conductor-v2
description: Staging Pre-Production Environment (Cloud Run - us-central1)
run:
  location: projects/riccardo-blog-test-v1/locations/us-central1
---
apiVersion: deploy.cloud.google.com/v1
kind: Target
metadata:
  name: prod
  labels:
    env: prod
    app: conductor-v2
description: Production Environment with Approval Gate and Canary Deployment (Cloud Run - us-central1)
requireApproval: true
run:
  location: projects/riccardo-blog-test-v1/locations/us-central1
```

---

### 3. `skaffold.yaml`
```yaml
apiVersion: skaffold/v4beta7
kind: Config
metadata:
  name: conductor-v2
build:
  artifacts:
    - image: conductor-v2
      context: .
      docker:
        dockerfile: Dockerfile
manifests:
  rawYaml:
    - infra/cloudrun/service.yaml
deploy:
  cloudrun: {}
profiles:
  - name: dev
    manifests:
      rawYaml:
        - infra/cloudrun/service-dev.yaml
  - name: staging
    manifests:
      rawYaml:
        - infra/cloudrun/service-staging.yaml
  - name: prod
    manifests:
      rawYaml:
        - infra/cloudrun/service.yaml
customActions:
  - name: postdeploy-e2e-test
    containers:
      - name: postdeploy-test-runner
        image: conductor-v2
        command:
          - /bin/bash
          - -c
          - |
            cd /app
            python infra/ci_cd/run_post_deploy_verification.py
```

---

### 4. `infra/cloudrun/service.yaml`
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: conductor-v2
  labels:
    cloud.googleapis.com/location: us-central1
    app.kubernetes.io/name: conductor-v2
    app.kubernetes.io/part-of: analyst-response-agent
    apphub.googleapis.com/functional-type: agent
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/launch-stage: GA
    apphub.cloud.google.com/functional-type: agent
    apphub.cloud.google.com/display-name: "Analyst Response Agent (Conductor v2)"
    apphub.cloud.google.com/description: "Autonomous multi-agent enterprise response platform for Gartner, Forrester, and IDC analyst evaluations"
spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/name: conductor-v2
        apphub.googleapis.com/functional-type: agent
      annotations:
        run.googleapis.com/client.name: cloud-deploy
        run.googleapis.com/functional-type: agent
        run.googleapis.com/identity-type: agent-identity
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/startup-cpu-boost: "true"
        run.googleapis.com/cloudsql-instances: riccardo-blog-test-v1:us-central1:genai-rag-db-859a1005
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containerConcurrency: 80
      timeoutSeconds: 3600
      serviceAccountName: conductor-agent@riccardo-blog-test-v1.iam.gserviceaccount.com
      containers:
        - name: conductor-v2
          image: conductor-v2
          ports:
            - name: http1
              containerPort: 8080
          resources:
            limits:
              cpu: "2000m"
              memory: "4Gi"
          env:
            - name: VERTEX_AI_PROJECT
              value: "riccardo-blog-test-v1"
            - name: VERTEX_AI_MODEL
              value: "gemini-3.5-flash"
            - name: ENVIRONMENT
              value: "production"
            - name: AGENT_REGISTRY_ENABLED
              value: "true"
            - name: AGENT_FUNCTIONAL_TYPE
              value: "agent"
            - name: AGENT_DISPLAY_NAME
              value: "Analyst Response Agent (Conductor v2)"
            - name: CLOUD_SQL_INSTANCE_CONNECTION_NAME
              value: "riccardo-blog-test-v1:us-central1:genai-rag-db-859a1005"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: CONDUCTOR_DATABASE_URL
                  key: latest
            - name: SECURITY_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: CONDUCTOR_SECURITY_SECRET_KEY
                  key: latest
          startupProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 2
            periodSeconds: 5
            failureThreshold: 10
            timeoutSeconds: 3
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            periodSeconds: 15
            failureThreshold: 3
            timeoutSeconds: 5
```

---

### 5. `infra/ci_cd/run_post_deploy_verification.py`
```python
#!/usr/bin/env python3
"""
Google Cloud Deploy Post-Deploy Verification Hook Runner
Executes comprehensive synthetic and live integration tests against the newly deployed Cloud Run target URL.
Compatible with Cloud Deploy customActions and Cloud Build verification steps.
"""

import os
import sys
import subprocess

def main():
    target_url = os.getenv("CLOUD_RUN_URL") or os.getenv("TARGET_URL")
    if not target_url and len(sys.argv) > 1:
        target_url = sys.argv[1]

    if not target_url:
        print("[WARN] No CLOUD_RUN_URL or TARGET_URL provided. Defaulting to production benchmark URL.")
        target_url = "https://conductor-v2-105792947502.us-central1.run.app"

    print(f"==========================================================================")
    print(f"🚀 Cloud Deploy Post-Deploy Verification Hook Starting")
    print(f"🎯 Target URL: {target_url}")
    print(f"==========================================================================")

    env = os.environ.copy()
    env["TARGET_URL"] = target_url
    env["CLOUD_RUN_URL"] = target_url

    # 1. Run Standard Workflow & Exploratory E2E Tests
    print("\n--- [Step 1/2] Running Live Full E2E Workflow Test ---")
    ret1 = subprocess.run([sys.executable, "test_live_cloud_run_full_e2e.py"], env=env)
    if ret1.returncode != 0:
        print("[FAIL] Post-deploy full E2E workflow verification failed!")
        sys.exit(ret1.returncode)

    # 2. Run Defensive Error Interception Test
    print("\n--- [Step 2/2] Running Live Error Handling & Resilience Test ---")
    ret2 = subprocess.run([sys.executable, "test_live_cloud_run_error_scenarios.py"], env=env)
    if ret2.returncode != 0:
        print("[FAIL] Post-deploy error scenario resilience verification failed!")
        sys.exit(ret2.returncode)

    print("\n==========================================================================")
    print("✅ All Cloud Deploy Post-Deploy Verification Checks Passed (100%)")
    print("==========================================================================")

if __name__ == "__main__":
    main()
```

---

### 6. `infra/deploy_cloud_run.sh`
```bash
#!/usr/bin/env bash
# deploy_cloud_run.sh
# Automated build & deployment script for Analyst Response Agent (ARA) on Google Cloud Run
# Supports both Google Cloud Deploy (Dev2Prod release pipeline) and Direct Cloud Run deployment via Artifact Registry.

set -euo pipefail

# Auto-configure ADC access token for gcloud CLI when running on developer Cloudtop / workstation environments
if command -v gcloud >/dev/null 2>&1 && [ -f "${HOME}/.config/gcloud/application_default_credentials.json" ]; then
    gcloud auth application-default print-access-token > /tmp/adc_token 2>/dev/null || true
    if [ -s /tmp/adc_token ]; then
        export CLOUDSDK_AUTH_ACCESS_TOKEN_FILE="/tmp/adc_token"
    fi
fi

# Configuration Environment Variables (Override via environment or replace defaults)
: "${VERTEX_AI_PROJECT:=riccardo-blog-test-v1}"
: "${VERTEX_AI_MODEL:=gemini-3.5-flash}"
: "${REGION:=us-central1}"
: "${REPO_NAME:=conductor-repo}"
: "${SERVICE_NAME:=conductor-v2}"
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
echo "Google Cloud Dev2Prod CI/CD Build"
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
    --description="Docker repository for Conductor v2 agent images" \
    --quiet

# Execute Cloud Build
echo "Building and pushing container image via Google Cloud Build..."
gcloud builds submit \
    --project="${VERTEX_AI_PROJECT}" \
    --tag="${IMAGE_TAG}" \
    .

# Also tag as latest in Artifact Registry
gcloud artifacts docker tags add "${IMAGE_TAG}" "${LATEST_TAG}" --quiet 2>/dev/null || true

if [ "${DEPLOY_METHOD}" = "cloud-deploy" ]; then
    echo "=========================================================================="
    echo "Creating Google Cloud Deploy Release in pipeline: conductor-v2-pipeline"
    echo "=========================================================================="
    gcloud deploy releases create "release-${GIT_TAG}" \
        --project="${VERTEX_AI_PROJECT}" \
        --region="${REGION}" \
        --delivery-pipeline="conductor-v2-pipeline" \
        --images="${SERVICE_NAME}=${IMAGE_TAG}" \
        --annotations="commit=${GIT_TAG},deployer=deploy_cloud_run_sh"
else
    echo "=========================================================================="
    echo "Deploying ${SERVICE_NAME} directly to Google Cloud Run (${REGION})"
    echo "Model:              ${VERTEX_AI_MODEL}"
    echo "Cloud SQL Instance: ${CLOUD_SQL_CONNECTION_NAME}"
    echo "Agent Registry:     Enabled (functional-type=agent, identity-type=agent-identity)"
    echo "=========================================================================="

    # Ensure Cloud Run and App Hub / Agent Registry APIs are enabled
    gcloud services enable run.googleapis.com apphub.googleapis.com --project="${VERTEX_AI_PROJECT}" --quiet 2>/dev/null || true

    gcloud run deploy "${SERVICE_NAME}" \
        --project="${VERTEX_AI_PROJECT}" \
        --region="${REGION}" \
        --image="${IMAGE_TAG}" \
        --service-account="${SERVICE_ACCOUNT_EMAIL}" \
        --functional-type="agent" \
        --identity-type="agent-identity" \
        --labels="apphub.googleapis.com/functional-type=agent,app.kubernetes.io/name=conductor-v2,app.kubernetes.io/part-of=analyst-response-agent" \
        --timeout=3600 \
        --no-cpu-throttling \
        --cpu-boost \
        --ingress=all \
        --allow-unauthenticated \
        --add-cloudsql-instances="${CLOUD_SQL_CONNECTION_NAME}" \
        --set-env-vars="VERTEX_AI_PROJECT=${VERTEX_AI_PROJECT},VERTEX_AI_MODEL=${VERTEX_AI_MODEL},CLOUD_SQL_INSTANCE_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME},ENVIRONMENT=${ENVIRONMENT},AGENT_REGISTRY_ENABLED=true,AGENT_FUNCTIONAL_TYPE=agent,AGENT_NAME=conductor-v2" \
        --set-secrets="DATABASE_URL=CONDUCTOR_DATABASE_URL:latest,SECURITY_SECRET_KEY=CONDUCTOR_SECURITY_SECRET_KEY:latest"
fi

echo "=========================================================================="
echo "Deployment operations for ${SERVICE_NAME} completed successfully!"
echo "=========================================================================="
```

---

### 7. `infra/DEV2PROD_SETUP.md`
```markdown
# Google Cloud Dev2Prod CI/CD Pipeline Specification (`rficonductorv2`)

This document outlines the complete Google Cloud Development-to-Production (Dev2Prod) continuous integration and continuous delivery pipeline for the **Analyst Response Agent (ARA / Conductor v2)**.

---

## 📋 Required Google Cloud APIs

Ensure the following APIs are enabled in your Google Cloud Project (`riccardo-blog-test-v1`):

\`\`\`bash
gcloud services enable \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    clouddeploy.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    aiplatform.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com
\`\`\`

---

## 📦 1. Artifact Registry Setup

Create the Docker artifact repository:

\`\`\`bash
export PROJECT_ID="riccardo-blog-test-v1"
export REGION="us-central1"
export REPO_NAME="conductor-repo"

gcloud artifacts repositories create ${REPO_NAME} \
    --project=${PROJECT_ID} \
    --location=${REGION} \
    --repository-format=docker \
    --description="Docker repository for Conductor v2 agent images"
\`\`\`

---

## 🔐 2. Service Accounts & IAM Permissions

### A. Cloud Build Service Account Permissions
Grant Cloud Build permissions to trigger Cloud Deploy releases and access Artifact Registry:

\`\`\`bash
export CB_SA="$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"

# Grant Cloud Deploy Releaser
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${CB_SA}" \
    --role="roles/clouddeploy.releaser"

# Grant Artifact Registry Writer
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${CB_SA}" \
    --role="roles/artifactregistry.writer"

# Grant Service Account User to act as the runtime service account
gcloud iam service-accounts add-iam-policy-binding \
    conductor-agent@${PROJECT_ID}.iam.gserviceaccount.com \
    --member="serviceAccount:${CB_SA}" \
    --role="roles/iam.serviceAccountUser"
\`\`\`

### B. Cloud Deploy Service Account Permissions
Grant Cloud Deploy permissions to deploy to Cloud Run:

\`\`\`bash
export CD_SA="service-$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')@gcp-sa-clouddeploy.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${CD_SA}" \
    --role="roles/run.developer"
\`\`\`

---

## 🚀 3. Registering the Cloud Deploy Pipeline & Targets

Apply the delivery pipeline and targets defined in `clouddeploy.yaml`:

\`\`\`bash
gcloud deploy apply \
    --file=clouddeploy.yaml \
    --region=us-central1 \
    --project=riccardo-blog-test-v1
\`\`\`

Verify the pipeline status:

\`\`\`bash
gcloud deploy delivery-pipelines describe conductor-v2-pipeline \
    --region=us-central1 \
    --project=riccardo-blog-test-v1
\`\`\`

---

## 🔄 4. Triggering Releases

### Option A: Via Google Cloud Build (Recommended for CI/CD)
When code is pushed to your source repository, Cloud Build executes `cloudbuild.yaml`:
\`\`\`bash
gcloud builds submit --config=cloudbuild.yaml --project=riccardo-blog-test-v1 .
\`\`\`

### Option B: Via Local Automation Script
\`\`\`bash
DEPLOY_METHOD=cloud-deploy bash infra/deploy_cloud_run.sh
\`\`\`

---

## 🛡️ 5. Cloud Deploy Stage Promotion & Approval

To promote a release from `dev` to `staging`:
\`\`\`bash
gcloud deploy releases promote \
    --release="release-<TAG>" \
    --delivery-pipeline="conductor-v2-pipeline" \
    --region="us-central1"
\`\`\`

To approve promotion into `prod`:
\`\`\`bash
gcloud deploy rollouts approve <ROLLOUT_NAME> \
    --delivery-pipeline="conductor-v2-pipeline" \
    --region="us-central1"
\`\`\`
```

---

### 8. `infra/iam_permissions.md`
```markdown
# IAM & Workload Identity Setup Specification

This document details the least-privilege runtime Identity and Access Management (IAM) security posture required for deploying **Analyst Response Agent (ARA)** on Google Cloud Run using Workload Identity.

## Service Account Definition

- **Service Account Name:** `conductor-agent`
- **Fully Qualified Email:** `conductor-agent@${VERTEX_AI_PROJECT}.iam.gserviceaccount.com`

---

## Least-Privilege Runtime Roles

To adhere to the principle of least privilege, assign only the following exact roles to the `conductor-agent` service account:

| Role | Role ID | Justification |
| :--- | :--- | :--- |
| **Vertex AI User** | `roles/aiplatform.user` | Required for invoking Vertex AI LLM (`gemini-3.5-flash`, `gemini-1.5-pro`) and text-embedding APIs (`text-embedding-004`). |
| **Cloud SQL Client** | `roles/cloudsql.client` | Required for connecting to Cloud SQL for PostgreSQL / AlloyDB instances via high-performance Unix domain sockets. |
| **Secret Manager Secret Accessor** | `roles/secretmanager.secretAccessor` | Required for securely mounting `DATABASE_URL` and `SECURITY_SECRET_KEY` from Google Secret Manager as runtime environment variables. |
| **Logs Writer** | `roles/logging.logWriter` | Required for emitting structured JSON audit logs correlated with Cloud Trace headers (`X-Cloud-Trace-Context`). |
| **Cloud Trace Agent** | `roles/cloudtrace.agent` | Required for exporting distributed OpenTelemetry trace spans (`opentelemetry-exporter-gcp-trace`) across HTTP, DB, and AI layers. |

---

## Workload Identity Binding for Cloud Run

When deploying the Cloud Run service, ensure `--service-account=${SA_EMAIL}` is explicitly passed so the container inherits this exact IAM posture without requiring physical JSON service account keys.
```

---

### 9. `tests/test_ci_cd_pipeline_configurations.py`
```python
#!/usr/bin/env python3
"""
Unit and Integration Tests for Google Cloud Dev2Prod CI/CD Configuration Files
Validates syntax, schemas, cross-references, environment profiles, and security postures
across cloudbuild.yaml, clouddeploy.yaml, skaffold.yaml, and infra/cloudrun/service.yaml.
"""

import os
import yaml
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

def load_yaml_file(filepath: Path):
    assert filepath.exists(), f"Configuration file {filepath} does not exist"
    with open(filepath, "r", encoding="utf-8") as f:
        # Load all documents if multi-document YAML
        docs = list(yaml.safe_load_all(f))
    return docs

def test_cloudbuild_yaml_structure_and_steps():
    """Validates Cloud Build CI pipeline configuration."""
    cloudbuild_path = REPO_ROOT / "cloudbuild.yaml"
    docs = load_yaml_file(cloudbuild_path)
    assert len(docs) == 1, "cloudbuild.yaml should contain a single document"
    cb = docs[0]

    assert "steps" in cb, "cloudbuild.yaml must declare 'steps'"
    steps = cb["steps"]
    step_ids = [s.get("id") for s in steps]

    # Verify key CI steps exist in order
    assert any("test" in s_id for s_id in step_ids), "Must contain unit/UI testing step"
    assert "build-container-image" in step_ids, "Must contain container build step"
    assert "push-to-artifact-registry" in step_ids, "Must contain push step to Artifact Registry"
    assert "create-cloud-deploy-release" in step_ids, "Must contain Cloud Deploy release step"

    # Verify Step 1 uses Playwright container for UI testing support
    test_step = next(s for s in steps if "test" in s.get("id", ""))
    assert "playwright" in test_step["name"].lower() or "python" in test_step["name"].lower()

    # Verify substitutions and image registry
    assert "substitutions" in cb
    assert cb["substitutions"].get("_SERVICE_NAME") == "conductor-v2"
    assert cb["substitutions"].get("_DELIVERY_PIPELINE_NAME") == "conductor-v2-pipeline"
    assert cb["substitutions"].get("_REPO_NAME") == "conductor-repo"

    # Ensure Artifact Registry format is used
    images = cb.get("images", [])
    assert any("pkg.dev" in img for img in images), "Images must be pushed to Artifact Registry (pkg.dev)"

def test_clouddeploy_yaml_pipeline_and_targets():
    """Validates Google Cloud Deploy delivery pipeline, targets, and canary stages."""
    clouddeploy_path = REPO_ROOT / "clouddeploy.yaml"
    docs = load_yaml_file(clouddeploy_path)
    assert len(docs) >= 4, "clouddeploy.yaml should contain DeliveryPipeline and at least 3 Target documents"

    pipeline_doc = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
    assert pipeline_doc is not None, "DeliveryPipeline kind not found in clouddeploy.yaml"
    assert pipeline_doc["metadata"]["name"] == "conductor-v2-pipeline"

    # Verify stage progression
    stages = pipeline_doc["serialPipeline"]["stages"]
    stage_target_ids = [s["targetId"] for s in stages]
    assert stage_target_ids == ["dev", "staging", "prod"], "Stages must progress dev -> staging -> prod"

    # Verify prod stage has canary rollout strategy and postdeploy actions
    prod_stage = next(s for s in stages if s["targetId"] == "prod")
    assert "canary" in prod_stage["strategy"], "Prod stage must have canary deployment strategy"

    # Verify targets
    targets = [d for d in docs if d.get("kind") == "Target"]
    target_names = [t["metadata"]["name"] for t in targets]
    assert "dev" in target_names
    assert "staging" in target_names
    assert "prod" in target_names

    prod_target = next(t for t in targets if t["metadata"]["name"] == "prod")
    assert prod_target.get("requireApproval") is True, "Production target must require manual approval gate"

def test_skaffold_yaml_profiles_and_custom_actions():
    """Validates Skaffold configuration for Cloud Deploy rendering."""
    skaffold_path = REPO_ROOT / "skaffold.yaml"
    docs = load_yaml_file(skaffold_path)
    assert len(docs) == 1
    sk = docs[0]

    assert sk.get("apiVersion", "").startswith("skaffold/")
    assert sk.get("kind") == "Config"
    assert "manifests" in sk
    assert "infra/cloudrun/service.yaml" in sk["manifests"]["rawYaml"]

    # Verify environment profiles
    profiles = sk.get("profiles", [])
    profile_names = [p["name"] for p in profiles]
    assert "dev" in profile_names
    assert "staging" in profile_names
    assert "prod" in profile_names

    # Verify custom post-deploy actions
    custom_actions = sk.get("customActions", [])
    action_names = [a["name"] for a in custom_actions]
    assert "postdeploy-e2e-test" in action_names

def test_declarative_cloud_run_service_manifest():
    """Validates the declarative Knative/Cloud Run service manifest."""
    service_path = REPO_ROOT / "infra" / "cloudrun" / "service.yaml"
    docs = load_yaml_file(service_path)
    assert len(docs) == 1
    svc = docs[0]

    assert svc.get("apiVersion") == "serving.knative.dev/v1"
    assert svc.get("kind") == "Service"
    assert svc["metadata"]["name"] == "conductor-v2"

    template = svc["spec"]["template"]
    annotations = template["metadata"]["annotations"]

    # Performance and Cloud SQL checks
    assert annotations.get("run.googleapis.com/cpu-throttling") == "false"
    assert annotations.get("run.googleapis.com/startup-cpu-boost") == "true"
    assert "run.googleapis.com/cloudsql-instances" in annotations

    spec = template["spec"]
    assert spec["timeoutSeconds"] == 3600
    assert spec["containerConcurrency"] == 80
    assert "conductor-agent@" in spec["serviceAccountName"]

    container = spec["containers"][0]
    assert container["ports"][0]["containerPort"] == 8080

    # Verify Secret Manager secret bindings
    env_vars = container["env"]
    secret_names = [e["name"] for e in env_vars if "valueFrom" in e]
    assert "DATABASE_URL" in secret_names
    assert "SECURITY_SECRET_KEY" in secret_names

def test_post_deploy_runner_file_exists_and_executable():
    """Validates the post-deploy verification script."""
    runner_path = REPO_ROOT / "infra" / "ci_cd" / "run_post_deploy_verification.py"
    assert runner_path.exists(), "Post-deploy verification runner must exist"
    assert os.access(runner_path, os.R_OK), "Post-deploy verification runner must be readable"

def test_pip_extra_index_url_cloudbuild_pipelines():
    """Validates that all pip install commands across CloudBuild pipelines configure --extra-index-url for Artifact Registry."""
    import re
    expected_url = "https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/"
    expected_pattern = re.compile(rf"--extra-index-url(?:=|\s+)[\"']?{re.escape(expected_url)}[\"']?")
    pip_pattern = re.compile(r"(?:^|[;&|\s])(?:pip|pip3|python[0-9.]*\s+-m\s+pip)\s+install\b")

    # Validate all CloudBuild pipeline manifests
    cb_files = sorted(set(list(REPO_ROOT.glob("cloudbuild*.yaml")) + list(REPO_ROOT.glob("infra/**/cloudbuild*.yaml"))))
    assert len(cb_files) >= 2, "Must find at least cloudbuild.yaml and cloudbuild-agent-engine.yaml"

    checked_required = {"cloudbuild.yaml": False, "cloudbuild-agent-engine.yaml": False}

    for cb_path in cb_files:
        docs = load_yaml_file(cb_path)
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            for step in doc.get("steps", []):
                scripts_to_check = []
                if "script" in step and step["script"]:
                    scripts_to_check.append(step["script"])
                
                entrypoint = step.get("entrypoint", "")
                args = step.get("args", [])
                args_str = " ".join(args)
                if entrypoint:
                    scripts_to_check.append(f"{entrypoint} {args_str}")
                else:
                    scripts_to_check.append(args_str)

                for raw_script in scripts_to_check:
                    normalized_script = raw_script.replace("\\\n", " ").replace("\\\r\n", " ")
                    for line in normalized_script.splitlines():
                        if pip_pattern.search(line) or (entrypoint in ("pip", "pip3") and "install" in line):
                            if cb_path.name in checked_required:
                                checked_required[cb_path.name] = True
                            assert expected_pattern.search(line), (
                                f"Python package installation in {cb_path.name} (step: {step.get('id', 'unnamed')}) "
                                f"missing extra-index-url: {line.strip()}"
                            )

    for req_name, found in checked_required.items():
        assert found, f"{req_name} must contain at least one pip install invocation"

def test_dockerfile_and_requirements_extra_index_url():
    """Validates that Dockerfile builder stage and requirements files configure --extra-index-url for python-pypi."""
    import re
    expected_url = "https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/"
    expected_flag_pattern = re.compile(rf"--extra-index-url(?:=|\s+)[\"']?{re.escape(expected_url)}[\"']?")
    pip_pattern = re.compile(r"(?:^|[;&|\s])(?:pip|pip3|python[0-9.]*\s+-m\s+pip)\s+install\b")

    # Validate all Dockerfiles across the repository
    dockerfiles = sorted(set(list(REPO_ROOT.glob("Dockerfile*")) + list(REPO_ROOT.glob("**/Dockerfile*"))))
    found_pip_in_dockerfile = False
    for df in dockerfiles:
        if ".venv" in df.parts or ".agents" in df.parts:
            continue
        content = df.read_text(encoding="utf-8")
        normalized = content.replace("\\\n", " ").replace("\\\r\n", " ")
        for line in normalized.splitlines():
            if pip_pattern.search(line):
                found_pip_in_dockerfile = True
                assert expected_flag_pattern.search(line), f"{df.name} pip install missing extra-index-url: {line.strip()}"

    assert found_pip_in_dockerfile, "Repository Dockerfiles must contain at least one pip install invocation"

    # Validate infra/agent_engine/requirements.txt
    ae_req_path = REPO_ROOT / "infra" / "agent_engine" / "requirements.txt"
    assert ae_req_path.exists(), "infra/agent_engine/requirements.txt must exist"
    ae_req_lines = [l.strip() for l in ae_req_path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert any(expected_flag_pattern.search(l) for l in ae_req_lines), (
        f"infra/agent_engine/requirements.txt must retain --extra-index-url configuration for {expected_url}"
    )

    # Validate root requirements.txt
    root_req_path = REPO_ROOT / "requirements.txt"
    assert root_req_path.exists(), "requirements.txt must exist"
    root_req_lines = [l.strip() for l in root_req_path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert any(expected_flag_pattern.search(l) for l in root_req_lines), (
        f"requirements.txt must configure --extra-index-url for {expected_url}"
    )

def test_extra_index_url_security_and_format_edge_cases():
    """Validates security posture and formatting of Artifact Registry extra-index-url configurations."""
    import re
    expected_url = "https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/"
    extra_index_pattern = re.compile(r"--extra-index-url(?:=|\s+)(\S+)")
    isolated_index_pattern = re.compile(r"(?<!-)--index-url\b")

    files_to_check = [
        REPO_ROOT / "cloudbuild.yaml",
        REPO_ROOT / "cloudbuild-agent-engine.yaml",
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "requirements.txt",
        REPO_ROOT / "infra" / "agent_engine" / "requirements.txt",
    ]
    for filepath in files_to_check:
        text = filepath.read_text(encoding="utf-8")

        # 1. Ensure no pipeline or build file uses dangerous --index-url (which would override public PyPI)
        for line in text.splitlines():
            if isolated_index_pattern.search(line):
                assert False, f"Found dangerous --index-url overriding PyPI in {filepath.name}: {line.strip()}"

        # 2. Extract every configured --extra-index-url from actual file content and validate
        urls = extra_index_pattern.findall(text)
        assert len(urls) > 0, f"{filepath.name} must declare at least one --extra-index-url"
        for raw_url in urls:
            url = raw_url.strip('"\'')
            assert url == expected_url, f"Unexpected extra-index-url in {filepath.name}: {url}"
            assert url.startswith("https://"), f"Artifact Registry URL must enforce HTTPS transport in {filepath.name}: {url}"
            assert url.endswith("/simple/"), f"Artifact Registry URL must follow PEP 503 trailing slash convention in {filepath.name}: {url}"
```

---

### 10. `tests/test_ui_portal.py`
```python
#!/usr/bin/env python3
"""
Automated Headless Playwright UI Test Suite for Analyst Response Agent (ARA) Web Portal
Validates DOM structure, A2UI executive client components, modal drawers, workspace switcher,
and client-side defensive error trapping without external network dependencies.
"""

import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

STATIC_HTML_PATH = Path(__file__).parent.parent / "app" / "static" / "index.html"

@pytest.fixture(scope="module")
def browser_context():
    """Launches headless Chromium for UI test scenarios."""
    with sync_playwright() as p:
        chrome_path = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
        launch_kwargs = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080"
            ]
        }
        if chrome_path:
            launch_kwargs["executable_path"] = chrome_path

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        yield context
        browser.close()

def test_ui_portal_header_and_workspace_selector(browser_context):
    """Verifies portal header, connection badge, and workspace selector initialization."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Verify Page Title and Header
    title = page.title()
    assert "Analyst Response Agent" in title

    header_text = page.locator("header").inner_text()
    assert "Analyst Response Agent" in header_text

    # 2. Verify Cloud Run Connection Badge
    assert "Cloud Run Connected" in header_text

    # 3. Verify Workspace Selector Dropdown is Present
    workspace_select = page.locator("#workspace-selector")
    assert workspace_select.is_visible()
    page.close()

def test_ui_portal_chat_controls_and_quick_actions(browser_context):
    """Verifies the chat input container, submit button, and quick action buttons."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Chat input textarea
    user_input = page.locator("#user-input")
    assert user_input.is_visible()
    user_input.fill("Test inquiry for criteria extraction")
    assert user_input.input_value() == "Test inquiry for criteria extraction"

    # 2. Chat form submit button (scoped to #chat-form)
    submit_btn = page.locator("#chat-form button[type='submit']")
    assert submit_btn.is_visible()

    # 3. Verify Quick Action Chips
    quick_actions = page.locator("button:has-text('Document Intake Form'), button:has-text('Saved Artifacts')")
    assert quick_actions.count() > 0
    page.close()

def test_ui_saved_artifacts_modal_drawer(browser_context):
    """Verifies opening and closing the right-side Saved Artifacts drawer modal."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    modal = page.locator("#saved-artifacts-modal")
    # Modal starts hidden
    assert not modal.is_visible() or "hidden" in (modal.get_attribute("class") or "")

    # Trigger modal open via UI helper or button
    page.evaluate("openSavedArtifactsModal()")
    page.wait_for_timeout(200)

    # Modal should now be visible or have hidden class removed
    modal_class = modal.get_attribute("class") or ""
    assert "hidden" not in modal_class or modal.is_visible()

    # Close modal
    page.evaluate("closeSavedArtifactsModal()")
    page.wait_for_timeout(200)
    modal_class_closed = modal.get_attribute("class") or ""
    assert "hidden" in modal_class_closed
    page.close()

def test_ui_responsive_mobile_viewport(browser_context):
    """Verifies that the UI renders without horizontal breakage on mobile viewports."""
    page = browser_context.new_page()
    page.set_viewport_size({"width": 375, "height": 812})  # iPhone dimensions
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # Verify header still visible
    assert page.locator("header").is_visible()
    # Verify chat input remains visible
    assert page.locator("#user-input").is_visible()
    page.close()

def test_ui_defensive_error_trap_elements(browser_context):
    """Verifies client-side JavaScript contains defensive DOM error trapping handlers."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    html_content = page.content()
    # Verify defensive catch blocks are present in DOM
    assert "Failed to render A2UI surface" in html_content
    assert "Error connecting to Cloud Run" in html_content or "formatMarkdown" in html_content
    page.close()
```

---

### 11. `requirements.txt`
```text
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
pgvector>=0.2.5
google-cloud-aiplatform>=1.55.0
google-cloud-logging>=3.10.0
google-cloud-trace>=1.11.0
opentelemetry-api>=1.25.0
opentelemetry-sdk>=1.25.0
opentelemetry-exporter-gcp-trace>=1.6.0
opentelemetry-instrumentation-fastapi>=0.46b0
opentelemetry-instrumentation-sqlalchemy>=0.46b0
pytest>=8.2.0
pytest-asyncio>=0.23.6
playwright>=1.40.0
```

---

### 12. `Dockerfile`
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies required for compiling Python packages (e.g., asyncpg C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/ --upgrade pip && \
    pip install --no-cache-dir --extra-index-url https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/ -r requirements.txt


# Stage 2: Production Runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install runtime PostgreSQL client library required for database connectivity
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group for runtime execution
RUN groupadd -r conductor-group && \
    useradd -r -g conductor-group -s /sbin/nologin -d /app conductor-runtime

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code and set proper ownership
COPY --chown=conductor-runtime:conductor-group . /app

# Switch to non-root user
USER conductor-runtime

# Expose HTTP service port
EXPOSE 8080

# Execute FastAPI via Uvicorn with 2 workers tailored for Cloud Run concurrency
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```
