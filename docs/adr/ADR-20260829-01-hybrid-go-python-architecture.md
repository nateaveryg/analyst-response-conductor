# Architectural Decision Record: Retention of hybrid Go and Python architecture

> **ADR ID:** ADR-20260829-01  
> **Status:** Superseded by [ADR-20260901-02](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260901-02-adk-go-agent-engine-migration.md)  
> **Date:** 2026-08-29 (Superseded: 2026-09-01)  
> **Deciders:** Engineering Lead & Cloud Architecture Team  
> **Scope:** Conductor v3 Core Runtime & Deployment Infrastructure

---

## 1. Context and problem statement

Conductor v3 uses Flutter (Dart) compiled to WebAssembly for its web frontend and Go for its high-performance backend API on Google Cloud Run. 

However, Python also exists within the codebase across two areas:
1. **AI reasoning microservice**: [`app/agent_engine/conductor_engine.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/agent_engine/conductor_engine.py)
2. **Delivery pipeline automation**: [`infra/agent_engine/deploy_agent_engine.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/agent_engine/deploy_agent_engine.py), [`render_agent_engine.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/agent_engine/render_agent_engine.py), and [`verify_agent_engine.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/agent_engine/verify_agent_engine.py)

The team evaluated whether Python should be eliminated entirely in favor of a pure Go architecture or retained in a hybrid model.

---

## 2. Decision

We will **retain the hybrid architecture** as currently designed:
* **Frontend**: Flutter Web (CanvasKit WebAssembly) served via Nginx Alpine on Cloud Run.
* **Core API & Gateway**: Pure Go static distroless binary on Cloud Run. Handles all client traffic, Model Armor DLP, and Cloud SQL pgvector queries.
* **AI Service Layer**: Vertex AI Agent Engine (Reasoning Engine) authored and packaged in Python.
* **Continuous Delivery**: Google Cloud Deploy Custom Target scripts in Python for Agent Engine lifecycle management.

---

## 3. Rationale

### A. Vertex AI Agent Engine runtime constraints
* Google Cloud's Reasoning Engine service is built upon a Python runtime environment.
* Packaging agents requires serializing Python classes via `cloudpickle` into Cloud Storage.
* Google Cloud currently offers **no Go SDK** to author, serialize, or provision Reasoning Engine microVMs.

### B. Complete isolation from user serving path
* Python is **not** on the user request path.
* The frontend talks directly to the Go backend via HTTP/2.
* Cloud Run cold starts (<40ms) and low memory footprints (<30MB) are preserved in production.

### C. Pipeline overhead is already mitigated
* Pipeline optimization **Option 1 (In-place updates)** cut microVM provisioning latency by 94 seconds.
* Pipeline optimization **Option 3 (Slim runner container)** reduced container image size by 88% (1.2 GB down to 146 MB), cutting image pull time to under 3 seconds.
* Pipeline optimization **Option A (Artifact Registry PyPI cache)** provides in-region package retrieval.

---

## 4. Architectural visual schematic

![ADR-20260829-01 Retention of Hybrid Go and Python Architecture](/usr/local/google/home/averyn/.gemini/jetski/brain/f0821df5-c0a3-48a6-a4db-72244c0853b9/adr_20260829_01_arch_1788133808687.jpg)

---

## 5. Alternatives evaluated and deferred

| Alternative | Technical Feasibility | Pros | Cons | Decision |
| :--- | :---: | :--- | :--- | :---: |
| **Pure Go Core (No Agent Engine)** | High | Eliminates Python entirely; 100% Go stack; unified toolchain. | Loses managed Vertex AI Agent Engine features (memory, sessions, orchestration). | **Deferred** |
| **Containerized Go Agent on Cloud Run** | High | Standard Cloud Run service; zero Python in deployment. | Requires building custom agent session and memory management in Go. | **Deferred** |
| **Hybrid Architecture (Current)** | Verified Live | Reuses managed Vertex AI services; zero Python on user path. | Requires maintaining Python packaging scripts for Cloud Deploy. | **Accepted** |

---

## 6. Tier-by-tier architectural alignment and change examples

Because Conductor v3 is decoupled across three architectural tiers, application changes are strictly isolated to their respective languages, runtimes, and delivery pipelines:

### Tier 1: Frontend Tier (Flutter Web & Nginx on Cloud Run)
* **Example change:** Adding a real-time RFI evaluation progress bar and export status badge.
* **Component modified:** Flutter UI widgets in `frontend/` and Nginx caching headers in [`infra/frontend/nginx.conf.template`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/frontend/nginx.conf.template).
* **Delivery pipeline:** [`cloudbuild-frontend.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/cloudbuild-frontend.yaml).
* **Isolation guarantee:** Modifies CanvasKit WebAssembly rendering and client presentation only; preserves backend API contracts and AI reasoning logic.

### Tier 2: Core API & Gateway Tier (Go on Cloud Run)
* **Example change:** Implementing Model Armor DLP regex redaction for confidential commercial discounts and rate-limiting middleware.
* **Component modified:** Governance middleware in [`backend/internal/governance/model_armor_dlp.go`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/backend/internal/governance/model_armor_dlp.go) and route registration in [`backend/internal/api/router.go`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/backend/internal/api/router.go).
* **Delivery pipeline:** [`cloudbuild-v3.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/cloudbuild-v3.yaml).
* **Isolation guarantee:** Enforces ingress request sanitization, authentication, and Cloud SQL pgvector connection pooling; shields the AI service layer from uninspected traffic without requiring Python or Flutter code changes.

### Tier 3: Managed AI Service & Data Tier (Python on Vertex AI Reasoning Engine)
* **Example change:** Adding a "FinOps & Cloud Financial Management" analyst taxonomy with automated SME routing.
* **Component modified:** Taxonomy rubrics and routing matrix in [`app/agent_engine/conductor_engine.py`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/agent_engine/conductor_engine.py).
* **Delivery pipeline:** [`cloudbuild-agent-engine.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/cloudbuild-agent-engine.yaml).
* **Isolation guarantee:** Adjusts cognitive reasoning rules, Gemini prompt synthesis, and SME routing (`finops-sme@google.com`) inside Vertex AI microVMs without altering the public Go gateway or requiring a frontend rebuild.

---

## 7. Future re-evaluation triggers

This architectural decision should be revisited if any of the following occur:
1. Google Cloud releases a native Go SDK for Vertex AI Reasoning Engine authoring.
2. The team decides to migrate all AI agent orchestration directly into the Go backend binary using the Google GenAI Go SDK.
3. Vertex AI Agent Engine introduces custom container runtimes for arbitrary compiled binaries.

---

## 8. Addendum: Superseded by ADR-20260901-02 (2026-09-01)

On 2026-09-01, Google Cloud Agent Development Kit (ADK) introduced support for Go (`google.golang.org/adk/v2`) and containerized Agent Runtime deployments to Vertex AI Agent Engine (`adk deploy agent_engine`). 

This fulfilled re-evaluation triggers 1 and 3 from Section 7:
* **Trigger 1**: ADK Go provides an official Go SDK for agent authoring and deployment.
* **Trigger 3**: Agent Runtime executes containerized OCI images, enabling static Go binaries.

As a result, Conductor v3 initiates the migration from Python to Go across all tiers under [ADR-20260901-02](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260901-02-adk-go-agent-engine-migration.md).

