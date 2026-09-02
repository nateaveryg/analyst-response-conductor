import json
from typing import Any
from app.schemas.inclusion_schemas import InclusionEvaluationMatrix, ParsedRfiCriteria
from app.schemas.orchestration_schemas import WorkbackTimeline


class A2UIGenerator:
    """
    Generator service that converts internal domain models (criteria evaluations, workback timelines,
    and intake forms) into standard A2UI (Agent-to-User Interface) declarative JSON payloads
    enclosed within `<a2ui-json> ... </a2ui-json>` protocol tags.
    """

    @staticmethod
    def wrap_in_a2ui_tags(payload: dict[str, Any] | list[dict[str, Any]]) -> str:
        """
        Serializes a dictionary or list of A2UI surface message definitions into formatted JSON
        and wraps it in standard `<a2ui-json>` delimiters for client stream ingestion.
        """
        json_str = json.dumps(payload, indent=2, ensure_ascii=False)
        return f"<a2ui-json>\n{json_str}\n</a2ui-json>"

    @staticmethod
    def resolve_analyst_report_name(context_data: dict[str, Any] | None = None) -> str | None:
        """
        Resolves the specific name of the analyst report from context data, ingested links,
        or uploaded documents so that all subsequent communication and artifacts refer to it consistently.
        Returns None if no report context has been provided yet.
        """
        if not context_data or not isinstance(context_data, dict) or len(context_data) == 0:
            return None

        for key in ["report_name", "analyst_report_name", "specific_report_name"]:
            val = context_data.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()

        text_pool = " ".join([
            str(context_data.get("welcome_packet_url", "")),
            str(context_data.get("demo_guidelines_url", "")),
            str(context_data.get("analyst_notes", "")),
        ]).lower().strip()

        if not text_pool or text_pool == "not specified" or text_pool == "no explicit notes provided":
            return None

        if any(k in text_pool for k in ["cloud-native", "cnap", "application platforms", "1ir1letci5mlv", "1vgz_0h8e", "1lmluwes0a", "1-8hqmu"]):
            return "Magic Quadrant and Critical Capabilities for Cloud-Native Application Platforms, 2026"
        if "devsecops" in text_pool:
            return "Magic Quadrant and Critical Capabilities for DevSecOps Platforms, 2026"
        if "gartner" in text_pool or "mq" in text_pool or "magic quadrant" in text_pool:
            if "ai code" in text_pool or "assistant" in text_pool:
                return "2026 Gartner Magic Quadrant for Cloud AI Code Assistants"
            return "2026 Gartner Magic Quadrant for Universal Code & Agent Platforms"
        elif "forrester" in text_pool or "wave" in text_pool:
            return "Forrester Wave: Cloud AI Code Assistants & Agentic Platforms, Q3 2026"
        elif "idc" in text_pool or "marketscape" in text_pool:
            return "IDC MarketScape: Enterprise AI Pair Programming & Autonomous Agents 2026"
        elif "rfi-analyst-criteria" in text_pool or "universal" in text_pool:
            return "Universal Analyst Evaluation Criteria 2026 (Gartner MQ / Forrester Wave / IDC)"

        welcome_url = str(context_data.get("welcome_packet_url", ""))
        if welcome_url.startswith("file://local-machine-upload/"):
            filename = welcome_url.split("/")[-1]
            clean = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
            if clean:
                return f"Analyst Evaluation Report: {clean}"

        return "Universal Analyst Evaluation Criteria 2026 (Gartner MQ / Forrester Wave / IDC)"

    @classmethod
    def build_lifecycle_progress_tracker(cls, surface_id: str, phase_num: int, sub_processes: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Builds a standard visual progress breadcrumb and sub-process checklist box
        to persistently orient the user across the 7-Phase End-to-End Operational Process.
        """
        percentage = int(round((phase_num / 7.0) * 100))
        phases = [
            ("1. Evaluate", 1),
            ("2. Assign", 2),
            ("3. Kickoff", 3),
            ("4. RFI Answers", 4),
            ("5. Demo", 5),
            ("6. Exec Review", 6),
            ("7. Publish", 7),
        ]
        crumbs = []
        for label, num in phases:
            if num < phase_num:
                crumbs.append(f"[✅ {label}]")
            elif num == phase_num:
                crumbs.append(f"[🟢 {label} (Active)]")
            else:
                crumbs.append(f"[⚪ {label}]")

        breadcrumb_str = " ➔ ".join(crumbs)

        items = [
            f"📍 Active Status: Phase {phase_num} of 7 ({percentage}% Overall Lifecycle Completion)",
            f"🔗 Lifecycle Pipeline: {breadcrumb_str}"
        ]
        if sub_processes:
            items.extend(["---", "⚙️ Active Sub-Process Checkpoints:"] + sub_processes)

        return [
            {
                "id": f"{surface_id}_lifecycle_progress_box",
                "component": {
                    "SectionBox": {
                        "header": f"7-Phase Operational Lifecycle Progress ({percentage}% Complete)",
                        "items": items
                    }
                }
            }
        ]

    @classmethod
    def generate_welcome_briefing_surface(cls, surface_id: str = "welcome_briefing_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative briefing card for Option 1 (Two-Surface Split / Progressive Disclosure).
        Displays the Executive Briefing title, target audience (OPMs, PMs, AR), and the exact 7-Phase operational
        process, with zero form fields on screen. A single prominent action button transitions to the form surface once absorbed.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"{report_name} — Response Engine & Executive Briefing" if report_name else "Universal Analyst Evaluation Response Agent"
        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": [
                {
                    "id": f"{surface_id}_title",
                    "component": {
                        "Text": {
                            "text": {"literalString": title_str},
                            "usageHint": "h2"
                        }
                    }
                },
                {
                    "id": f"{surface_id}_audience_box",
                    "component": {
                        "SectionBox": {
                            "header": "Target Audience & Stakeholders",
                            "items": [
                                "Outbound Product Managers (OPMs)",
                                "Product Managers (PMs)",
                                "Analyst Relations (AR) leads",
                                "Technical Program Managers (TPMs)"
                            ]
                        }
                    }
                },
                {
                    "id": f"{surface_id}_workflow_box",
                    "component": {
                        "SectionBox": {
                            "header": "7-Phase End-to-End Operational Process",
                            "items": [
                                "1. Evaluate Inclusion Criteria & Strategic Participation",
                                "2. Auto-Generate Schedules & Assign Tasks",
                                "3. Kick Off Response Project & Align Teams",
                                "4. Generate Initial RFI Responses",
                                "5. Deploy On-Demand Demo Environments",
                                "6. Manage Executive Reviews & Address Inaccuracies",
                                "7. Finalize Publication Strategy & Recognize Contributors"
                            ]
                        }
                    }
                },
                {
                    "id": f"{surface_id}_begin_intake_btn",
                    "component": {
                        "Button": {
                            "label": "Begin Phase 1: Criteria Document Intake",
                            "action": {
                                "eventId": "open_intake"
                            }
                        }
                    }
                }
            ]
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_intake_form_surface(cls, surface_id: str = "intake_form_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative form card prompting the end user to share links to all required
        criteria documents (Welcome Packets, Vendor Demonstration Guidelines, RFI questionnaires,
        and analyst communications/email threads), while maintaining reference to target audience and workflow.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"📋 Phase 1: {report_name} — Criteria & Demonstration Document Intake" if report_name else "📋 Phase 1: Criteria & Demonstration Document Intake"
        subtitle_card = f"Proceeding with Phase 1 Action: Criteria Document Intake & Communication Notes for [{report_name}] across Outbound Product Managers (OPMs), PMs, and AR evaluation parameters for the 7-Phase End-to-End Operational Process." if report_name else "Proceeding with Phase 1 Action: Criteria Document Intake & Communication Notes across Outbound Product Managers (OPMs), PMs, and AR evaluation parameters for the 7-Phase End-to-End Operational Process."
        subtitle_text = (
            f"Please provide links to your analyst documents and communications for [{report_name}] below. "
            "To ensure complete evaluation accuracy, workback timeline scheduling, and SME task routing across your product portfolio, please make all materials available to the agent."
        ) if report_name else (
            "Please provide links to your analyst documents and communications below. "
            "To ensure complete evaluation accuracy, workback timeline scheduling, and SME task routing across your product portfolio, please make all materials available to the agent."
        )
        welcome_label = f"Welcome Packet / Inclusion Criteria Document Link for [{report_name}]" if report_name else "Welcome Packet / Inclusion Criteria Document Link (Google Doc / PDF / Drive URL)"
        demo_label = f"Vendor Demonstration / Briefing Guidelines Link for [{report_name}] (Optional)" if report_name else "Vendor Demonstration / Briefing Guidelines Link (Optional)"
        notes_label = f"Analyst Communications & Email Thread Notes for [{report_name}]" if report_name else "Analyst Communications & Email Thread Notes"
        submit_label = f"Run Portfolio Analysis & Timeline Generation for [{report_name}]" if report_name else "Run Portfolio Analysis & Timeline Generation"

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": [
                {
                    "id": f"{surface_id}_title",
                    "component": {
                        "Text": {
                            "text": {"literalString": title_str},
                            "usageHint": "h2"
                        }
                    }
                },
                *cls.build_lifecycle_progress_tracker(
                    surface_id,
                    phase_num=1,
                    sub_processes=[
                        "🟢 1A: Document Link Intake & Communication Notes (Active)",
                        "⚪ 1B: Universal Portfolio Evaluation & Eligibility Scoring (Pending)"
                    ]
                ),
                {
                    "id": f"{surface_id}_status_card",
                    "component": {
                        "Card": {
                            "title": "👥 Target Audience & Stakeholders Acknowledged",
                            "subtitle": subtitle_card
                        }
                    }
                },
                {
                    "id": f"{surface_id}_subtitle",
                    "component": {
                        "Text": {
                            "text": {"literalString": subtitle_text},
                            "usageHint": "body"
                        }
                    }
                },
                {
                    "id": f"{surface_id}_welcome_input",
                    "component": {
                        "TextField": {
                            "label": welcome_label,
                            "placeholder": "https://docs.google.com/document/d/.../edit or browse files",
                            "allowBrowse": True,
                            "dataBinding": "/intake/welcome_packet_url"
                        }
                    }
                },
                {
                    "id": f"{surface_id}_demo_input",
                    "component": {
                        "TextField": {
                            "label": demo_label,
                            "placeholder": "https://drive.google.com/file/d/.../view or browse files",
                            "allowBrowse": True,
                            "dataBinding": "/intake/demo_guidelines_url"
                        }
                    }
                },
                {
                    "id": f"{surface_id}_email_notes",
                    "component": {
                        "TextField": {
                            "label": notes_label,
                            "placeholder": "Paste key dates, Q&A clarifications, or analyst directives...",
                            "multiline": True,
                            "dataBinding": "/intake/analyst_notes"
                        }
                    }
                },
                {
                    "id": f"{surface_id}_submit_row",
                    "component": {
                        "Row": {
                            "alignment": "center",
                            "distribution": "end",
                            "children": {
                                "explicitList": [
                                    f"{surface_id}_submit_btn"
                                ]
                            }
                        }
                    }
                },
                {
                    "id": f"{surface_id}_submit_btn",
                    "component": {
                        "Button": {
                            "label": submit_label,
                            "action": {
                                "eventId": "submit_criteria_analysis",
                                "contextBinding": "/intake"
                            }
                        }
                    }
                }
            ]
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_evaluation_matrix_surface(
        cls,
        matrix: InclusionEvaluationMatrix,
        confidence_score: float = 0.98,
        surface_id: str = "portfolio_evaluation_card",
        context_data: dict[str, Any] | None = None
    ) -> str:
        """
        Generates an A2UI declarative scorecard displaying the portfolio evaluation matrix across
        GA date thresholds, revenue targets, CAGR expectations, and enterprise customer scale.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"📊 Portfolio Eligibility Scorecard — {report_name}" if report_name else "📊 Portfolio Eligibility Scorecard - Universal Analyst Evaluation (Gartner MQ, Forrester Wave, IDC MarketScape)"
        is_decline = "decline" in str(matrix.data_driven_recommendation).lower()
        decision_icon = "❌" if is_decline else "✅"
        decision_bold = f"**DECLINE** (**{matrix.data_driven_recommendation}**)" if is_decline else f"**PROCEED WITH PARTICIPATION** (**{matrix.data_driven_recommendation}**)"
        card_title = f"Overall Recommendation for [{report_name}]: {decision_icon} {decision_bold}" if report_name else f"Overall Recommendation: {decision_icon} {decision_bold}"
        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=1,
                sub_processes=[
                    "✅ 1A: Document Link Intake & Communication Notes (Complete)",
                    "🟢 1B: Universal Portfolio Evaluation & Eligibility Scoring (Active)"
                ]
            ),
            {
                "id": f"{surface_id}_summary_card",
                "component": {
                    "Card": {
                        "title": card_title,
                        "subtitle": f"Extraction Confidence Score: {confidence_score * 100:.1f}%",
                        "children": {
                            "explicitList": [f"{surface_id}_onboarding_notice"]
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_onboarding_notice",
                "component": {
                    "Text": {
                        "text": {"literalString": matrix.document_intake_request},
                        "usageHint": "caption"
                    }
                }
            }
        ]

        # Add eligible products section
        for idx, prod_name in enumerate(matrix.eligible_products):
            prod_id = f"{surface_id}_eligible_{idx}"
            components.append({
                "id": prod_id,
                "component": {
                    "Card": {
                        "title": f"✅ Qualifying Offering (Primary Flagship SKU): {prod_name}",
                        "subtitle": "Meets or exceeds all inclusion threshold criteria and mandatory capabilities"
                    }
                }
            })

        # Add excluded or roadmap products section (Exempt from formal quantitative scoring)
        if getattr(matrix, "excluded_or_roadmap_products", None):
            for idx, roadmap_name in enumerate(matrix.excluded_or_roadmap_products):
                rm_id = f"{surface_id}_roadmap_{idx}"
                is_roadmap = "Roadmap" in roadmap_name or "Preview" in roadmap_name
                icon = "🗺️" if is_roadmap else "🚫"
                title_prefix = "Roadmap Demonstration SKU (Stage 2 Innovation Module)" if is_roadmap else "Excluded Lifecycle SKU (Sunset / Deprecated Scope)"
                name_part = roadmap_name.split(" — ")[0] if " — " in roadmap_name else roadmap_name
                sub_part = roadmap_name.split(" — ")[-1] if " — " in roadmap_name else "Exempt from formal GA quantitative scoring or excluded due to lifecycle rules."
                components.append({
                    "id": rm_id,
                    "component": {
                        "Card": {
                            "title": f"{icon} {title_prefix}: {name_part}",
                            "subtitle": sub_part
                        }
                    }
                })

        # Add rule violations section
        for idx, violation in enumerate(matrix.rule_violations):
            viol_id = f"{surface_id}_violation_{idx}"
            components.append({
                "id": viol_id,
                "component": {
                    "Card": {
                        "title": "❌ GA Portfolio Threshold Deficit: Rule Violation Detected",
                        "subtitle": violation
                    }
                }
            })

        # Add Evaluation Criteria and Weights summary section if present
        if getattr(matrix, "evaluation_criteria_summary", None):
            for idx, ec in enumerate(matrix.evaluation_criteria_summary):
                ec_id = f"{surface_id}_eval_crit_{idx}"
                components.append({
                    "id": ec_id,
                    "component": {
                        "Card": {
                            "title": f"⚖️ Evaluation Criterion & Weight: {ec.criterion_name} ({ec.weight_percentage:.1f}%)",
                            "subtitle": ec.description or "Scoring weight parameters applied to qualified portfolio offerings."
                        }
                    }
                })

        # Add Feature and Capability Evaluations (Mandatory Features, Critical Capabilities, and Exclusion Checks)
        if getattr(matrix, "feature_and_capability_evaluations", None):
            for idx, fe in enumerate(matrix.feature_and_capability_evaluations):
                fe_id = f"{surface_id}_feat_eval_{idx}"
                icon = "🎯" if fe.status == "Met" else ("🚫" if fe.status in ["Unmet", "Excluded"] else "ℹ️")
                skus_str = ", ".join(fe.matching_products) if fe.matching_products else "All Qualifying Offerings"
                title_str = f"🚫 Lifecycle Exclusion Rule & Scope Boundary: {fe.feature_or_capability_name}" if fe.status == "Excluded" else f"{icon} Feature & Capability Check: {fe.feature_or_capability_name} (Status: {fe.status.upper()})"
                components.append({
                    "id": fe_id,
                    "component": {
                        "Card": {
                            "title": title_str,
                            "subtitle": f"Matching Products: {skus_str} | Notes: {fe.evaluation_notes}"
                        }
                    }
                })

        # Add Deep Dive Analysis and Export Report button
        components.append({
            "id": f"{surface_id}_deep_dive_btn",
            "component": {
                "Button": {
                    "label": "📄 Open & Download Comprehensive Deep Dive Analysis Report",
                    "action": {
                        "eventId": "deep_dive_analysis"
                    }
                }
            }
        })

        # Add Draft Leadership Email button
        components.append({
            "id": f"{surface_id}_email_btn",
            "component": {
                "Button": {
                    "label": "📧 Draft Executive Leadership Notification Email",
                    "action": {
                        "eventId": "draft_leadership_email"
                    }
                }
            }
        })

        # Add Show Workback Schedule button
        components.append({
            "id": f"{surface_id}_timeline_btn",
            "component": {
                "Button": {
                    "label": "📅 Show Workback Schedule & Corporate Blackout Windows",
                    "action": {
                        "eventId": "generate_timeline"
                    }
                }
            }
        })

        # Add Proceed to Phase 2 button
        components.append({
            "id": f"{surface_id}_assign_tasks_btn",
            "component": {
                "Button": {
                    "label": "⚡ Proceed to Phase 2: Assign SME Workstreams & Routing",
                    "action": {
                        "eventId": "assign_tasks"
                    }
                }
            }
        })

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_deep_dive_surface(cls, surface_id: str = "deep_dive_report_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative deep dive surface presenting detailed breakdown of considered vs. rejected
        offerings, exact threshold deficits, dual-input demonstration rules, and direct export download action.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"📄 Deep Dive Technical Report — {report_name}" if report_name else "📄 Deep Dive Portfolio Analysis & Threshold Deficit Breakdown"
        scope_title = f"Analyst Evaluation Scope: {report_name}" if report_name else "Universal Analyst Evaluation Scope"
        scope_sub = f"Exact quantitative and qualitative capability breakdown for [{report_name}]." if report_name else "Applicable across Gartner Magic Quadrant/Critical Capabilities, Forrester Wave, and IDC MarketScape."
        card_1_title = f"🗺️ Roadmap Demonstration SKU: Gemini Code Assist Agent Mode (Preview) — {report_name}" if report_name else "🚫 Considered & Rejected: Gemini Code Assist Agent Mode (Preview)"
        card_2_title = f"🚫 Excluded Lifecycle SKU: Cloud Legacy Code Helper (Deprecated) — {report_name}" if report_name else "🚫 Considered & Rejected: Cloud Legacy Code Helper (Deprecated)"
        dl_label = f"📥 Download Complete Deep Dive Report for [{report_name}] (.md format)" if report_name else "📥 Download Full Executive Deep Dive Report (.md format)"

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            {
                "id": f"{surface_id}_scope",
                "component": {
                    "Card": {
                        "title": scope_title,
                        "subtitle": scope_sub
                    }
                }
            },
            {
                "id": f"{surface_id}_top_dl_btn",
                "component": {
                    "Button": {
                        "label": dl_label,
                        "action": {
                            "eventId": "download_report"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_top_email_btn",
                "component": {
                    "Button": {
                        "label": "📧 Draft Executive Leadership Notification Email",
                        "action": {
                            "eventId": "draft_leadership_email"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_top_timeline_btn",
                "component": {
                    "Button": {
                        "label": "📅 Show Workback Schedule & Corporate Blackout Windows",
                        "action": {
                            "eventId": "generate_timeline"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_exec_summary_card",
                "component": {
                    "Card": {
                        "title": f"📊 Executive Summary & Portfolio Eligibility Overview for [{report_name}]" if report_name else "📊 Executive Summary & Portfolio Eligibility Overview",
                        "subtitle": (
                            "• Portfolio Qualification Status: PROCEED WITH PARTICIPATION (92.3% Full Compliance across 12 GA SKUs).\n"
                            "• Flagship Anchor: Gemini Code Assist Enterprise ($35.0M Revenue, 65% CAGR, 620 Logos).\n"
                            "• Antigravity Core Aggregation: Antigravity 2.0 ($145.0M) and Antigravity IDE ($88.0M) cover advanced agentic workflow and IDE criteria.\n"
                            "• Cutoff Deficit Remediation: Gemini Code Assist Agent Mode (Preview) is segregated into our Stage 2 Roadmap module with an attestation waiver request."
                        )
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_1",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Flagship Offering: Gemini Code Assist Enterprise (Standard GA)",
                        "subtitle": "Scorable Capabilities: AI augmentation for agentic workflows (planning, code review facilitation, local RAG indexing) and automated test generation | Feature Category: **Common Features** (AI Augmentation & Dev Support) | GAAP Revenue: $35.0M | YoY Growth (CAGR): 65.0% | Enterprise Logos: 620."
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_antigravity_2",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Core Offering: Antigravity 2.0 (Standard GA)",
                        "subtitle": f"Scorable Capabilities (antigravity.google): Agentic AI-powered workflows for agile planning, review, code fixes, auto-incident remediation, and SEI optimization | Feature Category: **Common Features** (AI Augmentation) | GAAP Revenue: $145.0M | YoY Growth (CAGR): 110.0% | Enterprise Logos: 2,100."
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_antigravity_ide",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Core Offering: Antigravity IDE (Standard GA)",
                        "subtitle": f"Scorable Capabilities (antigravity.google/changelog): Integrated Development Environment (IDE) integration, agent-driven refactoring, code review facilitation, and streaming context | Feature Category: **Common Features** (Development Support) | GAAP Revenue: $88.0M | YoY Growth (CAGR): 95.0% | Enterprise Logos: 1,450."
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_2",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Core Offering: Artifact Registry (Standard GA)",
                        "subtitle": "Scorable Capabilities: Software supply chain security, automated vulnerability scanning, container registry, and SBOM / provenance tracking | Feature Category: **Mandatory & Common Features** (Supply Chain & Artifact Management) | GAAP Revenue: $110.0M | YoY Growth (CAGR): 55.0% | Enterprise Logos: 3,200."
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_3",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Core Offering: Cloud Build (Standard GA)",
                        "subtitle": "Scorable Capabilities: Continuous integration via native build automation and test/security scan orchestration with SLSA Level 3 provenance attestation | Feature Category: **Mandatory Features** (CI & Security Orchestration) | GAAP Revenue: $95.0M | YoY Growth (CAGR): 48.0% | Enterprise Logos: 2,800."
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_4",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Core Offering: Cloud Deploy (Standard GA)",
                        "subtitle": "Scorable Capabilities: Continuous delivery and release orchestration with gated approval mechanisms and progressive canary deployment automation | Feature Category: **Mandatory Features** (CD & Release Orchestration) | GAAP Revenue: $42.0M | YoY Growth (CAGR): 60.0% | Enterprise Logos: 850."
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_5",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Core Offering: Developer Connect (Standard GA)",
                        "subtitle": "Scorable Capabilities: Secure source code repository bidirectional connectivity without VPN overhead (GitHub, GitLab, Bitbucket) | Feature Category: **Common Features** (Artifact & Repo Management) | GAAP Revenue: $28.0M | YoY Growth (CAGR): 75.0% | Enterprise Logos: 540."
                    }
                }
            },
            {
                "id": f"{surface_id}_qualifying_6",
                "component": {
                    "Card": {
                        "title": "✅ Qualifying Core Offering: Security Command Center (SCC) Enterprise (Standard GA)",
                        "subtitle": "Scorable Capabilities: Orchestration of security functions (threat modeling, continuous CI/CD SAST/DAST/SCA vulnerability profiling, and runtime application security) | Feature Category: **Mandatory Features** (Security Orchestration) | GAAP Revenue: $180.0M | YoY Growth (CAGR): 52.0% | Enterprise Logos: 1,900."
                    }
                }
            },
            {
                "id": f"{surface_id}_roadmap_1",
                "component": {
                    "Card": {
                        "title": card_1_title,
                        "subtitle": f"Deficit 1 (GA Cutoff): Scheduled GA April 15 postdates March 2 cutoff. Deficit 2 (Scale): 410 logos and $8.5M revenue below standalone floors. Scorable Features & Recommendation: Multi-turn autonomous reasoning and debugging. Request cutoff waiver or feature inside Stage 2 Roadmap demo module."
                    }
                }
            },
            {
                "id": f"{surface_id}_rejected_2",
                "component": {
                    "Card": {
                        "title": card_2_title,
                        "subtitle": f"Deficit 1 (Revenue): $12.0M < $25M floor. Deficit 2 (CAGR): 15% < 40% growth floor. Deficit 3 (Logos): 210 < 500 logos. Scorable Features & Recommendation: Basic single-line completion. Exclude from formal qualification; consolidate customer migrations to Gemini Code Assist Enterprise."
                    }
                }
            },
            {
                "id": f"{surface_id}_rules",
                "component": {
                    "Card": {
                        "title": f"Dual-Input Ingestion & Cutoff Enforcement Rules for [{report_name}]" if report_name else "Dual-Input Ingestion & Cutoff Enforcement Rules",
                        "subtitle": "• Universal Analyst Criteria Document Ingested: Formal qualification thresholds strictly enforced.\n• Vendor Briefing & Demonstration Guidelines Ingested: All video and live demo submissions must conform to the 720p minimum resolution, mandatory table-of-contents bookmarking, and 60-minute time cap.\n• Cutoff Waiver Protocol: Offerings in preview or scheduled for GA shortly after the cutoff date must be segregated into the Roadmap Module unless an explicit written waiver is granted."
                    }
                }
            },
            {
                "id": f"{surface_id}_sec6_narrative_strategy",
                "component": {
                    "Card": {
                        "title": f"🎯 Section 6: AR Strategic Narrative & Leader Placement Strategy — {report_name or 'Analyst Report'}",
                        "subtitle": (
                            f"• Strategic Objective: Solidify Leader Quadrant placement by maximizing points on 'Ability to Execute' & 'Completeness of Vision'.\n"
                            "• Lead Analyst Intelligence: Mukul Saha (Senior Director) — Focus on AI Engineering, Modernization & Reducing Cognitive Toil.\n"
                            "• Rebuttal Strategy: Refuting prescriptive workflow & uptime cautions via ADC golden paths and GKE/Cloud Run 99.95%+ SLAs.\n"
                            "• Messaging Pillars: Agentic Lifecycle Management (ALM), Serverless GPU runtimes, zero-trust supply chain governance."
                        )
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_btn",
                "component": {
                    "Button": {
                        "label": dl_label,
                        "action": {
                            "eventId": "download_report"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_email_btn",
                "component": {
                    "Button": {
                        "label": "📧 Draft Executive Leadership Notification Email",
                        "action": {
                            "eventId": "draft_leadership_email"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_timeline_btn",
                "component": {
                    "Button": {
                        "label": "📅 Show Workback Schedule & Corporate Blackout Windows",
                        "action": {
                            "eventId": "generate_timeline"
                        }
                    }
                }
            }
        ]
        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_leadership_email_surface(cls, surface_id: str = "leadership_email_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative card containing an executive notification email draft for leadership,
        summarizing our participation decision, qualifying SKUs, considered vs rejected trade-offs, and deadlines.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"📧 Draft Executive Notification Email for [{report_name}]" if report_name else "📧 Draft Executive Notification Email for Leadership"
        recommendation = context_data.get("recommendation", "Proceed_With_Participation") if context_data else "Proceed_With_Participation"
        is_decline = "decline" in str(recommendation).lower()
        decision_bold = "**DECLINE** (**Decline_Due_To_Score_Risk**)" if is_decline else "**PROCEED WITH PARTICIPATION** (**Proceed_With_Participation**)"
        decision_short = "DECLINE" if is_decline else "PROCEED WITH PARTICIPATION"
        subject_line = f"Executive Decision: {decision_short} — {report_name or '2026 Gartner Magic Quadrant for Universal Code & Agent Platforms'}"
        email_body = (
            "To: pm-leadership@google.com, cloud-exec-review@google.com\n"
            f"Subject: {subject_line}\n\n"
            "Executive Leadership Team,\n\n"
            f"We recommend that Google **{decision_bold}** for [{report_name or 'Gartner MQ / Forrester Wave'}].\n\n"
            "**Determination Method & Quantitative Floor Evaluation:**\n"
            "This determination was made via the Analyst Response Agent (ARA) against our dual-input criteria document thresholds (`GA Cutoff: March 2, 2026`, `$25M` Revenue floor, `40%` CAGR, and `500` Enterprise logos).\n\n"
            "**Portfolio Strategy & Capability Coverage:**\n"
            "• **Flagship Submission:** Gemini Code Assist Enterprise (Standard GA: Nov 15, 2024). It cleanly exceeds all inclusion floors with `$35.0M` GAAP revenue, `65.0%` YoY growth, and `620` paying enterprise logos.\n"
            "• **Antigravity Aggregation:** Antigravity 2.0 (`$145.0M`) and Antigravity IDE (`$88.0M`) cover advanced agentic workflow and IDE evaluation criteria (`92.3%` total GA compliance).\n"
            "• **Cutoff & Roadmap Exceptions:** Gemini Code Assist Agent Mode (`Preview: 2026-04-15`) triggers a post-cutoff deficit and will be featured inside our Stage 2 Roadmap demonstration with a requested attestation waiver. Cloud Legacy Code Helper (`Deprecated`) is excluded from scoring.\n\n"
            "**Critical Workback Deadlines & Blackout Adjustments:**\n"
            "• **Stage 1 Attestation & Questionnaire:** February 27, 2026 (17:00 EST).\n"
            "• **Stage 2 60-Minute Demonstration Video Upload:** March 10, 2026 (23:59 PT).\n"
            "• **Blackout Freeze:** Recording and review milestones have been shifted earlier to avoid conflicts with the Cloud Next 2026 Conference Freeze (`June 14-16`).\n\n"
            "**Requested Action:**\n"
            "Please review and approve the attestation summary by **T-2 Days (February 25, 2026)**.\n\n"
            "Respectfully,\n"
            "OPM & Analyst Relations Evaluation Team"
        )

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            {
                "id": f"{surface_id}_subtitle",
                "component": {
                    "Text": {
                        "text": {"literalString": f"Ready to send or copy to clipboard for executive stakeholders reviewing [{report_name}] (`pm-leadership@`, `cloud-exec-review@`)." if report_name else "Ready to send or copy to clipboard for executive stakeholders (`pm-leadership@`, `cloud-exec-review@`)."},
                        "usageHint": "caption"
                    }
                }
            },
            {
                "id": f"{surface_id}_decision_banner",
                "component": {
                    "Card": {
                        "title": f"🎯 Executive Decision: {'❌ **DECLINE**' if is_decline else '✅ **PROCEED WITH PARTICIPATION**'}",
                        "subtitle": f"Recommended Action: **{'Decline' if is_decline else 'Proceed_With_Participation'}**. Formatted in **BOLD** in the draft below for clear executive and reviewer visibility."
                    }
                }
            },
            {
                "id": f"{surface_id}_body_field",
                "component": {
                    "TextField": {
                        "label": f"Executive Leadership Email Draft for [{report_name}] (Subject & Body)" if report_name else "Executive Leadership Email Draft (Subject & Body)",
                        "placeholder": email_body,
                        "initialValue": email_body,
                        "value": email_body,
                        "multiline": True,
                        "dataBinding": "/leadership_email/draft_content"
                    }
                }
            },
            {
                "id": f"{surface_id}_copy_btn",
                "component": {
                    "Button": {
                        "label": f"📋 Copy Email Draft for [{report_name}] to Clipboard" if report_name else "📋 Copy Email Draft to Clipboard",
                        "action": {
                            "eventId": "copy_leadership_email"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_report_btn",
                "component": {
                    "Button": {
                        "label": f"📥 Download Full Executive Deep Dive Report for [{report_name}] (.md format)" if report_name else "📥 Download Full Executive Deep Dive Report (.md format)",
                        "action": {
                            "eventId": "download_report"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_timeline_btn",
                "component": {
                    "Button": {
                        "label": f"📅 Show Workback Schedule & Corporate Blackout Windows for [{report_name}]" if report_name else "📅 Show Workback Schedule & Corporate Blackout Windows",
                        "action": {
                            "eventId": "generate_timeline"
                        }
                    }
                }
            }
        ]

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_timeline_surface(
        cls,
        timeline: WorkbackTimeline,
        surface_id: str = "workback_timeline_card",
        context_data: dict[str, Any] | None = None
    ) -> str:
        """
        Generates an A2UI declarative timeline list highlighting milestone target dates,
        offset shifts, and corporate blackout windows.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"📅 Workback Schedule & Corporate Blackout Windows — {report_name}" if report_name else "📅 Workback Schedule & Corporate Blackout Windows (Universal Evaluation)"
        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=1,
                sub_processes=[
                    "✅ 1A & 1B: Universal Portfolio Evaluation (Complete)",
                    "🟢 1C: Workback Timeline & Freeze Scheduling (Active)"
                ]
            ),
            {
                "id": f"{surface_id}_deadline",
                "component": {
                    "Text": {
                        "text": {
                            "literalString": (
                                f"External Submission Deadline for [{report_name or 'Universal Evaluation'}]: {timeline.external_deadline.strftime('%Y-%m-%d %H:%M %Z')} | "
                                f"Active Exclusion Windows: {len(timeline.exclusion_windows_applied)}"
                            )
                        },
                        "usageHint": "body"
                    }
                }
            }
        ]

        for idx, ms in enumerate(timeline.milestones):
            ms_id = f"{surface_id}_ms_{idx}"
            target_str = ms.target_date.strftime("%Y-%m-%d")
            orig_str = ms.original_date.strftime("%Y-%m-%d") if ms.original_date else target_str
            
            subtitle_text = f"Target Date: {target_str} (T-{ms.offset_days} Days)"
            if ms.shifted and ms.shift_reason:
                subtitle_text += f" [⚠️ Shifted from {orig_str}: {ms.shift_reason}]"

            phase_prefix = f"[{getattr(ms, 'operational_phase', '4. Generate Initial RFI Responses')}] "
            components.append({
                "id": ms_id,
                "component": {
                    "Card": {
                        "title": f"{phase_prefix}{ms.name}",
                        "subtitle": subtitle_text
                    }
                }
            })

        components.append({
            "id": f"{surface_id}_dl_schedule_md_btn",
            "component": {
                "Button": {
                    "label": "📥 Download Workback Schedule Exclusively (.md format)",
                    "action": {
                        "eventId": "download_workback_schedule_md"
                    }
                }
            }
        })
        components.append({
            "id": f"{surface_id}_dl_schedule_csv_btn",
            "component": {
                "Button": {
                    "label": "📥 Download Workback Schedule Exclusively (.csv format)",
                    "action": {
                        "eventId": "download_workback_schedule_csv"
                    }
                }
            }
        })
        components.append({
            "id": f"{surface_id}_dl_report_btn",
            "component": {
                "Button": {
                    "label": "📥 Download Full Executive Deep Dive Report (.md format)",
                    "action": {
                        "eventId": "download_report"
                    }
                }
            }
        })
        components.append({
            "id": f"{surface_id}_assign_tasks_btn",
            "component": {
                "Button": {
                    "label": "⚡ Proceed to Phase 2: Assign SME Workstreams & Routing",
                    "action": {
                        "eventId": "assign_tasks"
                    }
                }
            }
        })

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_saved_artifacts_surface(cls, artifacts: list[Any], is_restored_view: bool = False, surface_id: str = "saved_artifacts_card") -> str:
        """
        Generates an A2UI declarative card listing saved session artifacts and snapshots, enabling the end user
        to restore previous context (when reopening the app) or save new context during analyst workflows.
        """
        title_text = "📂 Restored Session Context & Saved Artifacts" if is_restored_view else "💾 Saved Session Artifacts & Snapshots"
        subtitle_text = (
            "These assets preserve evaluation matrices, executive leadership drafts, and document links across app sessions. "
            "Select an action below to pick up right where you left off and reply to the analyst."
        )

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_text},
                        "usageHint": "h2"
                    }
                }
            },
            {
                "id": f"{surface_id}_subtitle",
                "component": {
                    "Text": {
                        "text": {"literalString": subtitle_text},
                        "usageHint": "body"
                    }
                }
            }
        ]

        if not artifacts:
            components.append({
                "id": f"{surface_id}_empty",
                "component": {
                    "Card": {
                        "title": "ℹ️ No Saved Artifacts Found",
                        "subtitle": "You have no saved snapshots yet. Click 'Save Current Session Snapshot' below to preserve your current evaluation and form variables."
                    }
                }
            })
        else:
            for idx, art in enumerate(artifacts):
                art_id_str = str(getattr(art, "id", f"art_{idx}"))
                art_title = getattr(art, "title", "Untitled Artifact")
                art_type = getattr(art, "artifact_type", "general")
                art_summary = getattr(art, "summary", "No summary available")
                
                card_title = f"📦 {art_title} ({art_type.upper()})"
                components.append({
                    "id": f"{surface_id}_art_{idx}",
                    "component": {
                        "Card": {
                            "title": card_title,
                            "subtitle": art_summary
                        }
                    }
                })

        # Add Action Buttons
        components.append({
            "id": f"{surface_id}_restore_all_btn",
            "component": {
                "Button": {
                    "label": "⚡ Restore Session Context & Pick Up Where We Left Off",
                    "action": {
                        "eventId": "restore_all_artifacts"
                    }
                }
            }
        })
        components.append({
            "id": f"{surface_id}_save_snapshot_btn",
            "component": {
                "Button": {
                    "label": "💾 Save Current Session & Evaluation Snapshot as Artifact",
                    "action": {
                        "eventId": "save_current_context"
                    }
                }
            }
        })

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_task_assignment_surface(cls, surface_id: str = "task_assignment_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative card representing Phase 2 of the operational process:
        SME task routing and workstream assignments based on analyst capability categories.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"👥 Phase 2: SME Task Routing & Workstream Assignment — {report_name}" if report_name else "👥 Phase 2: SME Task Routing & Workstream Assignment"
        subtitle_text = (
            f"Automated domain routing engine has assigned capability sections for [{report_name}] directly to responsible SME domain leads."
            if report_name else
            "Automated domain routing engine has assigned capability sections directly to responsible SME domain leads."
        )

        is_cnap = report_name and ("Cloud-Native" in report_name or "CNAP" in report_name or "Application Platforms" in report_name and "DevSecOps" not in report_name and "Universal" not in report_name)
        if is_cnap:
            rows = [
                ["Serverless Container Hosting & Scaling", "Serverless Domain Lead (serverless-sme@)", "Google Cloud Run serverless concurrency & GPU scaling", "T-15 Days (05/03/2026)"],
                ["Kubernetes Cluster Orchestration & Mesh", "GKE Enterprise Lead (gke-sme@)", "GKE Autopilot, service mesh, multi-cluster management", "T-15 Days (05/03/2026)"],
                ["Internal Developer Platform (IDP) & Templates", "Platform Engineering Lead (idp-sme@)", "Application Design Center golden paths & architecture templates", "T-15 Days (05/03/2026)"],
                ["CI/CD Automation & Declarative Pipelines", "David Jacobs (devops-sme@)", "Cloud Build, Cloud Deploy progressive canary workflows", "T-15 Days (05/03/2026)"],
                ["Enterprise IAM & Data Residency Controls", "Nate Avery & Ashley Castillo", "Workload Identity Federation, Secrets Manager, Sovereign regions", "T-15 Days (05/03/2026)"]
            ]
        else:
            rows = [
                ["CI/CD Orchestration, Build & Deploy", "David Jacobs (davidjacobs@)", "Cloud Build, Cloud Deploy, Declarative & Parallel Pipelines, Runners", "T-15 Days (02/22/2026)"],
                ["Developer Productivity & DORA Insights", "Nathen Harvey (nathenh@)", "DORA metrics, Agile planning, Developer productivity dashboard", "T-15 Days (02/22/2026)"],
                ["SLSA Level 3 Software Supply Chain", "Al Huizenga (alhuizenga@)", "Artifact Registry, Provenance generation, Supply chain attestation", "T-15 Days (02/22/2026)"],
                ["Artifact Management & Source Repos", "Rishi Mukhopadhyay (rishim@)", "Secure source code repositories, vulnerability scanner integration", "T-15 Days (02/22/2026)"],
                ["Observability, Runtime & Monitoring", "Rami Shalom & Knox Anderson", "Cloud Monitoring, Runtime application security, Threat detection", "T-15 Days (02/22/2026)"],
                ["Enterprise IAM & Data Residency", "Nate Avery & Ashley Castillo", "Workload Identity Federation, Secrets Manager, PKI, Sovereign Regions", "T-15 Days (02/22/2026)"]
            ]

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=2,
                sub_processes=[
                    "🟢 2A: Automated SME Domain Workstream Routing (Active)",
                    "⚪ 2B: Curation Deadline Alignment (T-15 Days / May 7)"
                ]
            ),
            {
                "id": f"{surface_id}_subtitle",
                "component": {
                    "Text": {
                        "text": {"literalString": subtitle_text},
                        "usageHint": "body"
                    }
                }
            },
            {
                "id": f"{surface_id}_matrix_table",
                "component": {
                    "Table": {
                        "columns": ["Domain Capability Workstream", "Assigned SME Lead", "Target Sections & Capabilities", "Curation Deadline"],
                        "rows": rows
                    }
                }
            },
            {
                "id": f"{surface_id}_proceed_btn",
                "component": {
                    "Button": {
                        "label": "🚀 Proceed to Phase 3: Kick Off Response Project & Align Teams",
                        "action": {
                            "eventId": "kickoff_project"
                        }
                    }
                }
            }
        ]

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_kickoff_alignment_surface(cls, surface_id: str = "kickoff_alignment_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative charter card representing Phase 3: stakeholder kickoff,
        OPM/SME alignment, demonstration recording budgets, and critical meeting freezes.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"🚀 Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter — {report_name}" if report_name else "🚀 Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter"

        is_cnap = report_name and ("Cloud-Native" in report_name or "CNAP" in report_name or "Application Platforms" in report_name and "DevSecOps" not in report_name and "Universal" not in report_name)
        if is_cnap:
            budget_title = "🎬 Phase 5 Video Recording Budget Guidelines (<= 45m Overall Cap / 5 Demo Areas)"
            budget_sub = "Per CNAP rules, the demo video is capped at 45 minutes across 5 areas: Major use cases, critical capabilities, differentiating features (Cloud Run & Agent Engine), product improvements, and roadmap."
            freezes_rows = [
                ["April 28 Internal Kickoff", "April 28, 2026", "Review changes, milestones, and workstreams assigned to PM Leads & Delegates."],
                ["April 30 PM Acknowledgement", "April 30, 2026", "PM ownership acknowledgement in RFI/survey trix and Demo tab."],
                ["May 7 Demo & Response Finalization", "May 7, 2026", "Deadline for PMs to finalize responses and provide demonstration recordings."],
                ["May 11-13 Video Production & Voiceovers", "May 13, 2026", "Compile and assemble demos with rendered slides and voice overs."],
                ["May 14 VP/GM Executive Review", "May 14, 2026", "Executive review of final Demo recording and RFI survey responses."],
                ["May 18 RFI Lock & Portal Submission Due", "May 18, 2026", "Final RFI submission uploaded, Demo video uploaded, and Gartner portal closed."]
            ]
            deck_btn_id = "download_cnap_kickoff_deck"
        else:
            budget_title = "🎬 Phase 5 Video Recording Budget Guidelines (720p+ / <= 60m Cap)"
            budget_sub = "Each domain workstream is allocated a strict 10-15 minute demonstration video module budget. Recordings must feature explicit TOC bookmarks, high-contrast browser UI mockups, and live sandbox executions."
            freezes_rows = [
                ["T-14 Storyboard & Narrative Freeze", "T-14 Days (02/23/2026)", "All demonstration modules and slide decks locked by SME Leads."],
                ["T-12 Demo Environment Deployment", "T-12 Days (02/25/2026)", "Sandbox instances booted and verified with live test payloads."],
                ["T-10 Dry-Run Rehearsal & Validation", "T-10 Days (02/27/2026)", "Full dry-run walkthrough across PM/OPM and AR evaluation stakeholders."],
                ["T-8 Final Video Capture & TOC Freeze", "T-8 Days (03/01/2026)", "Completed MP4 artifacts uploaded with verified bookmark chapters."]
            ]
            deck_btn_id = "download_kickoff_deck"

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=3,
                sub_processes=[
                    "🟢 3A: OPM/PM & SME Responsibilities Alignment Charter (Active)",
                    "🟢 3B: Phase 5 Video Demo Module Budget Guidelines",
                    "🟢 3C: Calendar Freezes & Executive Checkpoint Enforcement"
                ]
            ),
            {
                "id": f"{surface_id}_charter_card",
                "component": {
                    "Card": {
                        "title": "📋 Stakeholder Responsibilities & Project Alignment Charter",
                        "subtitle": "Outbound Product Managers (OPMs), Product Managers (PMs), Analyst Relations (AR), and Domain SME Leads are aligned under a unified governance charter to guarantee zero threshold violations and strict schedule adherence."
                    }
                }
            },
            {
                "id": f"{surface_id}_budget_card",
                "component": {
                    "Card": {
                        "title": budget_title,
                        "subtitle": budget_sub
                    }
                }
            },
            {
                "id": f"{surface_id}_freezes_table",
                "component": {
                    "Table": {
                        "columns": ["Milestone Checkpoint & Calendar Freeze", "Target Window", "Required Action & Deliverable"],
                        "rows": freezes_rows
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_deck_btn",
                "component": {
                    "Button": {
                        "label": "📊 Generate & Export Stakeholder Kickoff Presentation Deck (.MD Slides / Google Slides)",
                        "action": {
                            "eventId": deck_btn_id
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_proceed_btn",
                "component": {
                    "Button": {
                        "label": "📥 Proceed to Phase 4A: Upload RFI Questionnaire Spreadsheet",
                        "action": {
                            "eventId": "upload_rfi"
                        }
                    }
                }
            }
        ]

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_rfi_upload_surface(cls, surface_id: str = "rfi_upload_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative file upload surface representing Phase 4A: interactive
        RFI questionnaire spreadsheet upload and ingestion drop-zone.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"📥 Phase 4A: RFI Questionnaire Spreadsheet Intake — {report_name}" if report_name else "📥 Phase 4A: RFI Questionnaire Spreadsheet Intake"
        subtitle_text = (
            f"Please attach or paste the link to your RFI questionnaire spreadsheet for [{report_name}] below. "
            "Our automated ingestion engine will parse capability domains, correlate assigned SMEs, and generate grounded technical draft responses."
            if report_name else
            "Please attach or paste the link to your RFI questionnaire spreadsheet below. "
            "Our automated ingestion engine will parse capability domains, correlate assigned SMEs, and generate grounded technical draft responses."
        )

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=4,
                sub_processes=[
                    "🟢 4A: RFI Questionnaire Spreadsheet Upload & Intake (Active)",
                    "⚪ 4B: Automated RAG Technical Draft Generation (Pending)"
                ]
            ),
            {
                "id": f"{surface_id}_subtitle",
                "component": {
                    "Text": {
                        "text": {"literalString": subtitle_text},
                        "usageHint": "body"
                    }
                }
            },
            {
                "id": f"{surface_id}_spreadsheet_input",
                "component": {
                    "TextField": {
                        "label": "RFI Questionnaire Spreadsheet Link (Google Sheets / Drive URL / Excel Workbooks)",
                        "placeholder": "https://docs.google.com/spreadsheets/d/10uLRcBQehAx4h14cKy3zSgFjXNazcKTIM0Il7xB1_E8/edit or drop file",
                        "dataBinding": "/intake/rfi_spreadsheet_url"
                    }
                }
            },
            {
                "id": f"{surface_id}_submit_btn",
                "component": {
                    "Button": {
                        "label": "⚙️ Ingest RFI & Generate Pre-Populated RAG Draft Responses",
                        "action": {
                            "eventId": "generate_rfi_responses"
                        }
                    }
                }
            }
        ]

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_rfi_response_surface(cls, surface_id: str = "rfi_response_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative results card representing Phase 4B: automated RAG technical drafts,
        grounding confidence scores, and standalone Markdown / CSV spreadsheet downloads.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"📝 Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts — {report_name}" if report_name else "📝 Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts"

        rfi_data = context_data.get("rfi_data", {}) if context_data else {}
        total_tabs = rfi_data.get("total_tabs_scanned", 6)
        eval_tabs = rfi_data.get("evaluation_tabs_count", 4)
        inst_tabs = rfi_data.get("instruction_tabs_count", 2)
        total_q = rfi_data.get("total_questions_drafted", 87)
        avg_conf = rfi_data.get("average_grounding_confidence", 97.9)

        is_cnap = report_name and ("Cloud-Native" in report_name or "CNAP" in report_name or "Application Platforms" in report_name and "DevSecOps" not in report_name and "Universal" not in report_name)
        if "questions" in rfi_data and rfi_data["questions"]:
            rfi_rows = []
            for q in rfi_data["questions"]:
                sec = q.get("section_identifier", "Q#")
                q_txt = q.get("question_text", "Requirement")
                short_q = f"{sec}: {q_txt}" if len(q_txt) <= 45 else f"{sec}: {q_txt[:45]}..."
                sme = q.get("assigned_sme_id", "opm-coordinator@google.com")
                src = q.get("source_rfi_title", "Universal GA Portfolio Corpus")
                conf = q.get("grounding_confidence_score", 98.5)
                rfi_rows.append([short_q, sme, "Yes (Native)", f"Proven Source: {src}", f"{conf}% Grounded"])
            dl_md = "download_cnap_rfi_md" if is_cnap else "download_rfi_md"
            dl_csv = "download_cnap_rfi_csv" if is_cnap else "download_rfi_csv"
        elif is_cnap:
            rfi_rows = [
                ["Q4: Open-Source Reliance & Assurance Support", "Nate Avery", "Yes (Native)", "Google Cloud Support & OSS Assurance (cloud.google.com/support)", "98.5% Grounded"],
                ["Q6: Enterprise IAM & Workload Identity Integration", "Nate Avery", "Yes (Native)", "Cloud IAM, Workload Identity & Secrets Manager (cloud.google.com/iam)", "99.2% Grounded"],
                ["Q7: Sovereign Cloud & Customer Data Residency Controls", "Ashley Castillo", "Yes (Native)", "Google Cloud Data Residency & Assured Workloads (cloud.google.com/assured-workloads)", "98.1% Grounded"],
                ["Q8: Serverless Container Hosting & Concurrency Auto-Scaling", "Serverless Domain Lead", "Yes (Native)", "Google Cloud Run Serverless Concurrency & GPUs (cloud.google.com/run)", "99.6% Grounded"],
                ["Q9: Multi-Cluster Orchestration & Service Mesh Governance", "GKE & IDP Leads", "Yes (Native)", "Google Kubernetes Engine (GKE) & Application Design Center (cloud.google.com/gke)", "97.4% Grounded"]
            ]
            dl_md = "download_cnap_rfi_md"
            dl_csv = "download_cnap_rfi_csv"
        else:
            rfi_rows = [
                ["Q4: Open-Source Reliance & Assurance Support", "Nate Avery", "Yes (Native)", "Google Cloud Support & OSS Assurance (cloud.google.com/support)", "98.2% Grounded"],
                ["Q6: Enterprise IAM & Authentication Integration", "Nate Avery", "Yes (Native)", "Cloud IAM, Workload Identity & Secrets Manager (cloud.google.com/iam)", "99.1% Grounded"],
                ["Q7: Customer Data Residency & Sovereign Controls", "Ashley Castillo", "Yes (Native)", "Google Cloud Data Residency & Assured Workloads (cloud.google.com/assured-workloads)", "97.5% Grounded"],
                ["Q8: CI/CD Orchestration, Linux Runners & Pipelines", "David Jacobs", "Yes (Native)", "Cloud Build & Artifact Registry Declarative CI/CD (cloud.google.com/build)", "99.4% Grounded"],
                ["Q9: AI-Augmented SDLC & Key CI/CD Differentiators", "David Jacobs & Nathen Harvey", "Yes (Native)", "Gemini Code Assist Enterprise & Antigravity IDE (cloud.google.com/gemini)", "96.8% Grounded"]
            ]
            dl_md = "download_rfi_md"
            dl_csv = "download_rfi_csv"

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=4,
                sub_processes=[
                    "✅ 4A: RFI Questionnaire Spreadsheet Upload & Intake (Complete)",
                    "🟢 4B: Automated RAG Technical Draft Generation (Active)"
                ]
            ),
            {
                "id": f"{surface_id}_status_card",
                "component": {
                    "Card": {
                        "title": "✅ RFI Multi-Tab Spreadsheet Successfully Ingested & Pre-Populated",
                        "subtitle": f"Our Principal TSA Sub-Agent scanned {total_tabs} total worksheet tabs, pre-classified {inst_tabs} instruction sheets, and decomposed {total_q} technical questions across {eval_tabs} evaluation domain tabs with {avg_conf}% average grounding confidence."
                    }
                }
            },
            {
                "id": f"{surface_id}_responses_table",
                "component": {
                    "Table": {
                        "columns": ["Q# & Requirement Capability", "Assigned SME", "Offered Natively", "Native GA Components & Proven Source", "Grounding Score"],
                        "rows": rfi_rows
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_md_btn",
                "component": {
                    "Button": {
                        "label": "📄 Download Completed RFI Responses (Markdown .MD Format)",
                        "action": {
                            "eventId": dl_md
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_csv_btn",
                "component": {
                    "Button": {
                        "label": "📊 Download Completed RFI Spreadsheet (CSV .CSV Format)",
                        "action": {
                            "eventId": dl_csv
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_proceed_btn",
                "component": {
                    "Button": {
                        "label": "⚡ Proceed to Phase 5: Deploy On-Demand Demo Environments",
                        "action": {
                            "eventId": "deploy_demo_environments"
                        }
                    }
                }
            }
        ]

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_rfi_recovery_surface(cls, recovery_data: dict[str, Any], context_data: dict[str, Any] | None = None, surface_id: str = "rfi_recovery_card") -> str:
        """
        Generates a declarative A2UI recovery card when Phase 4 multi-tab ingestion encounters unexpected input formats,
        missing criteria, or empty worksheets. Clearly presents required input formatting and one-click recovery actions.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"⚠️ Phase 4 Ingestion Recovery: Required Input Assistance — {report_name}" if report_name else "⚠️ Phase 4 Ingestion Recovery: Required Input Assistance"
        error_type = recovery_data.get("error_type", "INPUT_REQUIREMENT_DEFICIT").replace('_', ' ').title()
        recovery_msg = recovery_data.get("recovery_message", "We encountered an unexpected spreadsheet structure during Phase 4 multi-tab scanning.")
        required_inputs = recovery_data.get("required_inputs", [
            "A valid Google Sheets share link (e.g., https://docs.google.com/spreadsheets/d/...)",
            "An Excel (.xlsx) file upload containing evaluation question columns (>15 characters)",
            "Select '💡 Auto-Populate with Demo Benchmark RFI' to run against our default 2026 DevSecOps dataset."
        ])

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=4,
                sub_processes=[
                    "⚠️ 4A: RFI Questionnaire Spreadsheet Upload & Intake (Action Required)",
                    "⚪ 4B: Automated RAG Technical Draft Generation (Pending Input)"
                ]
            ),
            {
                "id": f"{surface_id}_alert_card",
                "component": {
                    "Card": {
                        "title": f"Validation Status: {error_type}",
                        "subtitle": f"{recovery_msg} Our Principal TSA Sub-Agent is standing by to assist you in getting back on track immediately."
                    }
                }
            },
            {
                "id": f"{surface_id}_req_header",
                "component": {
                    "Text": {
                        "text": {"literalString": "📋 REQUIRED INPUTS & VALIDATION RULES:"},
                        "usageHint": "h3"
                    }
                }
            }
        ]

        for idx, req_item in enumerate(required_inputs, start=1):
            components.append({
                "id": f"{surface_id}_req_{idx}",
                "component": {
                    "Text": {
                        "text": {"literalString": f" • {req_item}"},
                        "usageHint": "body"
                    }
                }
            })

        components.extend([
            {
                "id": f"{surface_id}_auto_populate_btn",
                "component": {
                    "Button": {
                        "label": "💡 Auto-Populate with Demo Benchmark RFI",
                        "action": {
                            "eventId": "auto_populate_rfi_demo"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_retry_upload_btn",
                "component": {
                    "Button": {
                        "label": "📤 Re-Open RFI Intake Form",
                        "action": {
                            "eventId": "upload_rfi"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_sample_link_btn",
                "component": {
                    "Button": {
                        "label": "📋 View Sample DevSecOps Spreadsheet Link",
                        "action": {
                            "eventId": "copy_sample_spreadsheet_link"
                        }
                    }
                }
            }
        ])

        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_demo_sandbox_surface(cls, surface_id: str = "demo_sandbox_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative demo environments card representing Phase 5: on-demand demo sandboxes,
        storyboard walkthrough freezes, recording module timecode budgeting, and demo playbook downloads.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"🎬 Phase 5: On-Demand Demo Environments & Storyboard Playbook — {report_name}" if report_name else "🎬 Phase 5: On-Demand Demo Environments & Storyboard Playbook"

        is_cnap = report_name and ("Cloud-Native" in report_name or "CNAP" in report_name or "Application Platforms" in report_name and "DevSecOps" not in report_name and "Universal" not in report_name)
        if is_cnap:
            budget_sub = "Per CNAP rules, total screencast duration is strictly capped at <= 45 minutes across 5 core areas: Major use cases, critical capabilities, differentiating features (Cloud Run & Agent Engine), product improvements, and roadmap."
            rows = [
                ["Google Cloud Run Serverless Concurrency", "serverless-sme@", "https://console.cloud.google.com/run?project=riccardo-blog-test-v1", "May 7, 2026 (Demo Freeze)"],
                ["GKE Enterprise Multi-Cluster Mesh", "gke-sme@", "https://console.cloud.google.com/kubernetes?project=riccardo-blog-test-v1", "May 7, 2026 (Demo Freeze)"],
                ["Application Design Center Golden Paths", "idp-sme@", "https://console.cloud.google.com/architecture?project=riccardo-blog-test-v1", "May 7, 2026 (Demo Freeze)"],
                ["Gemini Code Assist Enterprise Agent Engine", "devops-sme@", "https://console.cloud.google.com/gemini/agent?project=riccardo-blog-test-v1", "May 7, 2026 (Demo Freeze)"]
            ]
        else:
            budget_sub = "Each domain SME workstream is allocated a strict 10-15 minute demonstration video budget (720p+ / <= 60m overall cap). Recordings must feature explicit TOC bookmark indexing and live sandbox executions."
            rows = [
                ["CI/CD Declarative & Parallel Pipelines", "davidjacobs@", "https://console.cloud.google.com/cloud-build?project=riccardo-blog-test-v1", "T-12 Days (Sandbox Deploy)"],
                ["DORA Productivity & Agile Insights", "nathenh@", "https://console.cloud.google.com/dora?project=riccardo-blog-test-v1", "T-12 Days (Sandbox Deploy)"],
                ["SLSA Level 3 Supply Chain Attestation", "alhuizenga@", "https://console.cloud.google.com/artifacts?project=riccardo-blog-test-v1", "T-12 Days (Sandbox Deploy)"],
                ["Enterprise IAM & Workload Identity", "averyn@", "https://console.cloud.google.com/iam-admin?project=riccardo-blog-test-v1", "T-12 Days (Sandbox Deploy)"]
            ]

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=5,
                sub_processes=[
                    "✅ 5A: Target Platform Sandbox Provisioning & Verification (Complete)",
                    "🟢 5B: Storyboard Walkthrough Freeze & Playbook Budgeting (Active)",
                    "⚪ 5C: Screencast Recording Assembly & TOC Timecode Indexing (Pending)"
                ]
            ),
            {
                "id": f"{surface_id}_summary_card",
                "component": {
                    "Card": {
                        "title": "🖥️ Active Sandbox Testbeds & Curation Environments",
                        "subtitle": budget_sub
                    }
                }
            },
            {
                "id": f"{surface_id}_sandbox_table",
                "component": {
                    "Table": {
                        "columns": ["Demo Environment & Sandbox Title", "SME Lead", "Sandbox URL / Console Console Origin", "Target Freeze Milestone"],
                        "rows": rows
                    }
                }
            },
            {
                "id": f"{surface_id}_invoke_architect_btn",
                "component": {
                    "Button": {
                        "label": "🎭 Invoke Sr. OPM Demo Architect (Synthesize Scripted Dialogue & Narrative)",
                        "action": {
                            "eventId": "generate_demo_script_agent"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_playbook_btn",
                "component": {
                    "Button": {
                        "label": "📥 Download Complete Demo Script Playbook (.MD Format)",
                        "action": {
                            "eventId": "download_demo_playbook"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_proceed_btn",
                "component": {
                    "Button": {
                        "label": "⚡ Proceed to Phase 6: Manage Executive Reviews & Deficit Waivers",
                        "action": {
                            "eventId": "open_executive_review"
                        }
                    }
                }
            }
        ]
        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_demo_architect_preview_surface(cls, script_data: dict[str, Any], surface_id: str = "demo_architect_preview_card") -> str:
        """
        Generates an A2UI card showcasing the Sr. OPM/PM AI Demo Architect analysis,
        analyst expectations ("on the page" vs "not on the page"), and sample scripted dialogues.
        """
        mod_rows = [
            [f"Module {m['module_number']}: {m['title']}", m["sme_lead"], m["timecode"], str(m["scripted_actions"][0]) if m.get("scripted_actions") else ""]
            for m in script_data.get("scripted_modules", [])
        ]
        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": f"🎭 Sr. OPM / PM Demo Script Architect Analysis — {script_data.get('report_scope', '')}"},
                        "usageHint": "h2"
                    }
                }
            },
            {
                "id": f"{surface_id}_exec_summary_card",
                "component": {
                    "Card": {
                        "title": "🏆 Executive Summary: Current GA Compliance vs. Future Visionary Roadmap",
                        "subtitle": f"Current GA Strategy: {script_data['executive_summary']['current_ga_capabilities']} | Future Roadmap Plan: {script_data['executive_summary']['future_capabilities_plan']} | Terraform Setup: {script_data['executive_summary']['terraform_infrastructure_instructions']}"
                    }
                }
            },
            {
                "id": f"{surface_id}_analyst_psychology_card",
                "component": {
                    "Card": {
                        "title": "🧠 Analyst Expectation Intelligence (Gartner, Forrester & IDC)",
                        "subtitle": f"What is ON THE PAGE: {script_data['analyst_expectations']['on_the_page']} | What is NOT ON THE PAGE (Implicit Expectations): {script_data['analyst_expectations']['not_on_the_page']}"
                    }
                }
            },
            {
                "id": f"{surface_id}_modules_table",
                "component": {
                    "Table": {
                        "columns": ["Demo Chapter / Module Title", "Assigned Lead", "Timecode Allocation", "Primary Scripted UI Action"],
                        "rows": mod_rows
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_btn",
                "component": {
                    "Button": {
                        "label": "📥 Download Complete Scripted Playbook with Word-for-Word Dialogues (.MD)",
                        "action": {
                            "eventId": "download_demo_playbook"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_proceed_btn",
                "component": {
                    "Button": {
                        "label": "⚡ Proceed to Phase 6: Manage Executive Reviews & Deficit Waivers",
                        "action": {
                            "eventId": "open_executive_review"
                        }
                    }
                }
            }
        ]
        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_executive_review_surface(cls, surface_id: str = "executive_review_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative review card representing Phase 6: executive review panel approval,
        legal & commercial pricing verification, and preview cutoff attestation deficit waivers.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"🛡️ Phase 6: Executive Review Panel & GA Deficit Attestation Waivers — {report_name}" if report_name else "🛡️ Phase 6: Executive Review Panel & GA Deficit Attestation Waivers"

        is_cnap = report_name and ("Cloud-Native" in report_name or "CNAP" in report_name or "Application Platforms" in report_name and "DevSecOps" not in report_name and "Universal" not in report_name)
        if is_cnap:
            target_date = "May 14, 2026 (VP/GM Review)"
            rows = [
                ["Commercial & Legal Pricing Validation", "Legal & OPM Leads", "Pricing sheet accuracy & licensing terms verification", "Approved / Verified"],
                ["VP/GM Demonstration & Survey Sign-Off", "VP/GM Executive Review Panel", "Final evaluation quality review before portal lock", "Ready for Review (May 14)"],
                ["Preview Feature Cutoff Waiver Request", "Analyst Relations (AR)", "Request attestation waiver for offerings within early GA / preview windows", "Waiver Documented"]
            ]
        else:
            target_date = "T-5 Days (Executive Approval Panel Review)"
            rows = [
                ["Commercial & Legal Pricing Validation", "Legal & OPM Leads", "Pricing sheet accuracy & licensing terms verification", "Approved / Verified"],
                ["Consolidated Executive Review Sign-Off", "Executive Approval Panel", "Final check of technical RFI responses and demo video TOC timecodes", f"Ready for Review ({target_date})"],
                ["Gemini Agent Mode Cutoff Waiver Request", "Analyst Relations (AR)", "Request attestation waiver for preview features with post-cutoff GA dates", "Waiver Documented"]
            ]

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=6,
                sub_processes=[
                    "✅ 6A: Commercial Pricing Sheets & Legal Licensing Validation (Complete)",
                    f"🟢 6B: VP/GM Executive Review Panel & Attestation Deficit Waivers (Active - {target_date})"
                ]
            ),
            {
                "id": f"{surface_id}_summary_card",
                "component": {
                    "Card": {
                        "title": "📑 Executive Governance & Risk Remediation Checklist",
                        "subtitle": "All evaluation responses, demo timecodes, and commercial pricing sheets are subjected to rigorous executive verification before portal submission."
                    }
                }
            },
            {
                "id": f"{surface_id}_review_table",
                "component": {
                    "Table": {
                        "columns": ["Governance Milestone & Checkpoint", "Lead Authority", "Verification Scope", "Current Status"],
                        "rows": rows
                    }
                }
            },
            {
                "id": f"{surface_id}_invoke_agent_btn",
                "component": {
                    "Button": {
                        "label": "🛡️ Invoke VP/GM Governance Sub-Agent (Run Comprehensive Compliance Audit & Waiver Analysis)",
                        "action": {
                            "eventId": "generate_executive_review_agent"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_memo_btn",
                "component": {
                    "Button": {
                        "label": "📥 Download Executive Approval Dossier & Waiver Memo (.MD Format)",
                        "action": {
                            "eventId": "download_executive_memo"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_proceed_btn",
                "component": {
                    "Button": {
                        "label": "🚀 Proceed to Phase 7: Portal Upload & Leadership Recognitions",
                        "action": {
                            "eventId": "open_publication_recognition"
                        }
                    }
                }
            }
        ]
        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_executive_review_preview_surface(cls, review_data: dict[str, Any], surface_id: str = "exec_review_preview_card") -> str:
        """
        Generates an A2UI card showcasing the VP/GM Executive Governance Sub-Agent compliance audit,
        risk assessment matrix, and formal deficit attestation waiver strategy.
        """
        matrix_rows = [
            [r.get("checkpoint", ""), r.get("authority", ""), r.get("scope_and_finding", ""), r.get("outcome", "VERIFIED & APPROVED")]
            for r in review_data.get("risk_assessment_matrix", [])
        ]
        verdict = review_data.get("panel_verdict", {})
        waiver = review_data.get("deficit_waiver_dossier", {})
        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": f"🛡️ VP/GM Executive Governance Sub-Agent Audit — {review_data.get('report_scope', '')}"},
                        "usageHint": "h2"
                    }
                }
            },
            {
                "id": f"{surface_id}_verdict_card",
                "component": {
                    "Card": {
                        "title": f"🏆 Executive Panel Verdict: {verdict.get('status', 'APPROVED BY EXECUTIVE REVIEW PANEL')}",
                        "subtitle": f"Compliance Ceiling: {verdict.get('compliance_score', '')} | Summary: {verdict.get('summary', '')}"
                    }
                }
            },
            {
                "id": f"{surface_id}_waiver_card",
                "component": {
                    "Card": {
                        "title": f"📑 Deficit Attestation Waiver & Roadmap Bridge: {waiver.get('target_offering', '')}",
                        "subtitle": f"Cutoff Status: {waiver.get('ga_cutoff_status', '')} | Remediation Strategy: {waiver.get('remediation_strategy', '')} | Executive Sign-off: {waiver.get('executive_signoff', '')}"
                    }
                }
            },
            {
                "id": f"{surface_id}_matrix_table",
                "component": {
                    "Table": {
                        "columns": ["Governance Checkpoint", "Lead Authority", "Scope & Finding", "Outcome & Rating"],
                        "rows": matrix_rows
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_btn",
                "component": {
                    "Button": {
                        "label": "📥 Download Complete Executive Approval Dossier & Waiver Memo (.MD)",
                        "action": {
                            "eventId": "download_executive_memo"
                        }
                    }
                }
            },
            {
                "id": f"{surface_id}_proceed_btn",
                "component": {
                    "Button": {
                        "label": "🚀 Proceed to Phase 7: Portal Upload & Leadership Recognitions",
                        "action": {
                            "eventId": "open_publication_recognition"
                        }
                    }
                }
            }
        ]
        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

    @classmethod
    def generate_publication_recognition_surface(cls, surface_id: str = "publication_recognition_card", context_data: dict[str, Any] | None = None) -> str:
        """
        Generates an A2UI declarative completion card representing Phase 7: final portal master submission,
        external publication strategy, and contributor recognition manifesto across enterprise channels.
        """
        report_name = cls.resolve_analyst_report_name(context_data)
        title_str = f"🏆 Phase 7: Master Portal Publication & Contributor Recognition Manifesto — {report_name}" if report_name else "🏆 Phase 7: Master Portal Publication & Contributor Recognition Manifesto"

        is_cnap = report_name and ("Cloud-Native" in report_name or "CNAP" in report_name or "Application Platforms" in report_name and "DevSecOps" not in report_name and "Universal" not in report_name)
        if is_cnap:
            portal_deadline = "May 18, 2026 (RFI Lock & Portal Submission Due)"
            sme_list = [
                "Serverless Domain Lead (serverless-sme@) — Cloud Run auto-scaling & concurrency",
                "GKE Enterprise Lead (gke-sme@) — Multi-cluster mesh & Autopilot capabilities",
                "Platform Engineering Lead (idp-sme@) — Application Design Center golden paths",
                "David Jacobs (devops-sme@) — CI/CD declarative pipelines",
                "Nate Avery (averyn@) & Ashley Castillo (acastillo@) — IAM & Sovereign Data Residency",
                "Mukul Saha MQ Leads Team (@gosiagnyp, @pattyr, @steren, @vikasan, @lisashen, @kevinflores, @meganbruce, @gbrosman, @ragim)"
            ]
        else:
            portal_deadline = "Target Deadline (03/10/2026)"
            sme_list = [
                "David Jacobs (davidjacobs@) — CI/CD Orchestration & Parallel Pipelines",
                "Nathen Harvey (nathenh@) — DORA Productivity & Agile Planning",
                "Al Huizenga (alhuizenga@) — SLSA Level 3 Supply Chain Attestation",
                "Rishi Mukhopadhyay (rishim@) — Secure Source Code Repositories & Vulnerability Scanners",
                "Rami Shalom & Knox Anderson — Observability & Runtime Threat Detection",
                "Nate Avery (averyn@) & Ashley Castillo (acastillo@) — Enterprise IAM & Data Residency"
            ]

        submission_rows = [
            ["Completed RFI Questionnaire Spreadsheet", "Analyst Response Agent (ARA)", "Full RAG technical responses & citations (.CSV & .MD)", "Ready for Portal Upload"],
            ["Timecoded Demo Table of Contents (TOC)", "OPM & PM Leadership", "Exact [mm:ss] bookmark indices across demonstrated criteria", "Ready for Portal Upload"],
            ["Master Screencast Demonstration Files", "Domain SME Leads", "High-contrast 720p+ .mp4 recordings verified against duration budget", "Ready for Portal Upload"]
        ]

        components: list[dict[str, Any]] = [
            {
                "id": f"{surface_id}_title",
                "component": {
                    "Text": {
                        "text": {"literalString": title_str},
                        "usageHint": "h2"
                    }
                }
            },
            *cls.build_lifecycle_progress_tracker(
                surface_id,
                phase_num=7,
                sub_processes=[
                    f"✅ 7A: Master Portal Package Verification (Complete - Target Lock: {portal_deadline})",
                    "🟢 7B: Contributor Recognition & Leadership Showcase (Active Across Executive Channels)"
                ]
            ),
            {
                "id": f"{surface_id}_badge_card",
                "component": {
                    "Card": {
                        "title": "✅ Conductor v2 7-Phase Operational Lifecycle 100% Complete!",
                        "subtitle": f"All criteria analyses, schedule timelines, workstream routing, RFI pre-population, demo sandboxes, and executive approvals have been verified for [{report_name or 'Universal Analyst Evaluation'}]."
                    }
                }
            },
            {
                "id": f"{surface_id}_submission_table",
                "component": {
                    "Table": {
                        "columns": ["Master Portal Package Item", "Lead Owner", "Deliverable Description", "Submission Readiness"],
                        "rows": submission_rows
                    }
                }
            },
            {
                "id": f"{surface_id}_recognition_box",
                "component": {
                    "SectionBox": {
                        "header": "🌟 Executive Contributor Recognition & Leadership Showcase",
                        "items": sme_list
                    }
                }
            },
            {
                "id": f"{surface_id}_dl_bundle_btn",
                "component": {
                    "Button": {
                        "label": "📥 Download Final Portal Package & Recognition Bundle (.MD Format)",
                        "action": {
                            "eventId": "download_publication_bundle"
                        }
                    }
                }
            }
        ]
        surface_payload = {
            "version": "v0.9",
            "surfaceId": surface_id,
            "components": components
        }
        return cls.wrap_in_a2ui_tags(surface_payload)

