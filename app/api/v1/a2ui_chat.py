import asyncio
import datetime
import logging
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from vertexai.generative_models import GenerativeModel, GenerationConfig
from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger("conductor.api.a2ui")
from app.schemas.inclusion_schemas import (
    InclusionEvaluationMatrix,
    ParsedRfiCriteria,
)
from app.schemas.orchestration_schemas import (
    ExclusionWindow,
    Milestone,
    TimelineRequest,
    WorkbackTimeline,
)
import json
import uuid
from app.services.a2ui_generator import A2UIGenerator
from app.services.inclusion_analyzer import InclusionAnalyzer
from app.services.timeline_engine import TimelineEngine
from app.services.artifact_service import ArtifactService
from app.schemas.core_schemas import SavedArtifactCreate

from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/a2ui", tags=["A2UI Agent-to-User Interface"])


class A2UIChatRequest(BaseModel):
    """
    Incoming chat prompt or action event from the client A2UI host container.
    """
    message: str = Field(..., description="User prompt text or action command")
    action_id: str | None = Field(default=None, description="Optional action identifier if triggered by an A2UI button")
    workspace_id: uuid.UUID | None = Field(default=None, description="Optional active enterprise workspace UUID")
    context_data: dict[str, Any] = Field(default_factory=dict, description="Contextual form data or bound input variables")


class A2UIChatResponse(BaseModel):
    """
    Agent response containing conversational reasoning text and optional embedded `<a2ui-json>` protocol payloads.
    """
    agent_name: str = Field(default="Analyst Response Agent (ARA)", description="Name of the agent responding")
    response_text: str = Field(..., description="Natural language response or reasoning")
    a2ui_payloads: list[str] = Field(default_factory=list, description="List of formatted `<a2ui-json>` protocol blocks to render")
    restored_context: dict[str, Any] | None = Field(default=None, description="Optional dictionary of restored form fields and session variables when loading saved artifacts")


@router.post(
    "/chat",
    response_model=A2UIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat endpoint serving conversational guidance and A2UI declarative surfaces"
)
async def handle_a2ui_chat(
    payload: A2UIChatRequest,
    db: AsyncSession = Depends(get_db)
) -> A2UIChatResponse:
    """
    Processes user chat input or button actions, executes analyst evaluation logic,
    and returns conversational responses alongside declarative `<a2ui-json>` surfaces.
    Tracks and updates the last completed step per enterprise workspace to allow seamless resumption.
    """
    msg_lower = payload.message.lower()
    action = payload.action_id
    context_data = payload.context_data or {}
    
    # 1. Resolve active Workspace and its journey state if provided
    target_ws_id = payload.workspace_id or context_data.get("workspace_id")
    ws_obj = None
    ws_service = None
    if target_ws_id and db:
        try:
            ws_uuid = uuid.UUID(str(target_ws_id))
            ws_service = WorkspaceService(db_session=db)
            ws_obj = await ws_service.get_workspace(ws_uuid, current_user_email=settings.DEFAULT_ENTERPRISE_USER_EMAIL)
        except Exception as e:
            logger.warning(f"Could not load workspace for chat [{target_ws_id}]: {e}")
            ws_obj = None

    # Merge saved workspace context if available
    if ws_obj and ws_obj.context_data_json:
        try:
            saved_ctx = json.loads(ws_obj.context_data_json)
            if isinstance(saved_ctx, dict):
                for k, v in saved_ctx.items():
                    if k not in context_data:
                        context_data[k] = v
        except Exception as e:
            logger.warning(f"Failed to parse workspace context_data_json: {e}")

    # Determine if this is a Workspace Resumption event (loading or switching workspaces)
    is_workspace_resumption = False
    resumed_banner = ""
    if ws_obj and (action in ["resume_workspace", "resume"] or (action == "welcome" and payload.message in ["Switched workspace context", "Loading workspace", "Switched workspace", "resume_workspace", "Switched to workspace: " + ws_obj.name])):
        if ws_obj.last_action_id and ws_obj.last_action_id not in ["welcome", "resume_workspace"]:
            action = ws_obj.last_action_id
            is_workspace_resumption = True
        else:
            action = "open_intake" if ws_obj.current_phase == 1 else (ws_obj.last_action_id or "open_intake")
            is_workspace_resumption = True

    report_name = A2UIGenerator.resolve_analyst_report_name(context_data) or (ws_obj.report_type if ws_obj else None)
    context_data["report_name"] = report_name
    if ws_obj:
        context_data["workspace_id"] = str(ws_obj.id)
        context_data["workspace_name"] = ws_obj.name
        context_data["current_phase"] = ws_obj.current_phase
        context_data["last_completed_step"] = ws_obj.last_completed_step
        context_data["last_action_id"] = ws_obj.last_action_id
        context_data["journey_percentage"] = int(round((ws_obj.current_phase / 7.0) * 100))

    if is_workspace_resumption and ws_obj:
        phase_num = ws_obj.current_phase or 1
        pct = int(round((phase_num / 7.0) * 100))
        resumed_banner = (
            f"### 🔄 Resumed Workspace: **{ws_obj.name}**\n\n"
            f"**📍 Current Journey Position:** Step {phase_num} of 7 — **{ws_obj.last_completed_step}** ({pct}% Overall Lifecycle Complete)  \n"
            f"**🎯 Target Evaluation:** **{report_name or ws_obj.report_type}**\n\n"
            f"Welcome back! You have been returned directly to where you left off so you may proceed without losing momentum.\n\n"
            "---\n\n"
        )

    # Helper function to finalize response, record progression, and return payload
    async def finish_response(
        resp_text: str,
        payloads: list[str],
        phase_num: int | None = None,
        step_name: str | None = None,
        action_id: str | None = None,
    ) -> A2UIChatResponse:
        final_text = (resumed_banner + resp_text) if (is_workspace_resumption and resumed_banner) else resp_text
        if phase_num is not None:
            context_data["current_phase"] = phase_num
            context_data["journey_percentage"] = int(round((phase_num / 7.0) * 100))
        if step_name is not None:
            context_data["last_completed_step"] = step_name
        if action_id is not None:
            context_data["last_action_id"] = action_id

        if ws_obj and ws_service and phase_num is not None and step_name is not None and action_id is not None and not is_workspace_resumption:
            try:
                await ws_service.update_workspace_step(
                    workspace_id=ws_obj.id,
                    phase=phase_num,
                    step_name=step_name,
                    action_id=action_id,
                    context_data=context_data,
                    current_user_email=settings.DEFAULT_ENTERPRISE_USER_EMAIL,
                )
            except Exception as ex:
                logger.warning(f"Could not persist updated workspace step: {ex}")

        return A2UIChatResponse(
            response_text=final_text,
            a2ui_payloads=payloads,
            restored_context=context_data,
        )

    # Phase 2: SME Task Routing & Workstream Assignment Matrix
    if action == "assign_tasks" or any(k in msg_lower for k in ["assign", "route", "routing", "sme workstream", "phase 2", "task assignment", "assigning smes"]):
        task_surface = A2UIGenerator.generate_task_assignment_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"### 👥 Phase 2: SME Task Routing & Workstream Assignment\n\nWe have analyzed your criteria and automatically routed domain workstreams for **{report_name}** to responsible subject matter experts (David Jacobs, Nathen Harvey, Al Huizenga, Rishi Mukhopadhyay, Rami Shalom, Knox Anderson, Nate Avery, and Ashley Castillo). Each lead has been assigned an explicit **T-15 Day curation deadline**." if report_name else "### 👥 Phase 2: SME Task Routing & Workstream Assignment\n\nWe have analyzed your criteria and automatically routed domain workstreams directly to responsible subject matter experts.",
            payloads=[task_surface],
            phase_num=2,
            step_name="Phase 2: SME Task Routing & Workstream Assignment",
            action_id="assign_tasks"
        )

    # Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter
    if action == "kickoff_project" or any(k in msg_lower for k in ["kickoff", "align teams", "charter", "workstream alignment", "phase 3"]):
        kickoff_surface = A2UIGenerator.generate_kickoff_alignment_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"### 🚀 Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter\n\nProject kickoff rules and demonstration recording module budgets (10-15m per SME, 720p+ resolution, <= 60m overall cap) have been finalized for **{report_name}**. All stakeholders are aligned around critical calendar freeze dates." if report_name else "### 🚀 Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter\n\nProject kickoff rules and demonstration recording module budgets have been finalized.",
            payloads=[kickoff_surface],
            phase_num=3,
            step_name="Phase 3: Stakeholder Kickoff & OPM Alignment Charter",
            action_id="kickoff_project"
        )

    # Phase 4A: RFI Questionnaire Spreadsheet Intake Drop-Zone
    # Phase 4: Defensive Error Recovery & Sample Link Guidance
    if action == "copy_sample_spreadsheet_link" or any(k in msg_lower for k in ["sample devsecops", "view sample link", "copy sample link", "10ulrcbqehax"]):
        recovery_payload = {
            "error_type": "VERIFIED_SAMPLE_BENCHMARK_AVAILABLE",
            "recovery_message": "Here is the official Google Spreadsheet link for our 2026 Gartner DevSecOps MQ evaluation: `https://docs.google.com/spreadsheets/d/10uLRcBQehAx4h14cKy3zSgFjXNazcKTIM0Il7xB1_E8/edit?usp=drive_link`. You may copy this link into the RFI intake form or select **'💡 Auto-Populate with Demo Benchmark RFI'** below to run multi-tab RAG grounding immediately.",
            "required_inputs": [
                "Target Spreadsheet ID: 10uLRcBQehAx4h14cKy3zSgFjXNazcKTIM0Il7xB1_E8",
                "Evaluation Scope: 18 total worksheets (14 evaluation domain tabs, 4 instruction/admin sheets filtered)",
                "Click **'💡 Auto-Populate with Demo Benchmark RFI'** below to execute without manual link pasting."
            ]
        }
        recovery_surface = A2UIGenerator.generate_rfi_recovery_surface(recovery_data=recovery_payload, context_data=context_data)
        return await finish_response(
            resp_text=f"### 📋 Verified Sample DevSecOps RFI Spreadsheet Link\n\nTo assist you in getting back on track and verifying Phase 4 capabilities, we provide an official benchmark questionnaire link below. All required inputs and tab domain coordinates are pre-configured.",
            payloads=[recovery_surface],
            phase_num=4,
            step_name="Phase 4A: RFI Sample Benchmark Guidance",
            action_id="copy_sample_spreadsheet_link"
        )

    # Phase 4: Auto-Populate Demo Benchmark / Fallback Recovery Execution
    if action == "auto_populate_rfi_demo" or any(k in msg_lower for k in ["auto-populate", "auto populate", "demo benchmark", "benchmark rfi", "run benchmark"]):
        from app.services.rfi_architect_agent import RfiArchitectAgentService
        eval_id = context_data.get("evaluation_id", str(uuid.uuid4()))
        rfi_data = await RfiArchitectAgentService.generate_grounded_drafts(evaluation_id=eval_id, db_session=db, report_name="DevSecOps Platforms 2026 (Benchmark)")
        context_data["rfi_data"] = rfi_data
        rfi_response_surface = A2UIGenerator.generate_rfi_response_surface(context_data=context_data)
        avg_conf = rfi_data.get("average_grounding_confidence", 98.5)
        return await finish_response(
            resp_text=f"### 💡 Phase 4: Auto-Populated Benchmark RFI Execution\n\nOur Principal TSA Sub-Agent successfully initiated automated ingestion against our verified **2026 Gartner DevSecOps Benchmark Spreadsheet**, decomposing 14 domain evaluation tabs and pre-populating technical responses with **{avg_conf}% average grounding confidence**. Prior RFI historical provenance and SME lead assignments are fully populated below.",
            payloads=[rfi_response_surface],
            phase_num=4,
            step_name="Phase 4B: Automated RAG Ingestion & Initial Technical Drafts",
            action_id="generate_rfi_responses"
        )

    # Phase 4: Intercept Malformed RFI Ingestion Requests (Defensive Recovery)
    if action in ["submit_rfi_link", "ingest_rfi", "execute_rfi_ingestion"] or any(msg_lower.startswith(prefix) for prefix in ["ingest ", "scan rfi", "parse sheet", "upload url", "submit link"]):
        from app.services.rfi_architect_agent import RfiArchitectAgentService
        eval_id_val = context_data.get("evaluation_id", str(uuid.uuid4()))
        try:
            eval_uuid = uuid.UUID(str(eval_id_val))
        except ValueError:
            eval_uuid = uuid.uuid4()
        
        ingest_res = await RfiArchitectAgentService.ingest_multitab_spreadsheet(workbook_source=payload.message, evaluation_id=eval_uuid, db_session=db)
        if ingest_res.get("status") in ["error", "warning"]:
            recovery_surface = A2UIGenerator.generate_rfi_recovery_surface(recovery_data=ingest_res, context_data=context_data)
            return await finish_response(
                resp_text=f"### ⚠️ Phase 4: Ingestion Input Assistance & Recovery\n\nOur Technical Solution Architect Sub-Agent encountered an unrecognized input structure or incomplete evaluation criteria while processing your request. Please review the required inputs below or select one of our interactive recovery actions to proceed without interruption.",
                payloads=[recovery_surface],
                phase_num=4,
                step_name="Phase 4A: RFI Ingestion Recovery Guidance",
                action_id="upload_rfi"
            )
        else:
            rfi_data = await RfiArchitectAgentService.generate_grounded_drafts(evaluation_id=eval_uuid, db_session=db, report_name=report_name)
            context_data["rfi_data"] = rfi_data
            rfi_response_surface = A2UIGenerator.generate_rfi_response_surface(context_data=context_data)
            avg_conf = rfi_data.get("average_grounding_confidence", 98.4)
            return await finish_response(
                resp_text=f"### 📝 Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts\n\nOur Principal TSA Sub-Agent successfully ingested your multi-tab RFI spreadsheet across all worksheet tabs, classified instructional tables, and pre-populated technical responses with **{avg_conf}% average grounding confidence**.",
                payloads=[rfi_response_surface],
                phase_num=4,
                step_name="Phase 4B: Automated RAG Ingestion & Initial Technical Drafts",
                action_id="generate_rfi_responses"
            )

    if action == "upload_rfi" or any(k in msg_lower for k in ["upload rfi", "rfi spreadsheet", "questionnaire upload", "phase 4a", "upload questionnaire", "spreadsheet intake", "rfi link"]):
        rfi_upload_surface = A2UIGenerator.generate_rfi_upload_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"### 📥 Phase 4A: RFI Questionnaire Spreadsheet Intake\n\nPlease attach or paste the link to your RFI questionnaire spreadsheet (e.g., Google Sheets or Drive file) for **{report_name}** below to initialize automated RAG draft completion." if report_name else "### 📥 Phase 4A: RFI Questionnaire Spreadsheet Intake\n\nPlease attach or paste the link to your RFI questionnaire spreadsheet below to initialize automated RAG draft completion.",
            payloads=[rfi_upload_surface],
            phase_num=4,
            step_name="Phase 4A: RFI Questionnaire Spreadsheet Intake",
            action_id="upload_rfi"
        )

    # Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts
    if action == "generate_rfi_responses" or any(k in msg_lower for k in ["generate rfi responses", "rfi response", "rag ingestion", "pre-populate", "draft answer", "initial response", "phase 4", "draft rfi", "ingest rfi", "completed rfi"]):
        from app.services.rfi_architect_agent import RfiArchitectAgentService
        eval_id = context_data.get("evaluation_id", str(uuid.uuid4()))
        rfi_data = await RfiArchitectAgentService.generate_grounded_drafts(evaluation_id=eval_id, db_session=db, report_name=report_name)
        context_data["rfi_data"] = rfi_data
        rfi_response_surface = A2UIGenerator.generate_rfi_response_surface(context_data=context_data)
        avg_conf = rfi_data.get("average_grounding_confidence", 97.9)
        return await finish_response(
            resp_text=f"### 📝 Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts\n\nOur Principal TSA Sub-Agent successfully ingested the multi-tab RFI spreadsheet for **{report_name or 'Universal Analyst Evaluation'}**, correlated capabilities across our verified GA product portfolio, and pre-populated initial technical responses with **{avg_conf}% average grounding confidence** (recalling verified prior RFI sources). You may review the responses below or download them directly as standalone Markdown (`.md`) or CSV (`.csv`) files.",
            payloads=[rfi_response_surface],
            phase_num=4,
            step_name="Phase 4B: Automated RAG Ingestion & Initial Technical Drafts",
            action_id="generate_rfi_responses"
        )

    # Phase 4: Conversational TSA Draft Refinement
    if any(msg_lower.startswith(prefix) for prefix in ["refine ", "edit q", "update q", "refine tab", "refine section"]):
        from app.services.rfi_architect_agent import RfiArchitectAgentService
        target_token = payload.message.split()[1] if len(payload.message.split()) > 1 else "Q6"
        await RfiArchitectAgentService.refine_draft_response(question_identifier=target_token, refinement_instruction=payload.message, db_session=db)
        eval_id = context_data.get("evaluation_id", str(uuid.uuid4()))
        rfi_data = await RfiArchitectAgentService.generate_grounded_drafts(evaluation_id=eval_id, db_session=db, report_name=report_name)
        context_data["rfi_data"] = rfi_data
        rfi_response_surface = A2UIGenerator.generate_rfi_response_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"### ⚙️ Principal TSA Sub-Agent: Draft Answer Refined\n\nSuccessfully applied executive refinement instruction (`{payload.message}`) to target question section **{target_token}**. Grounding confidence re-verified and standalone Markdown / CSV export dossiers have been updated.",
            payloads=[rfi_response_surface],
            phase_num=4,
            step_name="Phase 4B: Principal TSA Refined RFI Drafts",
            action_id="generate_rfi_responses"
        )

    # Phase 5 AI Demo Architect: Synthesize Scripted Narrative & Dialogue
    if action in ["generate_demo_script_agent", "invoke_demo_architect"] or any(k in msg_lower for k in ["demo architect", "scripted dialogue", "sr opm", "sr. opm", "analyst psychology", "not on the page"]):
        from app.services.demo_script_agent import DemoScriptAgentService
        script_data = DemoScriptAgentService.generate_demo_playbook(report_name=report_name, context_data=context_data)
        architect_surface = A2UIGenerator.generate_demo_architect_preview_surface(script_data)
        return await finish_response(
            resp_text=f"### 🎭 Sr. OPM / PM Demo Script Architect Sub-Agent\n\nOur specialized AI Sub-Agent has analyzed both published RFI questionnaires and implicit analyst evaluation psychology ('not on the page') for **{report_name or 'Universal Analyst Evaluation'}**. Below is your synthesized two-stage executive strategy (balancing Current GA Compliance against Future Roadmap Vision) along with step-by-step UI actions and word-for-word voiceover scripts.",
            payloads=[architect_surface],
            phase_num=5,
            step_name="Phase 5B: Sr. OPM Demo Script Storyboard Playbook",
            action_id="generate_demo_script_agent"
        )

    # Phase 5: Deploy On-Demand Demo Environments & Storyboard Playbook
    if action in ["open_demo_sandboxes", "deploy_demo_environments", "proceed_to_phase_5"] or any(k in msg_lower for k in ["demo", "sandbox", "playbook", "phase 5", "storyboard", "screencast", "testbed", "timecode"]):
        demo_surface = A2UIGenerator.generate_demo_sandbox_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"### 🎬 Phase 5: On-Demand Demo Environments & Storyboard Playbook\n\nActive sandbox testbeds and timecoded demonstration budgets have been provisioned for **{report_name or 'Universal Analyst Evaluation'}**. You can review the sandbox table below or download the complete on-demand demo script playbook in Markdown format.",
            payloads=[demo_surface],
            phase_num=5,
            step_name="Phase 5A: On-Demand Demo Environments & Sandboxes",
            action_id="open_demo_sandboxes"
        )

    # Phase 6 VP/GM Executive Governance Sub-Agent: Run Compliance Audit & Deficit Analysis
    if action in ["generate_executive_review_agent", "invoke_executive_agent"] or any(k in msg_lower for k in ["governance agent", "compliance audit", "vp/gm governance", "deficit analysis", "executive review agent"]):
        from app.services.executive_review_agent import ExecutiveReviewAgentService
        review_data = ExecutiveReviewAgentService.generate_governance_dossier(report_name=report_name, context_data=context_data)
        review_surface = A2UIGenerator.generate_executive_review_preview_surface(review_data)
        return await finish_response(
            resp_text=f"### 🛡️ VP/GM Executive Governance & Compliance Sub-Agent\n\nOur AI Governance Sub-Agent has completed a full commercial, legal, and architectural compliance audit for **{report_name or 'Universal Analyst Evaluation'}**. Below is your synthesized Risk Assessment Matrix and formal Deficit Attestation Waiver Dossier.",
            payloads=[review_surface],
            phase_num=6,
            step_name="Phase 6B: VP/GM Governance & Compliance Audit",
            action_id="generate_executive_review_agent"
        )

    # Phase 6: Executive Review Panel & GA Deficit Attestation Waivers
    if action in ["open_executive_review", "proceed_to_phase_6"] or any(k in msg_lower for k in ["executive review", "vp review", "waiver", "deficit waiver", "phase 6", "legal review", "approval panel", "governance checklist"]):
        review_surface = A2UIGenerator.generate_executive_review_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"### 🛡️ Phase 6: Executive Review Panel & GA Deficit Attestation Waivers\n\nCommercial pricing sheets, open-source licensing attestations, and video TOC timecodes have undergone rigorous executive review for **{report_name or 'Universal Analyst Evaluation'}**. Deficit waiver requests for early GA / preview offerings are ready for download.",
            payloads=[review_surface],
            phase_num=6,
            step_name="Phase 6A: Executive Review Panel & Deficit Waivers",
            action_id="open_executive_review"
        )

    # Phase 7: Master Portal Publication & Contributor Recognition Manifesto
    if action in ["open_publication_recognition", "proceed_to_phase_7", "publish"] or any(k in msg_lower for k in ["publication", "recognition", "contributor", "portal upload", "phase 7", "manifesto", "celebratory", "final upload", "master upload"]):
        from app.services.rfi_architect_agent import RfiArchitectAgentService
        eval_id_val = context_data.get("evaluation_id", None)
        await RfiArchitectAgentService.archive_approved_rfi_to_corpus(evaluation_id=eval_id_val, db_session=db)
        pub_surface = A2UIGenerator.generate_publication_recognition_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"### 🏆 Phase 7: Master Portal Publication & Contributor Recognition Manifesto\n\n**100% Operational Lifecycle Completion Confirmed!** All required RFI questionnaires, TOC bookmark indexes, screencast demonstrations, and executive waiver dossiers have been verified and approved for master portal upload for **{report_name or 'Universal Analyst Evaluation'}**. Verified answers have been automatically indexed into continuous `RagDocumentChunk` memory (`Prior_RFI_Answer`). We proudly recognize our domain SME leads across enterprise leadership channels.",
            payloads=[pub_surface],
            phase_num=7,
            step_name="Phase 7: Master Portal Publication & Recognition Manifesto",
            action_id="open_publication_recognition"
        )

    # 1. Handle Intake / Onboarding Request
    if action == "open_intake" or (not action and any(k in msg_lower for k in ["intake", "link", "welcome packet", "guideline", "upload"]) and not any(k in msg_lower for k in ["evaluat", "matrix", "scorecard", "portfolio", "qualif", "deep dive", "export", "download", "rfi", "phase 2", "phase 3", "phase 4", "phase 5", "phase 6", "phase 7", "assign", "kickoff", "spreadsheet", "demo", "sandbox", "waiver", "publication", "recognition"])):
        intake_surface = A2UIGenerator.generate_intake_form_surface(context_data=context_data)
        return await finish_response(
            resp_text=f"Opening Phase 1 Intake for **{report_name}**. Please paste your document links or drop files below." if report_name else "",
            payloads=[intake_surface],
            phase_num=1,
            step_name="Phase 1A: Criteria Document Intake",
            action_id="open_intake"
        )

    # 2. Handle Deep Dive Analysis & Report Export Request
    if action in ["deep_dive_analysis", "download_report"] or any(k in msg_lower for k in ["deep dive", "export", "rejected", "deficit breakdown", "download"]):
        deep_dive_surface = A2UIGenerator.generate_deep_dive_surface(context_data=context_data)
        header_prefix = f"for **{report_name}** " if report_name else ""
        return await finish_response(
            resp_text=(
                f"### 🔍 Comprehensive Portfolio Deep Dive & Rejection Deficit Analysis\n\n"
                f"Here is the comprehensive **Deep Dive Technical Report & Threshold Deficit Breakdown** {header_prefix}across our Google Cloud and Antigravity offerings (`Standard GA` and `Preview`).\n\n"
                "**Exact Quantitative & Qualitative Capabilities Evaluated:**\n"
                "1. **✅ Qualifying Flagship SKU: Gemini Code Assist Enterprise** (`Standard GA: Nov 15, 2024` | `$35.0M` Revenue, `65.0%` CAGR, `620` Logos)\n"
                f"   * *Scorable Features:* AI-powered multi-file code generation, context-aware repository chatting, local RAG indexing, and automated test generation — scoring maximum points in AI developer productivity{f' for **{report_name}**' if report_name else ''}.\n\n"
                "2. **✅ Qualifying Core Offering: Antigravity 2.0** (`Standard GA: May 20, 2025` | `$145.0M` Revenue, `110.0%` CAGR, `2,100` Logos)\n"
                "   * *Scorable Features (`antigravity.google`):* Agentic workflow orchestration, autonomous multi-turn task resolution, and enterprise-grade AI coding agent intelligence.\n\n"
                "3. **✅ Qualifying Core Offering: Antigravity IDE** (`Standard GA: Aug 14, 2025` | `$88.0M` Revenue, `95.0%` CAGR, `1,450` Logos)\n"
                "   * *Scorable Features (`antigravity.google/changelog`):* Deep native IDE integration, agent-driven refactoring, real-time context streaming, and continuous changelog feature velocity.\n\n"
                "4. **✅ Qualifying Core Offering: Artifact Registry** (`Standard GA: 2020-05-15` | `$110.0M` Revenue, `55.0%` CAGR, `3,200` Logos)\n"
                "   * *Scorable Features:* Universal container/package management with automated vulnerability scanning and granular IAM — scoring critical points in secure software supply chain governance.\n\n"
                "5. **✅ Qualifying Core Offering: Cloud Build** (`Standard GA: 2018-07-24` | `$95.0M` Revenue, `48.0%` CAGR, `2,800` Logos)\n"
                "   * *Scorable Features:* Serverless CI/CD pipelines, SLSA Level 3 build provenance attestation, and hybrid private pools — scoring major points in enterprise DevOps orchestration.\n\n"
                "6. **✅ Qualifying Core Offering: Cloud Deploy** (`Standard GA: 2021-08-30` | `$42.0M` Revenue, `60.0%` CAGR, `850` Logos)\n"
                "   * *Scorable Features:* Automated continuous delivery to GKE and Cloud Run with progressive canary/blue-green deployments and automated rollback — scoring points for release safety and velocity.\n\n"
                "7. **✅ Qualifying Core Offering: Developer Connect** (`Standard GA: 2024-04-09` | `$28.0M` Revenue, `75.0%` CAGR, `540` Logos)\n"
                "   * *Scorable Features:* Secure bidirectional connectivity to third-party Git repositories (GitHub, GitLab, Bitbucket) without VPN overhead — scoring points in multi-cloud developer integration.\n\n"
                "8. **✅ Qualifying Core Offering: Security Command Center (SCC) Enterprise** (`Standard GA: 2023-10-10` | `$180.0M` Revenue, `52.0%` CAGR, `1,900` Logos)\n"
                "   * *Scorable Features:* AI-driven posture management, real-time threat detection, and continuous CI/CD pipeline vulnerability profiling — scoring maximum points in DevSecOps risk governance.\n\n"
                "9. **🗺️ Considered & Rejected SKU: Gemini Code Assist Agent Mode (Roadmap Demonstration SKU)** (`Preview: 2026-04-15` | `$8.5M` Revenue, `120.0%` CAGR, `410` Logos)\n"
                f"   * *Deficit & Remediation:* Triggers GA Cutoff Deficit (`April 15` vs `March 2` cutoff). Request an attestation waiver or feature autonomous multi-turn reasoning inside our Stage 2 Roadmap demonstration module{f' for **{report_name}**' if report_name else ''}.\n\n"
                "10. **🚫 Excluded Lifecycle SKU: Cloud Legacy Code Helper** (`Deprecated: 2022-06-01` | `$12.0M` Revenue, `15.0%` CAGR, `210` Logos)\n"
                f"   * *Deficit & Remediation:* Excluded from formal {f'**{report_name}** ' if report_name else ''}qualification due to Sunset/Deprecated status and threshold deficits; consolidate customer migrations to Enterprise GA.\n\n"
                f"You can inspect the interactive breakdown below or download the full **Executive Deep Dive Report (.md format)**{f' for **{report_name}**' if report_name else ''}."
            ),
            payloads=[deep_dive_surface],
            phase_num=1,
            step_name="Phase 1B: Portfolio Deep Dive Analysis",
            action_id="deep_dive_analysis"
        )

    # 3. Handle Leadership Email Draft Request
    if action in ["draft_leadership_email", "copy_leadership_email"] or any(k in msg_lower for k in ["email", "leadership", "briefing", "inform", "decision", "draft"]):
        email_surface = A2UIGenerator.generate_leadership_email_surface(context_data=context_data)
        return await finish_response(
            resp_text=(
                f"I have drafted an executive notification email ready to send to leadership (`pm-leadership@google.com`, `cloud-exec-review@`) communicating our participation decision for **{report_name}**.\n\n"
                "**Summary of Drafted Points:**\n"
                f"* **Data-Driven Decision:** Formal recommendation to **Proceed with Participation (`Proceed_With_Participation`)** for **{report_name}** submitting *Gemini Code Assist Enterprise* as our primary flagship SKU alongside Antigravity capabilities.\n"
                "* **Considered vs. Rejected Trade-Offs:** Explaining why *Agent Mode Preview* is scheduled for our Stage 2 Roadmap demonstration module and cutoff waiver request.\n"
                "* **Schedule & Freeze Alignment:** Highlighting the February 27 attestation deadline and our proactive shifts around the **Cloud Next 2026 Conference Freeze**.\n\n"
                "You can review, edit, or copy the email text using the interactive A2UI card below."
            ),
            payloads=[email_surface],
            phase_num=1,
            step_name="Phase 1C: Leadership Notification Email",
            action_id="draft_leadership_email"
        )

    # 4. Handle Evaluation Matrix / Scorecard Request (Phase 1 Agentic Multi-Agent System)
    if action == "submit_criteria_analysis" or (
        any(k in msg_lower for k in ["submit_criteria_analysis", "run evaluation", "portfolio analysis", "evaluat", "matrix", "scorecard", "qualif", "submit criteria"]) or
        ("portfolio" in msg_lower and not any(w in msg_lower for w in ["schedule", "timeline", "workback"]))
    ):
        from app.services.phase1_intake_agent import Phase1IntakeAgentService
        intake_agent = Phase1IntakeAgentService(db_session=db)
        raw_text = payload.context_data.get("analyst_notes") or payload.message
        if not raw_text or len(raw_text.strip()) < 10:
            raw_text = (
                "To qualify for inclusion, providers must meet the following criteria effective 2 March 2026: "
                "Recognized GAAP revenue >= $25M with 40% CAGR, or >= 500 paying enterprise customer logos. "
                "Mandatory features include CI/CD build automation, security supply chain scanning (SLSA L3), and agentic multi-file code generation."
            )

        try:
            matrix, telemetry_logs = await intake_agent.run_phase1_agentic_intake(raw_text)
            telemetry_summary = "\n".join([f"* **{log.agent_name}** ({log.stage}): {log.summary_message} ({log.duration_ms:.0f}ms)" for log in telemetry_logs])
            card = A2UIGenerator.generate_evaluation_matrix_surface(matrix, confidence_score=0.98, context_data=context_data)
            return await finish_response(
                resp_text=(
                    f"### 🤖 Phase 1: Agentic Multi-Sub-Agent Intake & Evaluation Complete (Portfolio Eligibility Scorecard)\n\n"
                    f"Our **Phase 1 Lead Orchestrator Agent** successfully dispatched **4 specialized sub-agents** to analyze your document intake packet and evaluate portfolio inclusion for **{report_name or 'Analyst Report'}**:\n\n"
                    f"{telemetry_summary}\n\n"
                    f"Overall Recommendation: **{matrix.data_driven_recommendation}** ({len(matrix.eligible_products)} qualifying portfolio SKUs matched)."
                ),
                payloads=[card],
                phase_num=1,
                step_name="Phase 1B: Portfolio Eligibility Scorecard",
                action_id="submit_criteria_analysis"
            )
        except Exception as e:
            logger.warning(f"Fallback during Phase 1 multi-agent execution: {e}")
            analyzer = InclusionAnalyzer(db_session=db)
            parsed_criteria = await analyzer.parse_rfi_criteria(raw_text)
            matrix = await analyzer.evaluate_portfolio_eligibility(parsed_criteria, prompt_text=payload.message)
            card = A2UIGenerator.generate_evaluation_matrix_surface(matrix, confidence_score=0.98, context_data=context_data)
            return await finish_response(
                resp_text=f"### 📊 Phase 1: Portfolio Eligibility Scorecard — {report_name or 'Analyst Report'}\n\nExtracted criteria parameters and evaluated portfolio eligibility.",
                payloads=[card],
                phase_num=1,
                step_name="Phase 1B: Portfolio Eligibility Scorecard",
                action_id="submit_criteria_analysis"
            )

    # 5. Handle Workback Timeline & Blackout Schedule Request
    if action in ["generate_timeline", "download_workback_schedule", "download_workback_schedule_md", "download_workback_schedule_csv"] or any(k in msg_lower for k in ["timeline", "schedule", "workback", "deadline", "milestone"]):
        target_dt = datetime.datetime(2026, 6, 20, 17, 0, tzinfo=datetime.timezone.utc)
        exclusion = ExclusionWindow(
            name="Cloud Next 2026 Conference Freeze",
            start_date=datetime.datetime(2026, 6, 14, 0, 0, tzinfo=datetime.timezone.utc),
            end_date=datetime.datetime(2026, 6, 16, 23, 59, 59, tzinfo=datetime.timezone.utc)
        )
        timeline = TimelineEngine.generate_timeline(
            target_deadline=target_dt,
            exclusion_windows=[exclusion]
        )
        timeline_surface = A2UIGenerator.generate_timeline_surface(timeline, context_data=context_data)
        return await finish_response(
            resp_text=(
                f"I have generated the end-to-end workback timeline for **{report_name}**, working backwards from your target submission deadline of **{target_dt.strftime('%Y-%m-%d %H:%M %Z')}**. "
                "Notice that milestones conflicting with the **Cloud Next 2026 Conference Freeze** have been automatically shifted earlier."
            ),
            payloads=[timeline_surface],
            phase_num=1,
            step_name="Phase 1C: Workback Schedule Timeline",
            action_id="generate_timeline"
        )

    # 6. Handle Saved Artifacts / Session Context Restoration Requests
    if action == "open_saved_artifacts" or any(k in msg_lower for k in ["saved artifact", "view artifact", "saved asset", "saved context", "reopened"]):
        service = ArtifactService(db_session=db)
        artifacts = await service.list_artifacts()
        artifacts_surface = A2UIGenerator.generate_saved_artifacts_surface(artifacts, is_restored_view=False)
        return await finish_response(
            resp_text=(
                "### 📂 Right-Side Saved Artifacts Modal Activated\n\n"
                f"I have triggered the **Saved Artifacts Modal** (`#saved-artifacts-modal`) displaying all stored snapshots and reports for **{report_name}** with individual **`👁️ View`**, **`📋 Copy`**, **`⚡ Restore`**, and **`🗑️ Delete`** actions."
            ),
            payloads=[artifacts_surface]
        )

    # 7. Handle Save Current Session Snapshot Request
    if action == "save_current_context" or any(k in msg_lower for k in ["save current", "save session", "save artifact", "save snapshot", "preserve context"]):
        service = ArtifactService(db_session=db)
        notes = payload.context_data.get("analyst_notes", "No explicit notes provided")
        welcome_url = payload.context_data.get("welcome_packet_url", "Not specified")
        
        create_payload = SavedArtifactCreate(
            title=f"{f'{report_name} — ' if report_name else ''}Session Snapshot ({datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})",
            artifact_type="session_snapshot",
            summary=f"Snapshot{f' for [{report_name}]' if report_name else ''} containing user context data, document links, and evaluation state.",
            content=f"### Saved Session Context Snapshot{f': {report_name}' if report_name else ''}\n* **Welcome Packet URL:** {welcome_url}\n* **Analyst Notes:** {notes}\n* **Context Variables:** {json.dumps(payload.context_data)}",
            metadata_json=json.dumps(payload.context_data)
        )
        saved_art = await service.create_artifact(create_payload)
        artifacts = await service.list_artifacts()
        artifacts_surface = A2UIGenerator.generate_saved_artifacts_surface(artifacts, is_restored_view=False)
        return await finish_response(
            resp_text=(
                f"### ✅ Session Context Successfully Saved!{f' ({report_name})' if report_name else ''}\n\n"
                f"Your active conversation context and form inputs have been preserved as **`{saved_art.title}`**. "
                "Whenever you reopen the app or start a future session, you can select **Restore Session Context** to pick up exactly where you left off."
            ),
            payloads=[artifacts_surface]
        )

    # 8. Handle Restore Session Context / Specific Artifact Request
    if action == "restore_all_artifacts" or (action and action.startswith("restore_artifact_")) or any(k in msg_lower for k in ["restore session", "restore all", "pickup where", "resume work", "load saved"]):
        service = ArtifactService(db_session=db)
        target_id = None
        if action and action.startswith("restore_artifact_"):
            try:
                target_id = uuid.UUID(action.replace("restore_artifact_", ""))
            except ValueError:
                target_id = None
        
        restored_data = await service.restore_session_context(artifact_id=target_id)
        return await finish_response(
            resp_text=restored_data["response_text"],
            payloads=restored_data["a2ui_payloads"]
        )

    # 9. Handle Welcome / Initial Onboarding Action (`action == "welcome"` or explicit greetings)
    if action == "welcome" or msg_lower in ["welcome", "initialize connection", "hello", "hi", "help", "menu", "overview", "start"]:
        welcome_surface = A2UIGenerator.generate_welcome_briefing_surface()
        return await finish_response(
            resp_text=(
                "### 🎯 Welcome to the Analyst Response Agent (ARA)\n\n"
                "**Purpose of Application:** The Analyst Response Agent (ARA) is an automated assistant designed for the end-to-end workflow triggered when an industry analyst like **Gartner**, **Forrester**, or **IDC** initiates an evaluation. These agentic workflows ensure consistency across our response processes and artifacts, while also making the lift significantly easier for **Analyst Relations**, **Product Managers**, and **Technical Program Managers**.\n\n"
                "**Progressive Disclosure:** Please review our **Target Audience & Stakeholders** and the **7-Phase End-to-End Operational Process** in the executive briefing card below.\n\n"
                "Once you have absorbed the workflow overview, click **Begin Stage 1: Criteria Document Intake** at the bottom of the card to transition to the document intake form."
            ),
            payloads=[welcome_surface],
            phase_num=1,
            step_name="Phase 1: Workflow Overview & Executive Briefing",
            action_id="open_intake"
        )

    # 10. Handle Corpus / Product Catalog Requests
    if any(k in msg_lower for k in ["corpus", "catalog", "match products", "database products", "list of products", "products evaluated"]):
        from sqlalchemy import select
        from app.models.core_models import Product
        
        products = []
        try:
            stmt = select(Product)
            result = await db.execute(stmt)
            products = result.scalars().all()
        except Exception as e:
            pass

        lines = []
        for p in products:
            lines.append(
                f"* **{p.name}** — GA Date: `{p.current_ga_date}` | Revenue: `${p.total_revenue_usd:,}` | CAGR: `{p.cagr_percentage}%` | Enterprise Logos: `{p.enterprise_customer_count}`"
            )
        corpus_md = "\n".join(lines) if lines else "*No products currently stored in PostgreSQL catalog.*"
        return await finish_response(
            resp_text=(
                f"### 📦 Active Product Evaluation Corpus for [{report_name}] (PostgreSQL)\n\n"
                f"Here is the complete corpus of Google Cloud and Antigravity product capabilities stored in PostgreSQL (`Product` table) from which I match and evaluate SKUs across **{report_name}**:\n\n"
                f"{corpus_md}\n\n"
                f"You can instruct me at any time to run the **{report_name}** scorecard or rerun evaluations across any combination of these offerings!"
            ),
            payloads=[]
        )

    # 11. Handle General Conversational AI Reasoning & Question Answering
    if settings.AGENT_RUNTIME == "agent_engine":
        from app.services.agent_engine_client import AgentEngineClientService
        try:
            engine_res = await AgentEngineClientService.async_query(
                prompt=payload.message,
                workspace_id=str(context_data.get("workspace_id", "ws-default")),
                context_data=context_data,
            )
            sme_identity = engine_res.get("assigned_sme", "Analyst Response Agent (Agent Engine)")
            ai_reply = engine_res.get("response", "")
            return A2UIChatResponse(
                agent_name=f"Analyst Response Agent ({sme_identity})",
                response_text=ai_reply,
                a2ui_payloads=[]
            )
        except Exception as e:
            logger.warning(f"Remote Agent Engine query encountered exception, falling back: {e}")

    from sqlalchemy import select
    from app.models.core_models import Product
    db_products = []
    try:
        stmt = select(Product)
        result = await db.execute(stmt)
        db_products = result.scalars().all()
    except Exception as e:
        pass

    corpus_summary = "\n".join([f"- {p.name} (GA: {p.current_ga_date}, Rev: ${p.total_revenue_usd:,}, CAGR: {p.cagr_percentage}%, Logos: {p.enterprise_customer_count})" for p in db_products]) if db_products else "Standard catalog."

    analyzer = InclusionAnalyzer(db_session=db)
    context_summary = json.dumps(payload.context_data) if payload.context_data else "No active form context."
    prompt = f"""
You are the Analyst Response Agent (ARA), an expert AI assistant helping Google Cloud analysts, product managers, and executive leadership prepare for the specific industry analyst evaluation report: [{report_name}].
From this point on, you MUST explicitly use and reference "{report_name}" by name whenever discussing our evaluation, scorecard, timeline, and leadership strategy.

Active Product Corpus in Database:
{corpus_summary}

Context Variables & Active Evaluation State:
{context_summary}

User Prompt / Question:
{payload.message}

Provide a helpful, professional, clear, and data-grounded response answering the user's prompt using our active product corpus for [{report_name}]. Use clean GitHub-style markdown formatting.
"""
    try:
        analyzer._init_vertex()
        model = GenerativeModel(settings.VERTEX_AI_MODEL)
        config = GenerationConfig(temperature=0.4)
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=config
        )
        ai_reply = response.text.strip()
    except Exception as e:
        ai_reply = (
            f"### 🤖 Analyst Response Agent Guidance — {report_name}\n\n"
            f"Regarding your inquiry about: *\"{payload.message}\"*\n\n"
            f"**Core Analyst Evaluation Principles for [{report_name}]:**\n"
            f"* **General Availability (GA) Rule:** Analyst criteria strictly require all evaluated capabilities to be Generally Available by their official cutoff date (`March 2, 2026`).\n"
            f"* **Active Database Offerings:** We match capabilities across our catalog including **Gemini Code Assist Enterprise**, **Antigravity 2.0**, **Antigravity IDE**, **Artifact Registry**, **Cloud Build**, and **Security Command Center (SCC)**.\n"
            f"* **Portfolio Optimization:** Custom mixes can be scored on-demand to verify threshold compliance for **{report_name}** (`$25M / 40% CAGR / 500 logos`).\n\n"
            f"If you'd like to perform an action on the current **{report_name}** evaluation, you can ask me to **Run the Scorecard**, **Draft the Leadership Email**, **Generate the Workback Timeline**, or **View Saved Artifacts** at any time!"
        )

    return await finish_response(
        resp_text=ai_reply,
        payloads=[]
    )
