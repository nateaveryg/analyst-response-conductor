# Google Cloud Dev2Prod CI/CD Pipeline Specification (`rficonductorv2`)

This document outlines the complete Google Cloud Development-to-Production (Dev2Prod) continuous integration and continuous delivery pipeline for the **Analyst Response Agent (ARA / Conductor v2)**.

---

## 🏗️ Architecture & Component Flow

```
+-----------------------------------------------------------------------------------+
| Continuous Integration (CI) - Google Cloud Build                                  |
| 1. Run unit/integration tests (.venv / python 3.11 with pytest)                   |
| 2. Build multi-stage container image from Dockerfile                              |
| 3. Push immutable versioned image (${COMMIT_SHA}) to Artifact Registry            |
| 4. Security vulnerability scanning via Artifact Analysis / Container Analysis    |
| 5. Create Release in Google Cloud Deploy                                          |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| Continuous Delivery (CD) - Google Cloud Deploy                                    |
| Pipeline: conductor-v2-pipeline (us-central1)                                     |
|                                                                                   |
|  [Stage 1: Dev] ──► Deploy to Cloud Run (dev)                                     |
|                      └──► Post-Deploy Verification Hook (Live E2E Verification)    |
|                              │                                                    |
|  [Stage 2: Staging] ◄────────┘ (Auto-promoted or CLI promotion)                   |
|          └──► Deploy to Cloud Run (staging)                                       |
|                └──► Post-Deploy Verification Hook (Live E2E Verification)         |
|                        │                                                          |
|  [Stage 3: Prod] ◄─────┘ (Requires Explicit Approval Gate)                        |
|          └──► Canary Rollout: 25% ➔ 50% ➔ 100% Traffic Progression                |
|                └──► Post-Deploy Canary Health Verification                        |
+-----------------------------------------------------------------------------------+
```

---

## 📋 Required Google Cloud APIs

Ensure the following APIs are enabled in your Google Cloud Project (`riccardo-blog-test-v1`):

```bash
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
```

---

## 📦 1. Artifact Registry Setup

Create the Docker artifact repository:

```bash
export PROJECT_ID="riccardo-blog-test-v1"
export REGION="us-central1"
export REPO_NAME="conductor-repo"

gcloud artifacts repositories create ${REPO_NAME} \
    --project=${PROJECT_ID} \
    --location=${REGION} \
    --repository-format=docker \
    --description="Docker repository for Conductor v2 agent images"
```

---

## 🔐 2. Service Accounts & IAM Permissions

### A. Cloud Build Service Account Permissions
Grant Cloud Build permissions to trigger Cloud Deploy releases and access Artifact Registry:

```bash
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
```

### B. Cloud Deploy Service Account Permissions
Grant Cloud Deploy permissions to deploy to Cloud Run:

```bash
export CD_SA="service-$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')@gcp-sa-clouddeploy.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${CD_SA}" \
    --role="roles/run.developer"
```

---

## 🚀 3. Registering the Cloud Deploy Pipeline & Targets

Apply the delivery pipeline and targets defined in `clouddeploy.yaml`:

```bash
gcloud deploy apply \
    --file=clouddeploy.yaml \
    --region=us-central1 \
    --project=riccardo-blog-test-v1
```

Verify the pipeline status:

```bash
gcloud deploy delivery-pipelines describe conductor-v2-pipeline \
    --region=us-central1 \
    --project=riccardo-blog-test-v1
```

---

## 🔄 4. Triggering Releases

### Option A: Via Google Cloud Build (Recommended for CI/CD)
When code is pushed to your source repository, Cloud Build executes `cloudbuild.yaml`:
```bash
gcloud builds submit --config=cloudbuild.yaml --project=riccardo-blog-test-v1 .
```

### Option B: Via Local Automation Script
```bash
DEPLOY_METHOD=cloud-deploy bash infra/deploy_cloud_run.sh
```

---

## 🛡️ 5. Cloud Deploy Stage Promotion & Approval

To promote a release from `dev` to `staging`:
```bash
gcloud deploy releases promote \
    --release="release-<TAG>" \
    --delivery-pipeline="conductor-v2-pipeline" \
    --region="us-central1"
```

To approve promotion into `prod`:
```bash
gcloud deploy rollouts approve <ROLLOUT_NAME> \
    --delivery-pipeline="conductor-v2-pipeline" \
    --region="us-central1"
```
