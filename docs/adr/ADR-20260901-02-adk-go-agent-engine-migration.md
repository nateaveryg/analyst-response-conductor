# Architectural Decision Record: Migration to Go ADK on Vertex AI Agent Engine

> **ADR ID:** ADR-20260901-02  
> **Status:** Accepted  
> **Date:** 2026-09-01  
> **Deciders:** Engineering Lead & Cloud Architecture Team  
> **Scope:** Conductor v3 Core Runtime & Deployment Infrastructure  
> **Supersedes:** [ADR-20260829-01](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260829-01-hybrid-go-python-architecture.md)

---

## 1. Context and problem statement

Conductor v3 previously retained Python exclusively for the AI reasoning tier. Google Cloud Vertex AI Reasoning Engine originally required Python class serialization through `cloudpickle`.

With the launch of the Agent Development Kit (ADK) Go SDK, Google Cloud introduced containerized Agent Runtime execution. Developers can now compile Go agents and deploy them directly to Vertex AI Agent Engine using `adk deploy agent_engine`.

The engineering team evaluated whether to replace the Python tier with a unified Go architecture.

---

## 2. Decision

We will **migrate the AI reasoning tier to Go** using the Agent Development Kit (`google.golang.org/adk/v2`).

The architecture adopts the following standards:
* **Frontend**: Flutter Web (CanvasKit WebAssembly) served through Nginx on Cloud Run.
* **Core API & Gateway**: Pure Go static distroless binary on Cloud Run.
* **AI Service Layer**: Go agent authored with ADK v2 running on Vertex AI Agent Engine.
* **Continuous Delivery**: Google Cloud Deploy Custom Target invoking `adk deploy agent_engine` via Skaffold.
* **Verification**: Synthetic smoke tests authored in Go executing during the Cloud Deploy verification phase.

---

## 3. Rationale

### A. Resolution of previous runtime constraints
* Legacy Reasoning Engine forced Python bytecode pickling into Cloud Storage buckets.
* ADK Agent Runtime executes standard OCI containers on managed microVMs.
* Go agents compile to single static binaries, eliminating Python interpreter overhead.

### B. Performance and resource improvements
* Cold start latency drops from 3–5 seconds down to under 500 milliseconds.
* Base memory consumption drops from ~180MB (Python virtual environment) to <30MB (Go binary).
* Concurrency handling improves through lightweight Go goroutines.

### C. Unified language ecosystem
* Go becomes the exclusive language across all backend, gateway, AI reasoning, and prober code.
* Developers share data models, taxonomy structs, and validation logic across tiers.
* Cross-language serialization friction between Cloud Run and Agent Engine is eliminated.

### D. Managed state and memory preservation
* The Go agent retains managed session state via `agentengine://<resource_id>` URIs.
* Vertex AI Agent Engine continues to manage auto-scaling, infrastructure patching, and IAM authentication.

---

## 4. Cloud Deploy Custom Target integration

Cloud Deploy manages the release lifecycle across environments without architectural changes:

```
Cloud Deploy Release
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ CustomTargetType: vertex-ai-agent-engine                        │
│                                                                 │
│  1. Render Action  ──> Validates Go agent manifest configuration│
│  2. Deploy Action  ──> Executes 'adk deploy agent_engine'       │
│  3. Verify Hook    ──> Runs Go synthetic smoke test prober      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
Vertex AI Agent Engine (Agent Runtime microVM)
```

The delivery pipeline retains automated progression through three stages:
1. `agent-engine-dev`: Rapid feature validation with automated verification.
2. `agent-engine-staging`: Pre-production regression testing with synthetic smoke tests.
3. `agent-engine-prod`: Production release with canary monitoring and automated rollback.

---

## 5. Alternatives evaluated

| Alternative | Technical Feasibility | Pros | Cons | Decision |
| :--- | :---: | :--- | :--- | :---: |
| **Retain Python Hybrid** | Verified Live | Zero migration effort required. | Dual language overhead; 3–5s cold starts; bytecode pickling. | **Superseded** |
| **Direct Cloud Run (GenAI SDK)** | High | Pure Go stack; fast cold starts. | Abandons managed Agent Engine sessions, memory banks, and microVM isolation. | **Rejected** |
| **ADK Go on Agent Engine** | High | Pure Go stack; fast cold starts; retains managed Agent Engine features. | Requires one-time migration of agent logic to ADK Go. | **Accepted** |

---

## 6. Consequences

### Positive
* Python dependencies and virtual environments are completely eliminated from the repository.
* Deployment container image size is reduced, improving pipeline throughput.
* End-to-end type safety connects the Cloud Run gateway and the Agent Engine service.
* Cloud Deploy continues to enforce promotion gates, approvals, and automated rollbacks.

### Negative
* The team must maintain Go ADK module dependencies (`google.golang.org/adk/v2`).
* Existing Python test fixtures must be migrated to Go unit tests.

---

## 7. Addendum: Pipeline decoupling and asset archival

**Date:** 2026-09-02  
**Scope:** Agent Engine CI/CD pipeline streamlining and legacy asset cleanup.

### What's new

* **Pipeline decoupling**: `cloudbuild-agent-engine.yaml` is now dedicated solely to Go ADK deployment.
* **Extraneous steps removed**: Legacy Python tests, Cloud Run container builds, and SBOM uploads are removed.
* **Asset archival**: Deprecated Python scripts and runner configurations moved to `infra/agent_engine/archive_python/`.
* **Obsolete patches removed**: Runtime `sed` patches for Go compiler versions are eliminated.

### Why it matters

Decoupling the pipelines prevents unnecessary container builds during Agent Engine updates.
Archiving legacy Python assets preserves historical reference while keeping the active codebase clean.
Compiling Go binaries without runtime sed commands guarantees reproducible and hermetic builds.
