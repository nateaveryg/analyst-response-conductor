# Architectural Decision Record: Differentiation between Application Gateway and Agent Platform Gateway

> **ADR ID:** ADR-20260831-04  
> **Status:** Accepted  
> **Date:** 2026-08-31  
> **Deciders:** Engineering Lead & Cloud Architecture Team  
> **Scope:** Conductor v3 Network Architecture, Ingress/Egress Routing, and Tool Governance

---

## 1. Context and problem statement

Conductor v3 deploys a high-performance Go backend service on Google Cloud Run serving client APIs, Model Armor DLP, and Cloud SQL pgvector database connections.

Concurrently, Google Cloud offers **Agent Platform Gateway (AGW)** within the Gemini Enterprise Agent Platform and Vertex AI Agent Engine ecosystem to govern agentic connectivity.

Because both components perform routing, security validation, and policy checks, the team addressed potential ambiguity regarding functional overlap:
1. Is Go on Cloud Run redundant if Agent Platform Gateway is available?
2. How do their responsibilities divide across application-layer logic and infrastructure-layer network proxies?

---

## 2. Decision

We affirm that **Go on Cloud Run** and **Agent Platform Gateway (AGW)** serve distinct, non-overlapping, and complementary functions:

1. **Go on Cloud Run serves as the Application API Gateway & Backend:**
   * Acts as the public ingress boundary for human users and web browsers (Flutter Web client over HTTP/2 REST and SSE).
   * Manages end-user authentication, tenant context, and stateful session lifecycles.
   * Directly manages the `pgx` connection pool to Cloud SQL PostgreSQL for semantic search, vector embeddings, and RAG document storage.
   * Performs pre-LLM application-level Data Loss Prevention (DLP) via Google Model Armor before routing requests to AI microservices.

2. **Agent Platform Gateway (AGW) serves as the Managed Network & Tool Proxy:**
   * Acts as the private egress boundary for Vertex AI Agent Engine (Reasoning Engine microVMs).
   * Governs Agent-to-Tools (ATT) and Agent-to-Agent (A2A) interactions.
   * Enforces infrastructure-layer protocol security for Model Context Protocol (MCP) servers, mTLS identity certificates, and Private Service Connect (PSC) routing.
   * Enforces tool-level authorization policies (e.g. read-only tool restrictions) at the network packet level.

---

## 3. Architectural visual schematic

![Core Distinction: Go on Cloud Run vs. Agent Platform Gateway](/usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/core_distinction_arch.jpg)

---

## 4. Detailed comparison matrix

| Architectural Dimension | Go on Cloud Run (Application Tier) | Agent Platform Gateway (Infrastructure Tier) |
| :--- | :--- | :--- |
| **Primary role** | **Application Gateway & Core Backend** | **Agentic Network & Tool Proxy (PEP)** |
| **OSI model level** | Layer 7 Application Software | Layer 4 / Layer 7 Network Proxy Infrastructure |
| **Traffic direction** | **Ingress:** Browser / Client to Backend | **Egress & East-West:** Agent to Tools / Agents |
| **Primary clients** | End users, web browsers, mobile applications | AI agents, autonomous models, reasoning engines |
| **Data & state access** | Holds Cloud SQL `pgx` pool, executes SQL migrations | Stateless network proxy; zero database access |
| **Key protocols** | HTTP/2, REST, Server-Sent Events (SSE), JSON | Model Context Protocol (MCP), mTLS, DPoP, PSC |
| **DLP & Model Armor** | Sanitizes user prompts before LLM submission | Inspects tool inputs and outputs at the packet level |
| **Deployment ownership** | Compiled Distroless container in customer project | Google Cloud Service Networking shared tenant proxy |
| **Delivery pipeline** | [`cloudbuild-v3.yaml`](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/cloudbuild-v3.yaml) (Cloud Deploy) | Declarative Google Cloud resource / Terraform |

---

## 5. End-to-end operational workflow

1. **User interaction:** The user interacts with the Flutter Web interface. The browser dispatches an HTTP/2 REST request to **Go on Cloud Run**.
2. **Application gateway validation:**
   * The Go backend authenticates the user credentials.
   * Queries Cloud SQL pgvector for contextual document embeddings.
   * Executes Model Armor DLP prompt sanitization.
3. **Reasoning engine invocation:** The Go service invokes **Vertex AI Agent Engine** via internal RPC.
4. **Governed tool invocation:**
   * If Agent Engine requires external data (e.g. BigQuery or an external MCP server), outbound traffic passes through **Agent Platform Gateway**.
   * Agent Platform Gateway validates mTLS agent identity, verifies tool allowlists, and enforces read-only policies before dispatching the request.

---

## 6. Consequences and benefits

* **Clean separation of concerns:** Application business logic remains isolated from infrastructure network proxy configuration.
* **Low user latency:** Cloud Run provides <40ms cold starts for browser users, avoiding heavy proxy handshakes on initial load.
* **Robust enterprise governance:** Dual-layer protection ensures prompts are sanitized at the application layer, and tool execution is bounded at the network layer.
