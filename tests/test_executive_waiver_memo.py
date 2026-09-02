import pytest
from app.services.executive_review_agent import ExecutiveReviewAgentService


def test_executive_review_dossier_synthesis():
    dossier = ExecutiveReviewAgentService.generate_governance_dossier(report_name="Gartner MQ CNAP 2026")
    assert dossier["panel_verdict"]["status"] == "APPROVED BY EXECUTIVE REVIEW PANEL"
    assert len(dossier["risk_assessment_matrix"]) > 0
    assert "target_offering" in dossier["deficit_waiver_dossier"]


def test_executive_review_memo_digital_signature():
    dossier = ExecutiveReviewAgentService.generate_governance_dossier(report_name="Gartner MQ CNAP 2026")
    memo_md = ExecutiveReviewAgentService.format_review_memo_markdown(dossier)
    assert "# Phase 6: Executive Review Panel & GA Deficit Attestation Waiver Memo" in memo_md
    assert "[DIGITAL SIGNATURE ATTESTED: VP / GM Analyst Relations & Product Management]" in memo_md
    assert "Target Remediation Date:" in memo_md
    assert "sha256:" in memo_md
