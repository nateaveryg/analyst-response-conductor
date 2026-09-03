# Conductor v3 Architectural Decision Records (ADRs)

This directory maintains the formal Architectural Decision Records (ADRs) governing Conductor v3's architecture, delivery pipelines, and governance standards.

---

## Index of decisions

| ADR ID | Date | Title | Status | Scope |
| :--- | :---: | :--- | :---: | :--- |
| [**ADR-20260829-01**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260829-01-hybrid-go-python-architecture.md) | 2026-08-29 | **Retention of Hybrid Go and Python Architecture** | Accepted | Go Backend on Cloud Run vs. Python Reasoning Engine on Vertex AI; Tier-by-tier change examples. |
| [**ADR-20260829-02**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260829-02-cloud-deploy-verification-and-automations.md) | 2026-08-29 | **Cloud Deploy Verification and Automated Stage Promotion** | Accepted | Verification prober hooks, automated stage progression from Dev to Staging, and manual canary gates for Production. |
| [**ADR-20260829-03**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260829-03-in-pipeline-sbom-generation.md) | 2026-08-29 | **In-Pipeline Software Bill of Materials (SBOM) Generation** | Accepted | Syft SPDX 2.3 JSON generation, Google Artifact Analysis occurrence registration, and Cloud Storage archival. |
| [**ADR-20260831-04**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260831-04-application-gateway-vs-agent-platform-gateway.md) | 2026-08-31 | **Differentiation between Application Gateway and Agent Platform Gateway** | Accepted | Layer 7 Application Backend on Cloud Run vs. Google Cloud Managed L4/L7 Agent Platform Gateway (AGW). |
| [**ADR-20260901-02**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260901-02-adk-go-agent-engine-migration.md) | 2026-09-01 | **Migration to Go ADK on Vertex AI Agent Engine** | Accepted | Go ADK v2 migration, elimination of Python serialization, and Cloud Deploy custom target integration. |
| [**ADR-20260902-05**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-05-cloud-deploy-private-pools-and-single-artifact-promotion.md) | 2026-09-02 | **Cloud Deploy Private Worker Pools & Single-Artifact Promotion** | Accepted | Single immutable container build across Dev/Staging/Prod, dedicated private worker pools, and manifest parameterization. |
| [**ADR-20260902-06**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-06-vertex-agent-engine-lifecycle-and-in-place-updates.md) | 2026-09-02 | **Vertex AI Agent Engine Lifecycle & In-Place Updates** | Accepted | Strict 1:1 tier mapping, removal of orphaned instances, and mandatory in-place updates via Skaffold. |
| [**ADR-20260902-07**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-07-three-tier-environment-strategy-and-canary-evaluation.md) | 2026-09-02 | **Retention of Dev Tier & Production Canary Evaluation** | Accepted | Dedicated Dev pairing for Flutter Web frontend, Staging operational gate, and live semantic evaluation in Production Canaries. |
| [**ADR-20260903-08**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260903-08-production-canary-agent-evaluation.md) | 2026-09-03 | **Production Canary Agent Evaluation** | Accepted | Embed evaluation in canary verify phases, custom deterministic scorers, Vertex AI Experiments tracking, and automated rollback gates. |

---

## Architectural visual references

* [**ADR-01 Hybrid Architecture Diagram**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr_20260829_01_arch.jpg)
* [**ADR-04 Core Distinction Gateway Diagram**](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/core_distinction_arch.jpg)
