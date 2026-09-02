# Architectural Decision Record: Retention of Permanent Dev Tier and Production Canary Evaluation

> **ADR ID:** ADR-20260902-07  
> **Status:** Accepted  
> **Date:** 2026-09-02  
> **Deciders:** Engineering Lead & Cloud Architecture Team  
> **Scope:** Multi-Tier Environment Topology, CI/CD Progression, and AI Evaluation Strategy  
> **Related:** [ADR-20260829-02](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260829-02-cloud-deploy-verification-and-automations.md), [ADR-20260902-05](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-05-cloud-deploy-private-pools-and-single-artifact-promotion.md), [ADR-20260902-06](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-06-vertex-agent-engine-lifecycle-and-in-place-updates.md)

---

## 1. Context and problem statement

The engineering team evaluated whether to consolidate Conductor v3's deployment topology from three tiers (Dev, Staging, Production) down to two tiers (Staging $\to$ Production Canary).

The evaluation weighed two competing considerations:
1. **Semantic evaluation divergence**: Lower environments (Dev and Staging) use static prompt fixtures and mocked vector databases. They cannot faithfully mirror production semantic quality, hallucination rates, or live user query distributions.
2. **Frontend full-stack dependency**: The Flutter Web frontend client (`conductor-v3-frontend-dev`) requires an active, live backend and Agent Engine to render streaming tokens, intermediate stage spinners, and client-side error states.

Eliminating Dev would force frontend testing into Staging, risking disruption to pre-production release validation and automated promotion rules.

---

## 2. Decision

We will **retain the permanent canonical Dev tier** alongside Staging and Production. We define distinct evaluation responsibilities for each tier:

1. **Dev Tier (Developer Velocity & Full-Stack Pairing)**:
   * **Role**: Rapid prototyping, full-stack vertical integration (Frontend $\leftrightarrow$ Gateway $\leftrightarrow$ Agent Engine), and shift-left infrastructure testing.
   * **Scope**: Validates UI streaming behavior, token buffering, and client state handling against active Go and ADK services.
   * **Hygiene**: Enforces exactly one canonical instance per tier with in-place updates to avoid resource sprawl.

2. **Staging Tier (Operational & Contract Gate)**:
   * **Role**: Pre-production dress rehearsal and automated release candidate qualification.
   * **Scope**: Validates Go binary compilation, container startup, sub-500ms cold starts, and Model Armor DLP policy enforcement.
   * **Promotion**: Serves as the launchpad for automated promotion rules (`promoteReleaseRule`).

3. **Production Canary (Semantic & User Quality Gate)**:
   * **Role**: Real-world evaluation against live customer queries and updated vector databases.
   * **Scope**: Progressive traffic shaping (25% $\to$ 50% $\to$ 100% stable) monitoring live response confidence, user feedback, and semantic quality.
   * **Safety**: Automated rollbacks halt deployment if error rates spike or grounding thresholds fail.

---

## 3. Rationale

### A. Full-stack frontend enablement
* Flutter Web client developers require live streaming endpoints to test user interfaces.
* Static mocks fail to expose real streaming latency, token chunking, and network dropouts.
* A live Dev Agent Engine provides authentic streaming without exposing unreleased code to Staging.

### B. Isolation of release candidates
* Staging acts as an immutable integration gate governed by automated Cloud Deploy automations.
* Running experimental prompt changes or schema refactors in Staging risks triggering false rollouts.
* Retaining Dev keeps experimental failures strictly contained within a non-production blast radius.

### C. Tier responsibility alignment
* Lower tiers verify deterministic system mechanics (APIs, contracts, and security policies).
* Production canaries verify non-deterministic AI behavior (grounding, semantics, and relevance).
* This separation prevents false confidence from static tests while protecting production users.

---

## 4. Architectural topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Dev Tier: Developer Velocity & Full-Stack Pairing                        │
│    conductor-v3-frontend-dev ──> conductor-v3-dev ──> conductor-agent-dev   │
│    (Validates streaming UX, token rendering, and infrastructure changes)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Git Commit to main
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Staging Tier: Operational & Contract Gate                                │
│    conductor-v3-frontend-staging ──> conductor-v3-staging ──> Staging Agent │
│    (Validates cold starts, JSON contracts, and Model Armor DLP policies)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Automated Release Promotion
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Production Tier: Progressive Canary & Semantic Gate                      │
│    Canary 25% ──> Canary 50% ──> 100% Stable Traffic                        │
│    (Evaluates live grounding, user queries, and automated rollback gates)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Consequences

### Positive
* Frontend developers retain immediate live feedback for streaming UI features.
* Staging remains stable, predictable, and protected from experimental breakage.
* Cloud Run and Vertex AI microVM scale-to-zero capabilities keep idle Dev costs near zero.
* Live AI responses are evaluated where it matters most: under real production traffic.

### Negative
* Requires maintaining target configurations across three environments in Cloud Deploy manifests.
* Pipeline configurations must preserve canonical IDs to prevent instance proliferation.
