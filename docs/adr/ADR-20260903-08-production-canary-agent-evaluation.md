# Architectural decision record: Production canary agent evaluation

> **ADR ID:** ADR-20260903-08  
> **Status:** Accepted  
> **Date:** 2026-09-03  
> **Deciders:** Engineering Lead & Cloud Architecture Team  
> **Scope:** Production Canary Agent Evaluation, Vertex AI Experiments, and Cloud Deploy Verify Automation  
> **Related:** [ADR-20260902-05](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-05-cloud-deploy-private-pools-and-single-artifact-promotion.md), [ADR-20260902-06](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-06-vertex-agent-engine-lifecycle-and-in-place-updates.md), [ADR-20260902-07](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/docs/adr/ADR-20260902-07-three-tier-environment-strategy-and-canary-evaluation.md)

---

## 1. Context and problem statement

Conductor v3 adopted a multi-tier delivery strategy in ADR-20260902-07. Dev and Staging tiers validate deterministic software contracts, container compilation, and Model Armor security policies. However, deterministic tests cannot verify non-deterministic Large Language Model (LLM) behaviors. 

Promoting release candidates into production without semantic validation risks regressions. Regressions include degraded response grounding, hallucinations of non-existent APIs, and corrupted tool invocation payloads. 

We require an automated evaluation gate embedded directly within Cloud Deploy canary rollout phases. The gate must evaluate the production Vertex AI Agent Engine against realistic enterprise scenarios. It must log evaluation metrics to Vertex AI Experiments. Finally, it must halt promotion and trigger automated rollback when quality gates fail.

---

## 2. Decision

We establish an automated production agent evaluation gate within Google Cloud Deploy:

1. **Embed evaluation in canary verify phases**:
   * Attach an automated verification job to every production canary rollout phase (`canary-25`, `canary-50`, and `stable`).
   * Execute verification workloads exclusively on the dedicated private worker pool (`cloudbuild-workerpool`) within VPC `cloudbuild-worker-vpc`.
   * Enforce a strict 600s execution timeout per verification phase.

2. **Standardize on a hybrid evaluation scoring strategy**:
   * Implement custom, deterministic metric scorers for fast in-pipeline gating during Cloud Deploy verify runs.
   * Provide built-in fallback and integration pathways to Vertex AI Gen AI Evaluation Service and Rapid Evaluation for asynchronous deep audits.
   * Query the canonical production reasoning engine (`projects/riccardo-blog-test-v1/locations/us-central1/reasoningEngines/1423301859237429248`) or mock fixtures during test runs.

3. **Track release quality in Vertex AI Experiments**:
   * Log every verification run to the Vertex AI Experiment `conductor-v3-prod-canary-eval`.
   * Tag each run with Cloud Deploy rollout identifiers, target phase, commit SHA, and container digest.
   * Compare canary quality against historical baselines before advancing traffic.

4. **Enforce automated rollback thresholds**:
   * Halt rollout and trigger immediate rollback when groundedness falls below 0.80, hallucination rate exceeds 0.05, or tool-call accuracy drops below 0.90.
   * Return non-zero exit codes from the verification runner to signal failure to Cloud Deploy.

---

## 3. Evaluation engine trade-offs

We evaluated three evaluation architectures for in-pipeline canary verification:

| Evaluation approach | Latency profile | Worker dependencies | Network egress requirement | Offline / Mock support | Cloud cost per run | Suitability for Cloud Deploy verify |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Vertex AI Gen AI Evaluation Service** | High (60s – 180s) | Heavy (`google-cloud-aiplatform[evaluation]`, pandas, pyarrow, tqdm) | External Google API endpoint | None (requires live project connection) | Medium ($0.05 – $0.20 per scenario batch) | Secondary (ideal for scheduled batch audits, too heavy for fast verify gates) |
| **Vertex AI Rapid Evaluation (evaluateInstances)** | Moderate (15s – 45s) | Medium (`google-genai` or direct REST API) | Direct API endpoint in `us-central1` | Limited | Low ($0.01 – $0.05 per batch) | Supported (viable when online credentials and endpoint connectivity exist) |
| **Custom deterministic metric scorers** | Near-instant (<2s) | Minimal (standard Python library + lightweight parsing) | Local compute only (zero egress) | Full (operates seamlessly offline and in tests) | Zero compute overhead | **Primary (mandatory for deterministic, fast in-pipeline gating)** |

### Architectural selection rationale
Heavy Python dependencies like `pandas` and `pyarrow` inflate worker container images by hundreds of megabytes. Image bloat causes worker cold starts and memory pressure in private build pools. 

Furthermore, managed evaluation services make external model calls that introduce non-deterministic scoring variances. Custom deterministic scorers provide sub-second evaluation, strict contract enforcement, and deterministic reproducibility. Rapid Evaluation and Gen AI Evaluation Service are retained as optional upstream audit plugins.

---

## 4. Canary verify phase execution architecture

Cloud Deploy canary verification executes sequentially across rollout phases:

1. **Phase 1: Canary 25% (`canary-25`)**:
   * Cloud Deploy shifts 25% of production traffic to the new revision.
   * The verify job initializes inside `cloudbuild-workerpool`.
   * The prober runs `scripts/evaluate_production_agent.py` against the golden dataset.
   * If all quality thresholds pass, Cloud Deploy automation `auto-advance-canary` triggers phase progression.

2. **Phase 2: Canary 50% (`canary-50`)**:
   * Cloud Deploy expands traffic allocation to 50%.
   * The verify runner executes a second evaluation pass with active latency monitoring.
   * If metrics remain above thresholds, automation promotes the release candidate to stable.

3. **Phase 3: 100% Stable (`stable`)**:
   * Cloud Deploy routes 100% of production traffic to the verified revision.
   * A final verification pass records baseline metrics to Vertex AI Experiments.

---

## 5. Experiment tracking with Vertex AI Experiments

Continuous tracking ensures model drift and prompt regressions are captured over time:

* **Experiment name**: `conductor-v3-prod-canary-eval`
* **Run ID convention**: `rollout-${CLOUD_DEPLOY_ROLLOUT_ID}-${CANARY_PHASE}`
* **Logged parameters**:
  * `phase`: Deployment phase (`canary-25`, `canary-50`, `stable`).
  * `agent_engine_id`: Vertex AI Reasoning Engine resource path.
  * `container_digest`: Immutable container image SHA256 digest.
  * `git_commit`: Source control commit hash.
  * `dataset_version`: Golden evaluation dataset semantic version.
* **Logged metrics**:
  * `average_groundedness`: Mean grounding score across all scenarios.
  * `average_hallucination_rate`: Percentage of ungrounded or contradictory assertions.
  * `average_tool_call_accuracy`: Ratio of correct tool invocations and parameter payloads.
  * `quality_gate_passed`: Binary status flag (`1` for pass, `0` for fail).

---

## 6. Metric selection and automated rollback thresholds

We define three core quantitative quality gates for production promotion:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Quality gate 1: Groundedness Score                                          │
│ Formula: (Supported Claims) / (Total Factual Claims in Agent Response)      │
│ Threshold: >= 0.80 (Warning < 0.85, Hard Failure < 0.80)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Quality gate 2: Hallucination Rate                                          │
│ Formula: (Unsupported or Fabricated Claims) / (Total Response Claims)       │
│ Threshold: <= 0.05 (Warning > 0.02, Hard Failure > 0.05)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Quality gate 3: Tool-Call Correctness                                       │
│ Formula: (Correct Tool Invocations + Parameter Matches) / (Expected Tools)  │
│ Threshold: >= 0.90 (Warning < 0.95, Hard Failure < 0.90)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Automated rollback mechanism
When any metric breaches its hard failure threshold:
1. The evaluation runner logs the violation details into `scorecard.json`.
2. The runner terminates with non-zero exit code `1`.
3. Cloud Deploy registers verify step failure on target `prod`.
4. The Cloud Deploy release enters a failed state, suppressing `advanceRolloutRule`.
5. Cloud Run routes 100% of user traffic back to the prior stable revision automatically.

---

## 7. Architectural topology

```mermaid
graph TD
    subgraph CD["Google Cloud Deploy: conductor-v3-pipeline"]
        P1["Phase 1: canary-25 (25% Traffic)"]
        P2["Phase 2: canary-50 (50% Traffic)"]
        P3["Phase 3: stable (100% Traffic)"]
        AUTO["Automation: auto-advance-canary"]
    end

    subgraph WP["Cloud Build Private Pool: cloudbuild-workerpool"]
        VERIFY["Cloud Deploy Verify Job<br/>(Timeout: 600s, VPC Peered)"]
        RUNNER["Evaluation Runner<br/>(evaluate_production_agent.py)"]
        DATASET["Golden Dataset<br/>(12 Enterprise Scenarios)"]
        SCORER["Scoring Engine<br/>(Groundedness, Hallucination, Tool Accuracy)"]
    end

    subgraph PROD["Production Runtime Environment"]
        GATEWAY["Conductor v3 Cloud Run Gateway<br/>(conductor-v3-prod)"]
        ENGINE["Vertex AI Agent Engine<br/>(1423301859237429248)"]
        SQL["Cloud SQL pgvector<br/>(genai-rag-db-859a1005)"]
    end

    subgraph EXP["Observability and Governance"]
        VERTEX_EXP["Vertex AI Experiments<br/>(conductor-v3-prod-canary-eval)"]
        SCORECARD["Evaluation Scorecard<br/>(scorecard.json)"]
        GATE["Rollback Gate Decision<br/>(Exit Code 0 vs 1)"]
    end

    P1 -->|Triggers Verify| VERIFY
    P2 -->|Triggers Verify| VERIFY
    P3 -->|Triggers Verify| VERIFY

    VERIFY --> RUNNER
    DATASET --> RUNNER
    RUNNER --> SCORER

    RUNNER -->|Query Agent| ENGINE
    ENGINE -->|Context Retrieval| SQL
    GATEWAY -.-> ENGINE

    SCORER --> SCORECARD
    SCORER --> VERTEX_EXP
    SCORER --> GATE

    GATE -->|Pass: Exit 0| AUTO
    AUTO -->|Advance| P2
    AUTO -->|Advance| P3
    GATE -->|Fail: Exit 1| ROLLBACK["Automated Rollback<br/>(Traffic 100% to Previous Stable)"]
```

---

## 8. Consequences

### Positive
* Protects production enterprise users from hallucinated facts and faulty tool executions.
* Preserves fast deployment cycles by executing deterministic verification within 15 seconds.
* Tracks longitudinal model quality trends in Vertex AI Experiments across every git commit.
* Eliminates manual approval toil for canary progression while retaining automated safety cutoffs.
* Functions reliably in isolated, private VPC worker pools without public internet dependencies.

### Negative
* Requires maintaining the golden evaluation dataset alongside backend API and schema evolution.
* Requires provisioning IAM permissions for `aiplatform.user` on the Cloud Deploy execution service account.
