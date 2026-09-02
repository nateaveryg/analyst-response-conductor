import pytest
from app.services.subagents.vector_retrieval_agent import VectorRetrievalSubAgent
from app.services.subagents.grounded_synthesis_agent import GroundedSynthesisSubAgent
from app.services.subagents.compliance_audit_agent import ComplianceAuditSubAgent


@pytest.mark.asyncio
async def test_vector_retrieval_subagent():
    agent = VectorRetrievalSubAgent()
    res = await agent.execute_retrieval("authentication methods IAM")
    assert res.total_matches_found > 0
    assert res.execution_duration_ms >= 0.0
    assert any("IAM" in chunk["product_tag"] or "IAM" in chunk["chunk_text"] for chunk in res.matched_chunks)


@pytest.mark.asyncio
async def test_grounded_synthesis_subagent():
    agent = GroundedSynthesisSubAgent()
    retrieved = [
        {
            "source_rfi_title": "2025 Gartner Magic Quadrant for CNAP — [Tab 2] Q6",
            "original_answer_text": "Natively integrates with Enterprise IAM via OIDC and SAML 2.0."
        }
    ]
    res = await agent.execute_synthesis(
        section_identifier="Tab 2 Q6",
        question_text="Describe IAM authentication",
        retrieved_chunks=retrieved
    )
    assert res.grounding_confidence_score == 0.982
    assert "color:#7e57c2" in res.draft_response
    assert "OIDC" in res.draft_response
    assert res.execution_duration_ms >= 0.0


@pytest.mark.asyncio
async def test_compliance_audit_subagent_compliant():
    agent = ComplianceAuditSubAgent()
    res = await agent.execute_audit("Fully supported in Standard GA across Google Cloud Run regions.")
    assert res.is_compliant is True
    assert res.compliance_score == 1.0
    assert len(res.flagged_terms) == 0


@pytest.mark.asyncio
async def test_compliance_audit_subagent_flagged_terms():
    agent = ComplianceAuditSubAgent()
    res = await agent.execute_audit("Feature is currently in preview and alpha testing for roadmap target.")
    assert res.is_compliant is False
    assert res.compliance_score == 0.75
    assert "preview" in res.flagged_terms
    assert "alpha" in res.flagged_terms
