import datetime
from decimal import Decimal
import pytest
from app.schemas.inclusion_schemas import InclusionEvaluationMatrix
from app.schemas.orchestration_schemas import Milestone, WorkbackTimeline
from app.services.a2ui_generator import A2UIGenerator


def test_generate_intake_form_surface():
    a2ui_str = A2UIGenerator.generate_intake_form_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "</a2ui-json>" in a2ui_str
    assert "Welcome Packet / Inclusion Criteria Document Link" in a2ui_str
    assert "Phase 1: Criteria & Demonstration Document Intake" in a2ui_str
    assert "Target Audience & Stakeholders" in a2ui_str
    assert "Outbound Product Managers (OPMs)" in a2ui_str
    assert "7-Phase Operational Lifecycle Progress (14% Complete)" in a2ui_str
    assert "[🟢 1. Evaluate (Active)]" in a2ui_str


def test_generate_welcome_briefing_surface():
    a2ui_str = A2UIGenerator.generate_welcome_briefing_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "welcome_briefing_card" in a2ui_str
    assert "SectionBox" in a2ui_str
    assert "Universal Analyst Evaluation Response Agent" in a2ui_str
    assert "Target Audience & Stakeholders" in a2ui_str
    assert "7-Phase End-to-End Operational Process" in a2ui_str
    assert "1. Evaluate Inclusion Criteria & Strategic Participation" in a2ui_str
    assert "($25M" not in a2ui_str
    assert "Begin Phase 1: Criteria Document Intake" in a2ui_str


def test_generate_evaluation_matrix_surface():
    matrix = InclusionEvaluationMatrix(
        eligible_products=["Gemini Code Assist Enterprise (Standard GA)"],
        rule_violations=[
            "[Cloud Legacy Code Helper] Revenue Rule Violation: Product revenue below floor.",
            "[Agent Mode Preview] GA Rule Violation: Product GA date 2026-04-15 after cutoff."
        ],
        data_driven_recommendation="Decline_Due_To_Score_Risk",
    )

    a2ui_str = A2UIGenerator.generate_evaluation_matrix_surface(matrix, confidence_score=0.98)
    assert "<a2ui-json>" in a2ui_str
    assert "Portfolio Eligibility Scorecard - Universal Analyst Evaluation" in a2ui_str
    assert "Gemini Code Assist Enterprise" in a2ui_str
    assert "Revenue Rule Violation" in a2ui_str
    assert "Open & Download Comprehensive Deep Dive Analysis Report" in a2ui_str


def test_generate_deep_dive_surface():
    a2ui_str = A2UIGenerator.generate_deep_dive_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Deep Dive Portfolio Analysis & Threshold Deficit Breakdown" in a2ui_str
    assert "Gemini Code Assist Enterprise" in a2ui_str
    assert "Antigravity 2.0" in a2ui_str
    assert "Antigravity IDE" in a2ui_str
    assert "Artifact Registry" in a2ui_str
    assert "Cloud Build" in a2ui_str
    assert "Cloud Deploy" in a2ui_str
    assert "Developer Connect" in a2ui_str
    assert "Security Command Center (SCC) Enterprise" in a2ui_str
    assert "Considered & Rejected: Gemini Code Assist Agent Mode" in a2ui_str
    assert "Download Full Executive Deep Dive Report" in a2ui_str
    assert "Everest" not in a2ui_str


def test_generate_leadership_email_surface():
    a2ui_str = A2UIGenerator.generate_leadership_email_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Draft Executive Notification Email for Leadership" in a2ui_str
    assert "pm-leadership@google.com" in a2ui_str
    assert "PROCEED WITH PARTICIPATION" in a2ui_str
    assert "Executive Decision: PROCEED WITH PARTICIPATION —" in a2ui_str
    assert "Copy Email Draft to Clipboard" in a2ui_str


def test_generate_timeline_surface():
    timeline = WorkbackTimeline(
        external_deadline=datetime.datetime(2026, 6, 20, 17, 0, tzinfo=datetime.timezone.utc),
        exclusion_windows_applied=[],
        milestones=[
            Milestone(
                name="Automated RAG Ingestion",
                offset_days=18,
                target_date=datetime.datetime(2026, 6, 2, 17, 0, tzinfo=datetime.timezone.utc),
                original_date=datetime.datetime(2026, 6, 2, 17, 0, tzinfo=datetime.timezone.utc),
                shifted=False,
                shift_reason="",
            ),
            Milestone(
                name="Executive Review",
                offset_days=5,
                target_date=datetime.datetime(2026, 6, 15, 17, 0, tzinfo=datetime.timezone.utc),
                original_date=datetime.datetime(2026, 6, 13, 17, 0, tzinfo=datetime.timezone.utc),
                shifted=True,
                shift_reason="Shifted due to Cloud Next freeze",
            ),
        ],
    )

    a2ui_str = A2UIGenerator.generate_timeline_surface(timeline)
    assert "<a2ui-json>" in a2ui_str
    assert "Workback Schedule & Corporate Blackout Windows (Universal Evaluation)" in a2ui_str
    assert "Automated RAG Ingestion" in a2ui_str
    assert "⚠️ Shifted from 2026-06-13: Shifted due to Cloud Next freeze" in a2ui_str
    assert "Download Workback Schedule Exclusively (.md format)" in a2ui_str
    assert "Download Workback Schedule Exclusively (.csv format)" in a2ui_str


def test_resolve_analyst_report_name_devsecops():
    ctx = {"welcome_packet_url": "https://docs.google.com/devsecops-mq-2026", "analyst_notes": "devsecops capability evaluation"}
    name = A2UIGenerator.resolve_analyst_report_name(ctx)
    assert name == "Magic Quadrant and Critical Capabilities for DevSecOps Platforms, 2026"


def test_generate_task_assignment_surface():
    ctx = {"welcome_packet_url": "https://docs.google.com/devsecops-mq-2026", "analyst_notes": "devsecops evaluation"}
    a2ui_str = A2UIGenerator.generate_task_assignment_surface(context_data=ctx)
    assert "<a2ui-json>" in a2ui_str
    assert "Phase 2: SME Task Routing & Workstream Assignment" in a2ui_str
    assert "David Jacobs" in a2ui_str
    assert "Nathen Harvey" in a2ui_str
    assert "Al Huizenga" in a2ui_str
    assert "Nate Avery & Ashley Castillo" in a2ui_str
    assert "kickoff_project" in a2ui_str


def test_generate_kickoff_alignment_surface():
    a2ui_str = A2UIGenerator.generate_kickoff_alignment_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter" in a2ui_str
    assert "Phase 5 Video Recording Budget Guidelines" in a2ui_str
    assert "T-14 Storyboard & Narrative Freeze" in a2ui_str
    assert "upload_rfi" in a2ui_str


def test_generate_rfi_upload_surface():
    a2ui_str = A2UIGenerator.generate_rfi_upload_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Phase 4A: RFI Questionnaire Spreadsheet Intake" in a2ui_str
    assert "/intake/rfi_spreadsheet_url" in a2ui_str
    assert "generate_rfi_responses" in a2ui_str


def test_generate_rfi_response_surface():
    a2ui_str = A2UIGenerator.generate_rfi_response_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts" in a2ui_str
    assert "98.2% Grounded" in a2ui_str
    assert "download_rfi_md" in a2ui_str
    assert "download_rfi_csv" in a2ui_str
    assert "deploy_demo_environments" in a2ui_str


def test_resolve_analyst_report_name_cnap():
    res = A2UIGenerator.resolve_analyst_report_name({"welcome_packet_url": "https://drive.google.com/drive/folders/1IR1letCi5MLv-Yk0aTOoRTJQm9jBTPCh"})
    assert res == "Magic Quadrant and Critical Capabilities for Cloud-Native Application Platforms, 2026"


def test_generate_task_assignment_surface_cnap():
    a2ui_str = A2UIGenerator.generate_task_assignment_surface(context_data={"welcome_packet_url": "https://drive.google.com/drive/folders/1IR1letCi5MLv-Yk0aTOoRTJQm9jBTPCh"})
    assert "Serverless Domain Lead" in a2ui_str
    assert "GKE Enterprise Lead" in a2ui_str
    assert "Platform Engineering Lead" in a2ui_str


def test_generate_kickoff_alignment_surface_cnap():
    a2ui_str = A2UIGenerator.generate_kickoff_alignment_surface(context_data={"welcome_packet_url": "https://drive.google.com/drive/folders/1IR1letCi5MLv-Yk0aTOoRTJQm9jBTPCh"})
    assert "45m Overall Cap" in a2ui_str
    assert "download_cnap_kickoff_deck" in a2ui_str
    assert "Phase 5 Video Recording Budget Guidelines" in a2ui_str


def test_generate_demo_sandbox_surface():
    a2ui_str = A2UIGenerator.generate_demo_sandbox_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Phase 5: On-Demand Demo Environments & Storyboard Playbook" in a2ui_str
    assert "71% Complete" in a2ui_str
    assert "download_demo_playbook" in a2ui_str
    assert "open_executive_review" in a2ui_str


def test_generate_demo_sandbox_surface_cnap():
    a2ui_str = A2UIGenerator.generate_demo_sandbox_surface(context_data={"welcome_packet_url": "https://drive.google.com/drive/folders/1IR1letCi5MLv-Yk0aTOoRTJQm9jBTPCh"})
    assert "45 minutes" in a2ui_str
    assert "serverless-sme@" in a2ui_str
    assert "gke-sme@" in a2ui_str


def test_generate_executive_review_surface():
    a2ui_str = A2UIGenerator.generate_executive_review_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Phase 6: Executive Review Panel & GA Deficit Attestation Waivers" in a2ui_str
    assert "86% Complete" in a2ui_str or "85% Complete" in a2ui_str or "Phase 6 of 7" in a2ui_str
    assert "download_executive_memo" in a2ui_str
    assert "open_publication_recognition" in a2ui_str


def test_generate_publication_recognition_surface():
    a2ui_str = A2UIGenerator.generate_publication_recognition_surface()
    assert "<a2ui-json>" in a2ui_str
    assert "Phase 7: Master Portal Publication & Contributor Recognition Manifesto" in a2ui_str
    assert "100% Complete" in a2ui_str
    assert "download_publication_bundle" in a2ui_str
    assert "David Jacobs" in a2ui_str

