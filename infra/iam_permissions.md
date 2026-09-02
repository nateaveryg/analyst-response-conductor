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

## gcloud Provisioning Commands

Run the following commands to provision the service account and bind the necessary IAM roles:

```bash
# Set variables
export VERTEX_AI_PROJECT="your-gcp-project-id"
export SERVICE_ACCOUNT="conductor-agent"
export SA_EMAIL="${SERVICE_ACCOUNT}@${VERTEX_AI_PROJECT}.iam.gserviceaccount.com"

# 1. Create the dedicated service account
gcloud iam service-accounts create ${SERVICE_ACCOUNT} \
    --project=${VERTEX_AI_PROJECT} \
    --display-name="Analyst Response Agent (ARA) Runtime Agent"

# 2. Grant roles/aiplatform.user
gcloud projects add-iam-policy-binding ${VERTEX_AI_PROJECT} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user"

# 3. Grant roles/cloudsql.client
gcloud projects add-iam-policy-binding ${VERTEX_AI_PROJECT} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"

# 4. Grant roles/secretmanager.secretAccessor
gcloud projects add-iam-policy-binding ${VERTEX_AI_PROJECT} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# 5. Grant roles/logging.logWriter
gcloud projects add-iam-policy-binding ${VERTEX_AI_PROJECT} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.logWriter"

# 6. Grant roles/cloudtrace.agent
gcloud projects add-iam-policy-binding ${VERTEX_AI_PROJECT} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtrace.agent"
```

---

## Workload Identity Binding for Cloud Run

When deploying the Cloud Run service, ensure `--service-account=${SA_EMAIL}` is explicitly passed so the container inherits this exact IAM posture without requiring physical JSON service account keys.
