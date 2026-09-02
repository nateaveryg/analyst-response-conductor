import datetime
import logging
from typing import Any

logger = logging.getLogger("conductor.demo_script_agent")


class DemoScriptAgentService:
    """
    Specialized AI Sub-Agent operating as a Senior OPM / Product Manager with comprehensive
    knowledge of the Google Cloud suite and deep insight into analyst psychology across
    Gartner, Forrester, IDC, and peer analyst firms.
    
    Synthesizes scripted demonstration workflows, visual UI actions, voiceover dialogues,
    analyst expectation evaluations ("on the page" vs. "not on the page"), and balanced
    current/future capability narratives.
    """

    @classmethod
    def generate_demo_playbook(cls, report_name: str | None = None, context_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Synthesizes a complete storyboard playbook dictionary with scripted actions, spoken dialogue,
        and executive narrative framing tailored to the target report scope.
        """
        if not report_name and context_data:
            from app.services.a2ui_generator import A2UIGenerator
            report_name = A2UIGenerator.resolve_analyst_report_name(context_data)

        is_cnap = report_name and any(key in report_name.lower() for key in ["cnap", "cloud-native", "application platforms"])
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        if is_cnap:
            report_scope = "Gartner Magic Quadrant & Critical Capabilities for Cloud-Native Application Platforms (CNAP), 2026"
            video_cap = "<= 45 Minutes Overall Cap (5 Core Demonstration Modules)"
            freeze_date = "May 7, 2026 (Demo & Narrative Freeze)"
            modules = [
                {
                    "module_number": 1,
                    "title": "Major Use Cases & Prescriptive Serverless Flows",
                    "sme_lead": "Serverless Domain Lead (`serverless-sme@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/run?project=riccardo-blog-test-v1",
                    "timecode": "[00:00 - 08:00] (08:00 allocation)",
                    "scripted_actions": [
                        "Navigate to Cloud Run serverless concurrency console surface.",
                        "Select active deployed service `conductor-v2` and inspect concurrency metrics showing 80 requests/container.",
                        "Execute CLI simulated load testing command to demonstrate automated horizontal scaling without warm-up latency."
                    ],
                    "spoken_dialogue": (
                        "Welcome to our live Cloud Run serverless concurrency demonstration. As you see on our active dashboard, "
                        "Google Cloud handles up to 80 concurrent enterprise requests per container instance without cold-start throttling. "
                        "Notice how our automated autoscaler smoothly provisions underlying capacity in sub-second intervals while maintaining "
                        "strict Zero Trust Workload Identity bindings."
                    )
                },
                {
                    "module_number": 2,
                    "title": "Critical Capabilities (Serverless GPUs & Concurrency)",
                    "sme_lead": "Serverless GPU Lead (`gpu-sme@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/run/gpu?project=riccardo-blog-test-v1",
                    "timecode": "[08:00 - 18:00] (10:00 allocation)",
                    "scripted_actions": [
                        "Open Cloud Run GPU runtime configuration pane under instance hardware allocation.",
                        "Attach NVIDIA L4 GPU accelerator profile with shared container memory provisioning.",
                        "Submit embedding inferencing prompt via API test harness and display sub-20ms P99 latency logs in Cloud Monitoring."
                    ],
                    "spoken_dialogue": (
                        "Turning to compute-intensive AI workloads, notice how effortlessly we attach high-performance GPU accelerators directly "
                        "to our containerized microservices. This integration bridges traditional cloud-native orchestration with next-generation "
                        "inferencing pipelines, ensuring enterprise engineering teams deploy generative models with zero infrastructure overhead."
                    )
                },
                {
                    "module_number": 3,
                    "title": "Differentiating Features (GKE Multi-Cluster Mesh & Cloud Run)",
                    "sme_lead": "GKE Enterprise Lead (`gke-sme@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/kubernetes?project=riccardo-blog-test-v1",
                    "timecode": "[18:00 - 30:00] (12:00 allocation)",
                    "scripted_actions": [
                        "Switch to GKE Enterprise autopilot multi-cluster mesh overview tab.",
                        "Highlight unified telemetry surface bridging stateful GKE workloads with stateless Cloud Run services.",
                        "Perform zero-downtime canary traffic split (90/10) across regional cluster boundaries."
                    ],
                    "spoken_dialogue": (
                        "Here we demonstrate our visionary differentiation: seamless interoperability between GKE Enterprise autopilot clusters "
                        "and Serverless Cloud Run services. Watch as we execute a live 90/10 canary traffic transition across multi-region "
                        "boundaries, fully protected by mutual TLS encryption and unified telemetry across our service mesh."
                    )
                },
                {
                    "module_number": 4,
                    "title": "Golden Paths & Application Design Center (ADC)",
                    "sme_lead": "Platform Engineering Lead (`idp-sme@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/architecture?project=riccardo-blog-test-v1",
                    "timecode": "[30:00 - 38:00] (08:00 allocation)",
                    "scripted_actions": [
                        "Access Application Design Center (ADC) service catalog and select verified 'Standard GA Enterprise Web App' template.",
                        "Inspect automated Terraform architecture layout and security guardrail compliance checks.",
                        "Click 'Deploy Golden Path' and show automated CI/CD pipeline instantiation in Cloud Build."
                    ],
                    "spoken_dialogue": (
                        "To maximize developer ergonomics and eliminate day-2 maintenance friction, our Application Design Center provides curated "
                        "Golden Paths. By selecting this verified enterprise template, engineering teams automatically spin up security-hardened, "
                        "compliant application architectures in under 90 seconds."
                    )
                },
                {
                    "module_number": 5,
                    "title": "12-Month Delivered Commitments & Strategic Roadmap",
                    "sme_lead": "Product Leadership (`pm-leadership@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/gemini/roadmap?project=riccardo-blog-test-v1",
                    "timecode": "[38:00 - 45:00] (07:00 allocation)",
                    "scripted_actions": [
                        "Display retrospective checklist of 2025 delivered commitments (Antigravity 2.0 GA, ADC GA, SCC Enterprise GA).",
                        "Open interactive preview sandbox for Gemini Code Assist Agent Mode (target GA April 15, 2026).",
                        "Execute multi-turn autonomous bug resolution workflow in live Cloudtop testing harness."
                    ],
                    "spoken_dialogue": (
                        "Finally, reviewing our 12-month delivered commitments, we have successfully achieved standard GA on 100% of our 2025 roadmap promises. "
                        "Looking ahead, we invite you into our preview testbed for Gemini Code Assist Agent Mode, demonstrating autonomous multi-turn "
                        "codebase resolution that solidifies our placement at the forefront of the Leaders Quadrant."
                    )
                }
            ]
        else:
            report_scope = "Universal Code & Agent Platforms / Forrester Wave & IDC MarketScape DevSecOps, 2026"
            video_cap = "<= 60 Minutes Overall Cap (High-Contrast 720p+ UI Mockups)"
            freeze_date = "T-14 Days (Storyboard & Narrative Freeze)"
            modules = [
                {
                    "module_number": 1,
                    "title": "CI/CD Declarative & Parallel Pipelines",
                    "sme_lead": "David Jacobs (`davidjacobs@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/cloud-build?project=riccardo-blog-test-v1",
                    "timecode": "[00:00 - 12:00] (12:00 allocation)",
                    "scripted_actions": [
                        "Open Cloud Build execution history showing parallel multi-architecture build workers.",
                        "Trigger live pull-request simulation and showcase automated dependency pre-caching.",
                        "Inspect zero-configuration secure worker pool networking within isolated VPC."
                    ],
                    "spoken_dialogue": (
                        "Our DevSecOps demonstration initiates with Cloud Build declarative parallel pipelines. Observe how our isolated build workers "
                        "instantly parallelize compilation tasks while maintaining secure private VPC peering, cutting developer build times by 65%."
                    )
                },
                {
                    "module_number": 2,
                    "title": "DORA Productivity & Agile Planning Insights",
                    "sme_lead": "Nathen Harvey (`nathenh@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/dora?project=riccardo-blog-test-v1",
                    "timecode": "[12:00 - 22:00] (10:00 allocation)",
                    "scripted_actions": [
                        "Navigate to DORA value stream productivity analytics portal.",
                        "Display real-time telemetry tracking deployment frequency, lead time for changes, and change fail rates.",
                        "Filter metrics by product domain team to demonstrate executive engineering governance."
                    ],
                    "spoken_dialogue": (
                        "Beyond infrastructure orchestration, our suite embeds natively integrated DORA analytics. Here, executive engineering leadership "
                        "monitors software delivery performance in real time, translating build activity into actionable organizational velocity insights."
                    )
                },
                {
                    "module_number": 3,
                    "title": "SLSA Level 3 Software Supply Chain Attestation",
                    "sme_lead": "Al Huizenga (`alhuizenga@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/artifacts?project=riccardo-blog-test-v1",
                    "timecode": "[22:00 - 34:00] (12:00 allocation)",
                    "scripted_actions": [
                        "Open Artifact Registry container image vulnerability inspection pane.",
                        "Verify SLSA Level 3 provenence build attestation signature generated during Cloud Build execution.",
                        "Attempt simulated unauthorized container deployment and show immediate interception by Binary Authorization."
                    ],
                    "spoken_dialogue": (
                        "Supply chain integrity is non-negotiable. As demonstrated here, every artifact compiled by Cloud Build is stamped with an immutable "
                        "SLSA Level 3 attestation. When an unverified container attempts to launch, our Binary Authorization admission controller instantly "
                        "blocks deployment, guaranteeing zero runtime exposure."
                    )
                },
                {
                    "module_number": 4,
                    "title": "Observability & Runtime Threat Detection (SCC Enterprise)",
                    "sme_lead": "Rami Shalom & Knox Anderson (`monitoring-smes@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/monitoring?project=riccardo-blog-test-v1",
                    "timecode": "[34:00 - 48:00] (14:00 allocation)",
                    "scripted_actions": [
                        "Transition to Security Command Center (SCC) Enterprise dashboard.",
                        "Review active runtime threat detection findings correlated with Cloud Monitoring trace telemetry.",
                        "Execute automated remediation playbook neutralizing simulated privilege escalation attempt."
                    ],
                    "spoken_dialogue": (
                        "Unifying developer operations with advanced security operations, Security Command Center Enterprise merges runtime threat detection "
                        "with deep observability telemetry. Notice how a simulated anomaly is instantly identified, mapped to its exact source line of code, "
                        "and remediated automatically via our integrated operations workflows."
                    )
                },
                {
                    "module_number": 5,
                    "title": "Enterprise IAM, Sovereign Data Residency & Strategic Roadmap",
                    "sme_lead": "Nate Avery & Ashley Castillo (`iam-smes@google.com`)",
                    "sandbox_url": "https://console.cloud.google.com/iam-admin?project=riccardo-blog-test-v1",
                    "timecode": "[48:00 - 60:00] (12:00 allocation)",
                    "scripted_actions": [
                        "Inspect Workload Identity Federation OIDC token trust boundary bindings.",
                        "Demonstrate explicit data sovereignty geography restriction policies.",
                        "Present 18-month AI autonomous security scanning roadmap module and concluding slides."
                    ],
                    "spoken_dialogue": (
                        "We conclude our evaluation walkthrough with enterprise governance and data sovereignty. Using Workload Identity Federation, "
                        "external CI/CD pipelines authenticate seamlessly without long-lived service account keys. Combined with our strict sovereign residency "
                        "guardrails and upcoming autonomous AI remediation engine, Google Cloud provides the definitive platform for secure enterprise software delivery."
                    )
                }
            ]

        playbook_dict = {
            "report_scope": report_scope,
            "timestamp": now_str,
            "video_duration_cap": video_cap,
            "target_freeze_date": freeze_date,
            "executive_summary": {
                "current_ga_capabilities": (
                    "To guarantee zero evaluation deficit violations and full compliance with formal analyst GA cutoff dates, our primary "
                    "demonstration sequence is anchored exclusively in bedrock Standard GA offerings: Gemini Code Assist Enterprise ($35M Revenue, 65% CAGR), "
                    "Cloud Run Serverless Concurrency, GKE Autopilot, Cloud Build SLSA Level 3 Pipelines, and Security Command Center (SCC) Enterprise. "
                    "This establishes immediate, indisputable qualification against all core functional scoring floors."
                ),
                "future_capabilities_plan": (
                    "To prove unmatched 12-to-18-month innovation velocity and secure visionary placement in the Leaders Quadrant, the concluding "
                    "demonstration module features dedicated roadmap previews and attestation waiver modules. Specifically, we unveil Gemini Code Assist "
                    "Agent Mode (Preview until April 15, 2026), showcasing multi-turn autonomous bug resolution and self-healing cloud architectures."
                ),
                "terraform_infrastructure_instructions": (
                    "Before initializing screencast video capture, domain SME leads must provision their isolated demonstration testbeds using our "
                    "standardized Terraform configuration suite located in `infra/terraform/demo_sandboxes/`. Running `bash test_and_deploy_sandboxes.sh` "
                    "(or `terraform init && terraform apply`) automatically creates the identical Cloud Run services, GKE clusters, Artifact Registry repositories, "
                    "and IAM bindings referenced in this script."
                )
            },
            "analyst_expectations": {
                "on_the_page": (
                    "Strict adherence to published questionnaire items: explicit demonstration of horizontal scaling, zero-trust container signing, "
                    "SLSA Level 3 provenence attestation, developer golden paths, and absolute respect for formal duration ceilings (<= 45m CNAP, <= 60m DevSecOps)."
                ),
                "not_on_the_page": (
                    "Implicit analyst evaluation psychology: demonstrating architectural cohesion (zero fragmentation across compute, security, and CI/CD), "
                    "day-2 operational elegance, executive engineering visibility (DORA), predictable Total Cost of Ownership (TCO), and AI integration that "
                    "acts as a native multiplier rather than a bolted-on afterthought."
                )
            },
            "narrative_overview": (
                "Our overarching storyboard narrative unites enterprise software delivery under a single cohesive theme: 'From Prompt to Production with Zero Security Friction.' "
                "Each domain module smoothly builds upon the previous chapter, showing an enterprise application progressing from developer ideation through "
                "automated secure CI/CD pipelines, multi-cluster service mesh deployment, runtime threat detection, and autonomous AI remediation."
            ),
            "scripted_modules": modules,
            "narrative_closeout": (
                "In closing, this demonstration validates that Google Cloud delivers the industry's only unified, security-first application platform "
                "where artificial intelligence natively illuminates every stage of the software developer lifecycle. By combining bedrock GA enterprise "
                "stability with visionary autonomous AI capabilities, we provide engineering organizations with unmatched deployment velocity and security resilience."
            )
        }
        return playbook_dict

    @classmethod
    def format_playbook_markdown(cls, script_data: dict[str, Any]) -> str:
        """
        Converts synthesized demo playbook dictionary into a highly structured, professional Markdown document
        suitable for executive evaluation reviews and standalone REST downloads.
        """
        lines = [
            "# 🎬 Phase 5: On-Demand Demo Environments & Storyboard Playbook",
            f"**Target Evaluation Scope:** {script_data['report_scope']}  ",
            "**Generated By:** Analyst Response Agent (ARA) — Sr. OPM / PM Demo Architect  ",
            f"**Timestamp:** {script_data['timestamp']}  ",
            f"**Video Recording Budget:** {script_data['video_duration_cap']}  ",
            f"**Target Freeze Milestone:** {script_data['target_freeze_date']}  ",
            "",
            "---",
            "",
            "## 🏆 Executive Summary: Current GA vs. Future Roadmap Strategy",
            "",
            "### 1. Current GA Bedrock Capabilities (Immediate Floor Compliance)",
            script_data["executive_summary"]["current_ga_capabilities"],
            "",
            "### 2. Future Visionary Capabilities & Roadmap (Visionary Differentiation)",
            script_data["executive_summary"]["future_capabilities_plan"],
            "",
            "### 3. Terraform Sandbox Infrastructure Provisioning",
            script_data["executive_summary"]["terraform_infrastructure_instructions"],
            "",
            "---",
            "",
            "## 🧠 Analyst Expectation Intelligence",
            "",
            "### What's Written on the Page (Explicit Scoring Criteria)",
            f"> [!IMPORTANT]\n> **Written Requirements:** {script_data['analyst_expectations']['on_the_page']}",
            "",
            "### What's Not on the Page (Implicit Analyst Psychology & Vision)",
            f"> [!TIP]\n> **Implicit Expectations:** {script_data['analyst_expectations']['not_on_the_page']}",
            "",
            "---",
            "",
            "## 📖 Overarching Narrative Overview",
            script_data["narrative_overview"],
            "",
            "---",
            "",
            "## 🎭 Scripted Demonstration Modules & Voiceover Dialogues",
            ""
        ]

        for mod in script_data.get("scripted_modules", []):
            lines.extend([
                f"### Module {mod['module_number']}: {mod['title']}",
                f"* **Assigned Domain Lead:** `{mod['sme_lead']}`",
                f"* **Target Cloud Sandbox URL:** `{mod['sandbox_url']}`",
                f"* **Timecode Budget:** `{mod['timecode']}`",
                "",
                "#### 🛠️ Scripted Visual UI Actions & Console Flow",
            ])
            for act in mod.get("scripted_actions", []):
                lines.append(f"1. {act}")
            lines.extend([
                "",
                "#### 🎙️ Spoken Voice-Over Narration Dialogue",
                f"> **SME Script:** *\"{mod['spoken_dialogue']}\"*",
                "",
                "---",
                ""
            ])

        lines.extend([
            "## 🎯 Narrative Closeout & Strategic Wrap-Up",
            script_data["narrative_closeout"],
            "",
            "---",
            "*Confidential & Proprietary — Prepared for Industry Analyst Evaluation Sessions by Google Cloud.*",
            ""
        ])

        return "\n".join(lines) + "\n"
