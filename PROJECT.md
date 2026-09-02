# Project: Conductor v3 Release v3.3.1 Multi-Pipeline Delivery and Live Verification

## Architecture
- **Frontend Delivery Pipeline**: Dedicated lightweight Nginx Alpine container (`<20MB`, `Dockerfile.frontend`) packaging Flutter WebAssembly and CanvasKit assets with gzip compression, `application/wasm` MIME mapping, SPA fallback routing, and release `version.json` (version `3.3.1`, marker `v3.3.1-verified`). Deployed via `cloudbuild-frontend.yaml` and `conductor-v3-frontend-pipeline` across `dev`, `staging`, and `prod`.
- **Backend Cloud Run Pipeline**: Static Go binary container (`Dockerfile.v3`, Distroless nonroot, `<35MB`) with Model Armor DLP governance, Cloud SQL PostgreSQL 16 connectivity, and operational endpoints (`/health`, `/ready`). Deployed via `cloudbuild-v3.yaml` and `conductor-v3-pipeline` to Cloud Run.
- **Vertex AI Agent Engine Pipeline**: Hermetic container packaging Go AI microservice (`backend/Dockerfile`), validated with Pytest contract suites and deployed via `cloudbuild-agent-engine.yaml` and `conductor-agent-engine-pipeline`.
- **Supply Chain Security & SBOM Generation**: In-pipeline generation of Syft SPDX 2.3 `sbom.spdx.json`, registration of SBOM occurrences in Google Artifact Analysis (`gcloud artifacts sbom load`), and archival to Google Cloud Storage (`gs://riccardo-blog-test-v1_cloudbuild/sboms/${BUILD_ID}`).
- **Continuous Delivery & Verification**: Google Cloud Deploy delivery pipelines with built-in post-deploy verification (`infra/frontend/verify_frontend.py` 6/6 checks) gating automated promotion from `dev` to `staging` (`infra/frontend/automations.yaml`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Survey & Technical Assessment | Comprehensive survey of build manifests, deploy configs, and probers | M1 | Survey Reports |
| 2 | Live Frontend Cloud Build Submission | Submit `cloudbuild-frontend.yaml` with timestamped `_COMMIT_SHA` via ADC | M2 | R1, Build Explorer |
| 3 | Live Backend Cloud Run Build Submission | Submit `cloudbuild-v3.yaml` with timestamped `_COMMIT_SHA` via ADC | M2 | R1, Build Explorer |
| 4 | Live Agent Engine Build Submission | Submit `cloudbuild-agent-engine.yaml` with `COMMIT_SHA` and `SHORT_SHA` via ADC | M2 | R1, Build Explorer |
| 5 | Immutable Container Image Publishing | Publish images to `us-central1-docker.pkg.dev/riccardo-blog-test-v1/conductor-repo/` | M2 | R2, Build Explorer |
| 6 | Syft SPDX 2.3 SBOM Generation | Generate `sbom.spdx.json` manifests in-pipeline using Syft v1.18.1 | M2 | R2, Build Explorer |
| 7 | Artifact Analysis SBOM Occurrence Loading | Ingest SBOM occurrences via `gcloud artifacts sbom load` for published images | M2 | R2, Build Explorer |
| 8 | Cloud Storage SBOM Archiving | Archive SBOM files to `gs://riccardo-blog-test-v1_cloudbuild/sboms/${BUILD_ID}` | M2 | R2, Build Explorer |
| 9 | Cloud Build Execution Status | Verify all three remote build executions finish with `STATUS: SUCCESS` | M2 | R2, Build Explorer |
| 10 | Frontend Cloud Deploy dev Rollout & Verify | Monitor `conductor-v3-frontend-pipeline` rollout to `dev` with `verify_frontend.py` | M3 | R3, Deploy Miner |
| 11 | Frontend Automated Staging Promotion | Verify automated promotion rule triggers rollout to `staging` upon passing dev | M3 | R3, Deploy Miner |
| 12 | Backend Cloud Run dev Rollout | Monitor `conductor-v3-pipeline` release rollout to `dev` target on Cloud Run | M3 | R3, Deploy Miner |
| 13 | Agent Engine Release Rollout | Monitor `conductor-agent-engine-pipeline` release creation and rollout | M3 | R3, Deploy Miner |
| 14 | Live Frontend Version & Marker Probe | Probe `https://conductor-v3-frontend-dev-4izasuhqpq-uc.a.run.app/version.json` (3.3.1, v3.3.1-verified) | M4 | R4, Prober Miner |
| 15 | Live 6/6 Frontend Prober Verification | Execute `infra/frontend/verify_frontend.py --env dev` against live Cloud Run | M4 | R4, Prober Miner |
| 16 | Live Backend Health & Status Probing | Probe `/health` and `/ready` on `conductor-v3-dev` Cloud Run service | M4 | R4, Prober Miner |
| 17 | Multi-Reviewer, Challenger & Audit Gating | Independent review, adversarial challenge, and Forensic Integrity Audit verification | M5 | Audit Framework |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Survey & Technical Assessment | Survey Cloud Build manifests, Cloud Deploy pipelines, probers | None | DONE |
| M2 | Live Cloud Build & Supply Chain | Submit 3 builds, verify container images, Syft SBOMs, Artifact Analysis, GCS archiving | M1 | DONE |
| M3 | Cloud Deploy Release & Rollouts | Monitor releases, dev rollouts, verify hooks, auto-promotion to staging | M2 | DONE |
| M4 | Live Endpoint & Prober Verification | Verify version.json (3.3.1), verify_frontend.py 6/6 pass, backend health/ready | M3 | DONE |
| M5 | Quality & Forensic Integrity Gating | Reviewer APPROVE, Challenger confirmation, Forensic Auditor CLEAN verdict | M4 | DONE |


## Interface Contracts
### CLI Build Submission Interface
- Submissions execute with Application Default Credentials:
  `CLOUDSDK_AUTH_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"`
- Unified substitution variables:
  `--substitutions=_COMMIT_SHA="${REL}",COMMIT_SHA="${REL}",_SHORT_SHA="${SHORT_REL}",SHORT_SHA="${SHORT_REL}"`
- Target project: `riccardo-blog-test-v1`, region: `us-central1`.

### Supply Chain & Artifact Interface
- Artifact Registry Repository: `us-central1-docker.pkg.dev/riccardo-blog-test-v1/conductor-repo/`
  - `conductor-v3-frontend:${_COMMIT_SHA}`
  - `conductor-v3:${_COMMIT_SHA}`
  - `conductor-backend-v3:${COMMIT_SHA}`
- SBOM standard: SPDX 2.3 JSON (`sbom.spdx.json`) generated by Anchore Syft v1.18.1.
- SBOM Storage: `gs://riccardo-blog-test-v1_cloudbuild/sboms/${BUILD_ID}/sbom.spdx.json`.
- Artifact Analysis: Ingested occurrences loaded via `gcloud artifacts sbom load`.

### Cloud Deploy Delivery & Verification Interface
- Delivery Pipelines:
  - `conductor-v3-frontend-pipeline`: Stages `dev` (verify enabled) ➔ `staging` (verify enabled) ➔ `prod` (canary 25%, 50%, stable).
  - `conductor-v3-pipeline`: Stages `dev` ➔ `staging` ➔ `prod` (canary 25%, 50%, stable).
  - `conductor-agent-engine-pipeline`: Target `agent-engine-custom-target`.
- Automation: `conductor-v3-frontend-pipeline/auto-promote-dev-to-staging` promotes release to staging when dev rollout achieves `SUCCEEDED` status with verifyJob passing.

### Live Endpoints & Prober Interface
- Frontend Dev URL: `https://conductor-v3-frontend-dev-4izasuhqpq-uc.a.run.app`
  - `GET /version.json`: HTTP 200, JSON containing `"version": "3.3.1"` and `"verification_marker": "v3.3.1-verified"`.
  - 6/6 checks in `infra/frontend/verify_frontend.py --env dev`: `/health`, `/`, `/main.dart.wasm`, `/main.dart.js`, `/index.html` (gzip), `/workspace/rfi-analysis/deep-link` (SPA fallback).
- Backend Dev URL: `https://conductor-v3-dev-4izasuhqpq-uc.a.run.app`
  - `GET /health`: HTTP 200, status `"healthy"`.
  - `GET /ready`: HTTP 200, database `"connected"`.

## Code Layout
- Build Manifests: `cloudbuild-frontend.yaml`, `cloudbuild-v3.yaml`, `cloudbuild-agent-engine.yaml`
- Deploy Manifests: `clouddeploy-frontend.yaml`, `clouddeploy-v3.yaml`, `infra/frontend/automations.yaml`, `skaffold-frontend.yaml`, `skaffold-v3.yaml`, `infra/agent_engine/skaffold-agent-engine.yaml`
- Source Code:
  - Frontend: `frontend/build/web/version.json`, `frontend/pubspec.yaml`, `Dockerfile.frontend`, `infra/frontend/nginx.conf.template`
  - Backend: `backend/cmd/server/main.go`, `backend/internal/api/router.go`, `backend/Dockerfile`, `Dockerfile.v3`
- Verification Probers: `infra/frontend/verify_frontend.py`, `test_live_frontend_verification.py`

