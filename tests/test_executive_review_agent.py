import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.executive_review_agent import ExecutiveReviewAgentService


def test_executive_review_agent_cnap_audit() -> None:
    data = ExecutiveReviewAgentService.generate_governance_dossier(report_name="Gartner CNAP 2026")
    assert "report_scope" in data
    assert "CNAP" in data["report_scope"]
    assert "panel_verdict" in data
    assert "APPROVED BY EXECUTIVE REVIEW PANEL" in data["panel_verdict"]["status"]
    assert "risk_assessment_matrix" in data
    assert len(data["risk_assessment_matrix"]) == 4

    waiver = data["deficit_waiver_dossier"]
    assert "Gemini Code Assist Enterprise Agent Engine" in waiver["target_offering"]
    assert "Mukul Saha MQ Engagement Leadership Team" in waiver["executive_signoff"]


def test_executive_review_agent_universal_audit() -> None:
    data = ExecutiveReviewAgentService.generate_governance_dossier(report_name="Universal Code & DevSecOps 2026")
    assert "report_scope" in data
    assert "Universal Code & Agent Platforms / DevSecOps Platforms" in data["report_scope"]
    waiver = data["deficit_waiver_dossier"]
    assert "Gemini Code Assist Agent Mode" in waiver["target_offering"]
    assert "Consolidated Universal Code Executive Panel" in waiver["executive_signoff"]


def test_format_review_memo_markdown_output() -> None:
    data = ExecutiveReviewAgentService.generate_governance_dossier("cnap")
    md = ExecutiveReviewAgentService.format_review_memo_markdown(data)
    assert "# Phase 6: Executive Review Panel & GA Deficit Attestation Waiver Memo" in md
    assert "## 1. Governance Verification & Commercial Risk Remediation" in md
    assert "| Governance Checkpoint | Lead Reviewer / Authority | Scope & Methodology | Verification Outcome |" in md
    assert "## 2. Formal Preview Cutoff Deficit Attestation Waiver Request" in md
    assert "Mukul Saha MQ Engagement Leadership Team" in md


@pytest.mark.asyncio
async def test_a2ui_chat_invoke_executive_governance_agent() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        payload = {
            "action_id": "generate_executive_review_agent",
            "message": "Invoke VP/GM Governance Sub-Agent",
            "context_data": {"report_name": "Gartner CNAP 2026"}
        }
        response = await client.post("/api/v1/a2ui/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "VP/GM Executive Governance & Compliance Sub-Agent" in data["response_text"]
        payloads = data.get("a2ui_payloads", [])
        assert len(payloads) == 1
        assert "exec_review_preview_card" in payloads[0]
        assert "Risk Assessment Matrix" in data["response_text"]
