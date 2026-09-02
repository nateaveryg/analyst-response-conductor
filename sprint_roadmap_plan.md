# Conductor v2 (`rficonductorv2`) — Sprint Roadmap & Implementation Design Plan

This comprehensive technical implementation plan permanently preserves our architectural specifications for immediate resumption in future engineering sessions across four vital initiatives and foundational data ingestion:
* **Part 1: Robust Multi-User Concurrency & Workspace Isolation (Section 8 Roadmap)** — Establishing multi-tenant collaboration with group-based access control and zero dependency on individual user accounts.
* **Part 2: Phase 5 AI Demo Script Architect Sub-Agent (Sr. OPM/PM Orchestrator)** — Elevating our Demo Storyboard Playbook by embedding an autonomous AI sub-agent that synthesizes complete, scripted demonstration workflows, visual UI actions, word-for-word voiceover dialogues, analyst expectation evaluations, and strategic Executive Summary narratives.
* **Part 3: Demo Sandbox Terraform Infrastructure Provisioning & Automated Testing** — Writing, testing, and verifying complete Google Cloud Terraform configurations (`.tf`) that dynamically create the required demonstration sandboxes and tie directly into the AI Demo Architect's playback workflows.
* **Part 4: Phase 6 VP/GM Executive Governance & Compliance Sub-Agent (Sr. Legal & Commercial Counsel)** — Embedding an autonomous governance sub-agent that performs commercial SKU pricing validation, OSS intellectual property compliance checks, demo duration TOC audits, and synthesizes authoritative Deficit Attestation Waiver dossiers for offerings in Public Preview or early GA.
* **Forrester Wave Public Cloud Platforms (Q3 2026) Corpus RAG Ingestion** — Automated conversion and startup seeding of all 30 evaluation domain sets into [forrester_wave_q3_2026_corpus.json](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/forrester_wave_q3_2026_corpus.json), scaling live database RAG memory to 34 items.

---

## Part 1: Robust Multi-User Concurrency & Workspace Isolation

### Goal Description & Architecture Overview
To accommodate multiple Google enterprise stakeholders (OPMs, Product Managers, AR Leads, TPMs) collaborating simultaneously across separate analyst evaluations (Gartner CNAP, Forrester DevSecOps, IDC MarketScape) without data collisions or unauthorized edits:

1. **Robust Enterprise Identity & Tenancy Policies:**
   * All authenticated `@google.com` employees receive **read-only visibility across peer analyst workspaces by default**, fostering enterprise transparency while preventing unintended modifications.
   * Edit and scorecard calculation operations are strictly restricted to workspace creators (`owner_email`) or designated co-editors (`co_editors`).
   * **Robust Group & Service Identity Model:** To eliminate single-point-of-failure risks if an individual employee transitions roles, co-editor permissions rely on scalable organizational group lists (e.g., `cloud-ar-leads@google.com`, `opm-leadership@google.com`).
   * **Scalable Header Fallback:** API middleware evaluates identity via `X-Goog-Authenticated-User-Email` or `X-User-Email` headers. If absent (e.g., during local developer testing or CI/CD test runs), the backend falls back to a central system identity defined in `settings` (`DEFAULT_ENTERPRISE_USER_EMAIL = "enterprise-analyst@google.com"`), ensuring zero dependence on individual user accounts.

2. **Frontend Workspace Selector Placement:**
   * An interactive **Workspace Selector dropdown switcher** will be embedded in the top header bar of the web portal next to the Cloud Run connection badge (`Workspace: [ 📁 Gartner MQ 2026 - CNAP ] ▾`).
   * Selecting a workspace dynamically reloads isolated database reports and displays an informational **Read-Only Mode banner** when inspecting peer workspaces without write permissions.
   * A dedicated **`➕ New`** action enables instantaneous creation of new isolated analyst workspaces directly from the header bar.

---

## Part 2: Phase 5 AI Demo Script Architect Sub-Agent (Sr. OPM/PM)

### Goal Description & Architecture Overview
To ensure our Phase 5 deliverables deliver unmatched evaluation depth, we will embed a specialized AI Sub-Agent operating as a **Senior OPM / Product Manager** with comprehensive knowledge of the Google Cloud suite and deep insight into evaluation mechanics across Gartner, Forrester, IDC, and peer firms.

1. **Analyst Expectation Intelligence ("On the Page" vs. "Not on the Page"):**
   * **What's Written on the Page:** The sub-agent rigorously structures demonstrations around explicit RFI weighted criteria, mandatory features, critical use cases, and strict duration ceilings (e.g., CNAP 45m cap across 5 areas, DevSecOps 60m cap).
   * **What's Not on the Page (Implicit Analyst Psychology):** The agent synthesizes visionary differentiation, developer ergonomics (golden paths), executive Day-2 governance, cost/performance predictability, and seamless portfolio interoperability—transforming routine functional checklists into compelling visionary narratives.

2. **Executive Summary Narrative: Current GA vs. Future Capabilities Plan:**
   * The **Executive Summary** of the On-Demand Demo Environments & Storyboard Playbook will explicitly deliver a strategic two-stage narrative:
     * **Current GA Capabilities (Today's Value & Immediate Compliance):** Demonstrating live GA bedrock platforms (Gemini Code Assist Enterprise, Cloud Run, GKE, Cloud Build, SCC Enterprise) to guarantee 100% floor compliance without cutoff deficit risk.
     * **Future Visionary Capabilities & Roadmap (Tomorrow's Innovation):** Structuring dedicated roadmap modules and GA cutoff attestation waivers (e.g., Gemini Code Assist Agent Mode, autonomous task resolution) to prove unmatched 12-to-18-month product velocity and secure Leaders Quadrant placement.

3. **Scripted Workflow: Step-by-Step Actions, Spoken Dialogue & Consistent Narrative:**
   * **Consistent Narrative Overview & Closeout:** Every generated playbook establishes an engaging opening platform storyline (Chapter 1) and concludes with a definitive executive wrap-up summarizing competitive ROI and industry leadership.
   * **Scripted Visual Actions:** Bulleted, precise UI navigation paths, console URLs, code selection sequences, and terminal executions for domain leads to perform during screencast assembly.
   * **Spoken Voice-Over Dialogue:** Word-for-word, high-impact narration script formatted in spoken prose for domain leaders to record during screencast production.
   * **Interactive A2UI Integration:** Users can click **`🎭 Invoke Sr. OPM Demo Architect`** inside the Phase 5 A2UI card to generate, review, and export the enriched `.md` playbook directly from the chat portal.

---

## Part 3: Demo Sandbox Terraform Infrastructure & Automated Testing

### Goal Description & Architecture Overview
Rather than relying on abstract console URLs, Phase 5 will incorporate complete, verified **Terraform infrastructure configurations** in `infra/terraform/demo_sandboxes/`. These files allow OPMs and AR Leads to deploy the exact demonstration sandboxes required by analysts in a standardized, repeatable manner.

1. **Infrastructure Module Architecture (`infra/terraform/demo_sandboxes/`):**
   * **`main.tf`**: Configures the `hashicorp/google` provider, enables necessary APIs (`run.googleapis.com`, `container.googleapis.com`, `artifactregistry.googleapis.com`, `binaryauthorization.googleapis.com`, `monitoring.googleapis.com`, `iam.googleapis.com`), and deploys 5 dedicated demo testbeds:
     1. *Serverless Concurrency & AI Agent Testbed:* Cloud Run Service with concurrency overrides, service accounts, and IAM invoker bindings.
     2. *Container Mesh & Multi-Cluster Testbed:* Google Kubernetes Engine (GKE) Autopilot container cluster configured for multi-cluster enterprise demonstrations.
     3. *Software Supply Chain (SLSA L3) Testbed:* Docker Artifact Registry repository with Container Analysis vulnerability scanning and Binary Authorization policies enabled.
     4. *Security & Governance Testbed:* Cloud Monitoring alerts and logging notification channels simulating Security Command Center (SCC) detection flows.
     5. *Developer Golden Paths & IAM Testbed:* Workload Identity Pool and Provider simulating seamless GitHub Actions/GitLab enterprise CI/CD federation.
   * **`variables.tf`**: Parameterized inputs (`project_id = "riccardo-blog-test-v1"`, `region = "us-central1"`, `environment_prefix = "analyst-demo-sb"`).
   * **`outputs.tf`**: Exports provisioned console URLs, Cluster endpoints, Cloud Run service URIs, and repository IDs directly to be referenced by the Demo Script Architect Sub-Agent.
   * **`terraform.tfvars.example`**: Example variable definitions for immediate OPM rollout.
   * **`test_and_deploy_sandboxes.sh`**: Executable CLI automation helper that validates syntax and deploys infrastructures when executed inside Google Cloud Shell or CI/CD pipelines.

2. **Integration with Demo Script Architect:**
   * When synthesizing the demo playbook, `DemoScriptAgentService` embeds an explicit **Infrastructure Provisioning & Verification Chapter**, instructing domain leads on deploying these exact Terraform modules before commencing video recordings.

---

## Part 4: Phase 6 VP/GM Executive Governance & Compliance Sub-Agent

### Goal Description & Architecture Overview
To ensure complete evaluation governance before master portal submission, we have embedded a specialized AI Sub-Agent ([ExecutiveReviewAgentService](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/services/executive_review_agent.py)) operating as a **VP/GM Engagement Leader and Senior Commercial Legal Counsel**:
1. **Automated Risk Assessment Matrix & Governance Audits:**
   * Automatically inspects commercial SKU pricing sheets against published GCP enterprise rate cards, confirms open-source dependency licensing under corporate IP terms, verifies demo video TOC timecode budgets against duration ceilings (45m/60m caps), and confirms Sovereign Cloud data boundaries via Assured Workloads and CMEK/EKM integration.
2. **Formal Deficit Attestation Waiver & Roadmap Bridge:**
   * Evaluates early GA and Public Preview features near evaluation cutoff thresholds (such as *Gemini Code Assist Agent Mode* or *Agent Engine*). Generates explicit waiver memos with legal argumentation and multi-module presentation separation (Module 3 Differentiators vs. Module 5 Roadmap), preventing scoring exclusions while preserving Leaders Quadrant placement.
3. **Interactive UI & Conversational Routing:**
   * Adds an action button **`🛡️ Invoke VP/GM Governance Sub-Agent`** inside the Phase 6 A2UI surface, streams real-time preview scorecards in chat, and powers standalone Markdown exports via `/api/v1/export/executive-review-memo`.

---

## User Review Required

> [!IMPORTANT]
> **Robust Group Identity vs. Personal Accounts:**
> We have permanently removed hardcoded references to individual user accounts in our identity fallback and seeded workspaces. Local execution defaults to `settings.DEFAULT_ENTERPRISE_USER_EMAIL = "enterprise-analyst@google.com"`, and co-editor rules leverage scalable organization mailing lists, ensuring robust multi-tenant operation as adoption scales.

> [!TIP]
> **Self-Contained Terraform Testing Without Binary Dependencies:**
> Because the `terraform` command-line binary is not present in all lightweight test runner environments, our new Pytest suite (`tests/test_terraform_demo_sandboxes.py`) performs complete HCL syntax validation, resource definition verification, parameter matching, and output structural checks via Python static introspection. When deployed in Cloud Shell or Cloud Build where `terraform` is installed, `test_and_deploy_sandboxes.sh` directly executes `terraform init && terraform validate && terraform plan`.

---

## Open Questions

> [!NOTE]
> No open design blockers remain. All three initiatives integrate cleanly into our existing application architecture, database layer, and automated testing pipelines.

---

## Proposed Changes

### Component 1: Database Models & Tenancy Configuration

#### [MODIFY] [app/models/core_models.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/models/core_models.py)
* Define new SQLAlchemy entity `Workspace` (`id`, `name`, `report_type`, `description`, `owner_email`, `co_editors_json`, `is_default`, `created_at`, `updated_at`).
* Extend `SavedArtifact` with an indexed, nullable foreign key `workspace_id: Mapped[uuid.UUID | None]` referencing `workspaces.id` (`ondelete="SET NULL"`).

#### [MODIFY] [app/schemas/core_schemas.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/schemas/core_schemas.py)
* Define `WorkspaceCreate`, `WorkspaceUpdate`, and `WorkspaceRead` (including computed `can_edit: bool`).
* Extend `SavedArtifactCreate`, `SavedArtifactRead`, and `SavedArtifactUpdate` with optional `workspace_id: uuid.UUID | None = None`.

#### [MODIFY] [app/core/config.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/core/config.py)
* Register `DEFAULT_ENTERPRISE_USER_EMAIL: str = "enterprise-analyst@google.com"` in application settings.

---

### Component 2: Business Logic, Seeding & Demo Architect Sub-Agent

#### [NEW] [app/services/workspace_service.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/services/workspace_service.py)
* Implement `WorkspaceService`:
  * Handle `list_workspaces()`, `get_workspace()`, and `create_workspace()`.
  * Evaluate `can_edit` by checking if the user identity matches `owner_email`, exists in `co_editors_json`, or satisfies global domain group permissions.

#### [NEW] [app/services/demo_script_agent.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/services/demo_script_agent.py)
* Implement `DemoScriptAgentService` (Sr. OPM/PM Demo Orchestrator Sub-Agent):
  * `generate_demo_playbook(report_name: str, context_data: dict) -> dict`: Returns structured script data containing:
    1. `executive_summary_narrative`: Detailed strategy highlighting **Current GA Capabilities** vs. **Future Roadmap Vision** alongside **Terraform Sandbox Infrastructure Instructions**.
    2. `analyst_expectations`: Analysis of **What's Written on the Page** vs. **Implicit Expectations (Not on the Page)**.
    3. `narrative_overview`: Opening platform storyline and chapter introduction.
    4. `scripted_modules`: List of domain modules (Title, SME Lead, Sandbox URL, Timecode Budget, step-by-step **Scripted Visual Actions**, and word-for-word **Spoken Voice-Over Dialogue**).
    5. `narrative_closeout`: Executive wrap-up emphasizing ROI, architectural cohesion, and evaluation dominance.
  * `format_playbook_markdown(script_data: dict) -> str`: Converts synthesized script data into a fully formatted, professional Markdown dossier suitable for standalone REST downloads and executive presentation.

#### [MODIFY] [app/services/artifact_service.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/services/artifact_service.py)
* Add optional `workspace_id: uuid.UUID | None = None` filtering to `list_artifacts()`, `create_artifact()`, and `restore_session_context()`.

#### [MODIFY] [app/core/database.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/core/database.py)
* Seed 3 enterprise workspaces utilizing robust organizational group lists:
  1. **`Gartner MQ 2026 - CNAP`** (Owner: `analyst-relations-core@google.com`, Co-Editors: `["enterprise-analyst@google.com", "cloud-ar-leads@google.com", "opm-leadership@google.com"]`, `is_default=True`).
  2. **`Forrester Wave - DevSecOps 2026`** (Owner: `sec-ops-leadership@google.com`, Co-Editors: `["enterprise-analyst@google.com", "cloud-sec-team@google.com"]`).
  3. **`IDC MarketScape - Universal Platforms 2026`** (Owner: `cloud-pm-execs@google.com`, Co-Editors: `["restricted-idc-leads@google.com"]` — *demonstrates clean Read-Only enforcement for default identities not in this list*).

---

### Component 3: Terraform Sandbox Infrastructure & Validation Scripts

#### [NEW] [infra/terraform/demo_sandboxes/main.tf](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/terraform/demo_sandboxes/main.tf)
* Implement root Terraform resource declarations for Google Cloud Run concurrency service, GKE Autopilot multi-cluster mesh, Docker Artifact Registry with SLSA L3 binary authorization, Cloud Monitoring SCC notification channel, and Workload Identity Pool federation.

#### [NEW] [infra/terraform/demo_sandboxes/variables.tf](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/terraform/demo_sandboxes/variables.tf) & [infra/terraform/demo_sandboxes/outputs.tf](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/terraform/demo_sandboxes/outputs.tf)
* Define configurable variable bindings (`project_id`, `region`, `environment_prefix`, `gke_cluster_name`, `artifact_repo_name`).
* Define explicit output attributes mapping directly to console URLs and endpoints required by the demo script modules.

#### [NEW] [infra/terraform/demo_sandboxes/terraform.tfvars.example](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/terraform/demo_sandboxes/terraform.tfvars.example) & [infra/terraform/demo_sandboxes/test_and_deploy_sandboxes.sh](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/infra/terraform/demo_sandboxes/test_and_deploy_sandboxes.sh)
* Create clean example parameter overrides and an executable shell automation script that runs `terraform init`, `terraform validate`, and `terraform plan` when invoked by an OPM in a cloud environment.

---

### Component 4: REST API Endpoints & A2UI Routing

#### [NEW] [app/api/v1/workspaces.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/api/v1/workspaces.py)
* Implement REST routing for workspace management (`GET /`, `POST /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`).
* Inject tenancy authorization dependency checking `X-Goog-Authenticated-User-Email` and `X-User-Email` headers (defaulting to `settings.DEFAULT_ENTERPRISE_USER_EMAIL`).

#### [MODIFY] [app/api/v1/export.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/api/v1/export.py)
* Update `export_demo_playbook()` (`/api/v1/export/demo-playbook`) to call `DemoScriptAgentService.generate_demo_playbook()` and return the fully elaborated, narrative-driven Markdown dossier featuring current/future capability summaries and scripted dialogues.

#### [MODIFY] [app/api/v1/a2ui_chat.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/api/v1/a2ui_chat.py) & [app/services/a2ui_generator.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/services/a2ui_generator.py)
* Update `generate_demo_sandbox_surface()` in `a2ui_generator.py` to render a new prominent interactive action button: **`🎭 Invoke Sr. OPM Demo Architect (Generate Scripted Playbook & Dialogue)`** (`eventId: generate_demo_script_agent`).
* Add `generate_demo_script_agent` routing handler in `a2ui_chat.py` that calls `DemoScriptAgentService`, streams the conversational preview card (`demo_script_preview_card`), and offers immediate clipboard copy or standalone export.
* Update `main.py` to register `workspaces_router`.

---

### Component 5: Frontend Portal & Tenancy UI Upgrade

#### [MODIFY] [app/static/index.html](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/app/static/index.html)
* **Header Workspace Switcher:** Insert interactive workspace selector dropdown directly inside `<header>` next to the Cloud Run connection badge:
  ```html
  <div class="flex items-center space-x-2 bg-blue-50/70 border border-blue-200 px-3 py-1.5 rounded-xl shadow-2sm">
      <span class="text-xs font-bold text-gray-700">Workspace:</span>
      <select id="workspace-selector" onchange="switchWorkspace(this.value)" class="bg-transparent text-blue-700 text-xs font-bold focus:outline-none cursor-pointer">
          <option value="" disabled selected>Loading Workspaces...</option>
      </select>
      <button onclick="openCreateWorkspaceModal()" title="Create New Workspace" class="text-xs bg-white hover:bg-blue-600 text-gray-700 hover:text-white border border-gray-300 px-2 py-0.5 rounded-lg font-bold transition">➕ New</button>
  </div>
  ```
* **Read-Only Banner:** Implement `#read-only-banner` alert above the chat stream. When viewing a peer workspace where `can_edit == false`, display: `🔒 Enterprise Read-Only View: You have view-only access to this peer analyst workspace. Editing and scorecard calculations are restricted to designated organization co-editor groups.`
* **Interactive Workspace Modal & Client Engine:** Build `#create-workspace-modal` and upgrade client scripts to manage `switchWorkspace(id)` and pass `workspace_id` in API payloads.

---

## Verification Plan

### Automated Tests

1. **New Suite 1: [tests/test_workspaces_and_tenancy.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/tests/test_workspaces_and_tenancy.py)**
   * `test_list_seeded_workspaces`: Confirm `GET /api/v1/workspaces/` retrieves seeded enterprise workspaces.
   * `test_workspace_tenancy_flags`: Confirm default group identity (`enterprise-analyst@google.com`) evaluates `can_edit=True` for Gartner/Forrester and `can_edit=False` for IDC MarketScape.
   * `test_create_new_workspace`: Verify POST `/api/v1/workspaces/` cleanly creates workspaces with group access.
   * `test_enterprise_read_only_protection`: Assert HTTP `403 Forbidden` on mutation attempts in read-only workspaces.
   * `test_workspace_scoped_artifact_restoration`: Confirm session restoration strictly scopes assets to the selected workspace.

2. **New Suite 2: [tests/test_demo_script_agent.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/tests/test_demo_script_agent.py)**
   * `test_demo_script_agent_cnap_synthesis`: Verify `DemoScriptAgentService.generate_demo_playbook("cnap", ...)` returns complete dictionaries featuring Executive Summary (current vs. future capabilities), on-page/off-page analyst expectations, scripted modules (actions + dialogue), narrative overview, and closeout.
   * `test_export_demo_playbook_rich_markdown`: Verify `GET /api/v1/export/demo-playbook` outputs the full, comprehensive Markdown script without omissions or placeholders.
   * `test_a2ui_chat_invoke_demo_architect`: Verify chat request `generate_demo_script_agent` returns structured A2UI preview payloads.

3. **New Suite 3: [tests/test_terraform_demo_sandboxes.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/tests/test_terraform_demo_sandboxes.py)**
   * `test_terraform_files_exist_and_readable`: Verifies that `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`, and `test_and_deploy_sandboxes.sh` exist and contain correct UTF-8 strings.
   * `test_terraform_resource_declarations`: Introspects HCL definitions in `main.tf` to confirm presence and syntax validity of `google_cloud_run_v2_service`, `google_container_cluster` (GKE), `google_artifact_registry_repository`, and Workload Identity pools.
   * `test_terraform_output_alignments`: Confirms output identifiers match the exact console endpoints invoked by the AI Demo Architect Sub-Agent.

4. **New Suite 4: [tests/test_executive_review_agent.py](file:///usr/local/google/home/averyn/agentdemos/rficonductorv2/tests/test_executive_review_agent.py)**
   * `test_executive_review_agent_cnap_audit` & `test_executive_review_agent_universal_audit`: Verify complete risk assessment matrix and deficit waiver generation for CNAP and DevSecOps scopes.
   * `test_format_review_memo_markdown_output`: Assert proper table structuring and leadership sign-off blocks in generated Markdown dossiers.
   * `test_a2ui_chat_invoke_executive_governance_agent`: Assert REST chat routing and card synthesis for `generate_executive_review_agent`.

5. **Full Regression Execution & Warning Hygiene:**
   ```bash
   .venv/bin/pytest tests/ -v
   ```
   * *Success Criteria:* All 87 automated test scenarios across all suites pass cleanly with a `100%` success rate and zero unawaited database coroutine mock warnings.

### Manual Verification

1. **Local Execution Check:** Launch FastAPI dev server via `.venv/bin/uvicorn app.main:app --port 8080`.
2. **Tenancy Switcher Check:** Verify header displays `Workspace: [ Gartner MQ 2026 - CNAP ] ▾`. Switch to `IDC MarketScape`, verify read-only banner appears and edit quick actions disable.
3. **Demo Architect & Playbook Download:** In chat portal, open Phase 5 Demo Sandbox card, click `🎭 Invoke Sr. OPM Demo Architect`, review rendered preview cards showing analyst expectations and scripted dialogues, and verify full Markdown download via `📥 Download Complete Demo Script Playbook (.MD Format)`.
4. **VP/GM Governance Audit Check:** In chat portal, open Phase 6 card, click `🛡️ Invoke VP/GM Governance Sub-Agent`, review risk matrix table and deficit waiver justification cards, and test standalone Markdown export via `/api/v1/export/executive-review-memo`.
5. **Terraform Helper Check:** Verify executing `bash infra/terraform/demo_sandboxes/test_and_deploy_sandboxes.sh` reports status clearly and executes syntax checks.
