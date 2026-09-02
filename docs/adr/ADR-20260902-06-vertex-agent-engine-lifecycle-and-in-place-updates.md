# Architectural Decision Record: Vertex AI Agent Engine Lifecycle and In-Place Updates

> **ADR ID:** ADR-20260902-06  
> **Status:** Accepted  
> **Date:** 2026-09-02  
> **Deciders:** Engineering Lead & Cloud Architecture Team  
> **Scope:** Vertex AI Agent Engine Infrastructure, Cloud Deploy Pipeline, and Metadata Governance  
> **Related:** [ADR-20260901-02](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260901-02-adk-go-agent-engine-migration.md), [ADR-20260902-05](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-05-cloud-deploy-private-pools-and-single-artifact-promotion.md)

---

## 1. Context and problem statement

During Conductor v3's Go ADK migration, multiple Vertex AI Agent Engine instances accumulated in project `riccardo-blog-test-v1`.

Two primary factors caused this resource sprawl:
1. **Decommissioned legacy instances**: Three Conductor v2 Python `cloudpickle` reasoning engines remained active after cutover.
2. **Missing rollout IDs in Skaffold**: [`skaffold-agent-engine.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/agent_engine/skaffold-agent-engine.yaml) only passed `--agent_engine_id` for the `dev` target. Every deployment to `staging` and `prod` provisioned a new reasoning engine instance rather than updating existing resources in-place.

This sprawl cluttered the Vertex AI Console with 11 instances, obscured active endpoints, and generated redundant microVM allocations.

---

## 2. Decision

We mandate a strict **1:1 instance-to-tier lifecycle policy** across Conductor v3 environments:

1. **Clean up legacy and orphaned instances**:
   * Decommission all legacy Python v2 reasoning engines (`6138588261280382976`, `99261160976547840`, and `1252182665583394816`).
   * Decommission intermediate orphaned v3.1.1 reasoning engines (`4718388674100723712`, `3921251540056145920`, `6227094549269839872`, and `7735800424438956032`).

2. **Retain one canonical instance per tier**:
   * **Dev**: `projects/105792947502/locations/us-central1/reasoningEngines/7652483831332601856` (`conductor-agent-dev`)
   * **Staging**: `projects/105792947502/locations/us-central1/reasoningEngines/313868238532378624` (`conductor-agent-agent-engine-staging`)
   * **Production**: `projects/105792947502/locations/us-central1/reasoningEngines/1423301859237429248` (`conductor-agent-agent-engine-prod`)

3. **Mandate in-place updates in Skaffold**:
   * Update [`skaffold-agent-engine.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/agent_engine/skaffold-agent-engine.yaml) to supply `--agent_engine_id` across Dev, Staging, and Production.
   * All future Cloud Deploy rollouts must execute in-place updates (`adk deploy agentengine --agent_engine_id=<ID>`).

4. **Synchronize deployment metadata**:
   * Update [`infra/agent_engine/deployed_engine.json`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/agent_engine/deployed_engine.json) to reference canonical v3 IDs exclusively.

---

## 3. Rationale

### A. Console clarity and governance
* A single agent per tier provides an intuitive 1:1:1 mapping in the Google Cloud Console.
* Operators and platform engineers immediately identify the active runtime instance for each environment.

### B. Deployment velocity and latency
* In-place microVM updates bypass cold provisioning, saving approximately 90 seconds per rollout.
* Existing network peering and IAM bindings persist across updates without reconfiguration.

### C. Deterministic endpoint binding
* Upstream callers, including the Go API Gateway and automated probers, maintain stable resource URIs.
* Eliminates configuration drift between Cloud Deploy releases and environment metadata.

---

## 4. Environment mapping

```
Google Cloud Deploy (conductor-agent-engine-pipeline)
   │
   ├──> Target: agent-engine-dev     ──> Reasoning Engine: 7652483831332601856 (in-place update)
   │
   ├──> Target: agent-engine-staging ──> Reasoning Engine: 313868238532378624  (in-place update)
   │
   └──> Target: agent-engine-prod    ──> Reasoning Engine: 1423301859237429248 (in-place update)
```

---

## 5. Consequences

### Positive
* Eliminates instance proliferation and reduces cloud infrastructure costs.
* Speeds up Cloud Deploy rollouts via consistent in-place updates.
* Establishes reliable, persistent resource identifiers for synthetic smoke tests.

### Negative
* Rollout failures during in-place updates require rolling back the existing instance rather than simply abandoning an ephemeral one.
* Operators must preserve canonical IDs in version-controlled pipeline manifests.
