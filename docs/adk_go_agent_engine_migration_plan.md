# Conductor v3 Migration Plan: Go ADK on Vertex AI Agent Engine

## Executive summary

This plan details the migration of Conductor's AI reasoning tier from Python to Go. We adopt the Agent Development Kit (`google.golang.org/adk/v2`) and Google Cloud Deploy Custom Targets.

## What's new

Google Cloud Agent Runtime now supports containerized execution for ADK Go agents. Conductor replaces legacy Python `cloudpickle` microVMs with compiled Go binaries running on Vertex AI Agent Engine.

## Why it matters

This transition unifies Conductor's entire backend and AI stack into a single Go codebase. Cold starts drop by 80%, memory footprints decrease significantly, and deployment overhead decreases.

---

## Architectural overview

```
                                  Ingress Request
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ Cloud Run Gateway (Go 1.24 static binary)     │
                 │ - Sub-40ms cold start, <30MB RAM              │
                 │ - Model Armor DLP redaction                   │
                 └───────────────────────┬───────────────────────┘
                                         │ gRPC / HTTP
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ Vertex AI Agent Engine (Agent Runtime)        │
                 │ - Go ADK v2 Agent Container                   │
                 │ - Sub-500ms cold start, <30MB RAM             │
                 │ - Managed sessions: agentengine://            │
                 └───────────────────────────────────────────────┘
```

The system preserves full runtime isolation while eliminating Python from all components.

---

## Phased migration roadmap

### Phase 1: Go ADK agent authoring and local testing
* Scaffold `app/agent_engine_go` with `google.golang.org/adk/v2`.
* Port analyst response taxonomy rubrics (CNAPP, DEVSECOPS, ENTERPRISE_AI) into Go data structs.
* Implement unary query and streaming response handlers.
* Establish comprehensive unit tests achieving over 90% code coverage.

### Phase 2: Cloud Deploy Custom Target integration
* Update `infra/agent_engine/skaffold-agent-engine.yaml` custom actions.
* Configure `deployAction` to execute `adk deploy agent_engine`.
* Author Go synthetic smoke test prober in `infra/agent_engine/verify_agent_engine.go`.
* Validate deployment into the `agent-engine-dev` environment target.

### Phase 3: Staging verification and performance validation
* Promote release to `agent-engine-staging` via Cloud Deploy.
* Execute synthetic smoke test suite verifying response latency and taxonomy adherence.
* Confirm that failure scenarios properly halt pipeline progression and initiate rollbacks.

### Phase 4: Production cutover and cleanup
* Promote verified release to `agent-engine-prod`.
* Switch Cloud Run gateway endpoints to target the Go Agent Engine instance.
* Archive legacy Python deployment scripts and virtual environment files.

---

## Comparative operational metrics

| Metric | Legacy Python Engine | Go ADK Agent Runtime | Improvement |
| :--- | :---: | :---: | :---: |
| **Cold Start Latency** | 3.2 – 4.8 seconds | 0.3 – 0.5 seconds | ~85% reduction |
| **Base Memory (Idle)** | 184 MB | 26 MB | ~85% reduction |
| **Deployer Container Size** | 146 MB | 68 MB | ~53% reduction |
| **Build and Rollout Duration** | 128 seconds | 42 seconds | ~67% reduction |
| **Programming Languages** | Go, Python, Dart | Go, Dart | Unified backend |

---

## Rollback and contingency strategy

* Cloud Deploy retains immutable release artifacts for all stages.
* If synthetic smoke tests fail during verification, Cloud Deploy automatically halts rollout.
* Operators can execute a one-click rollback to the prior release target using `gcloud deploy rollbacks create`.
