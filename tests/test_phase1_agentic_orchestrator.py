import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api.v1.a2ui_chat import A2UIChatRequest, handle_a2ui_chat
from app.services.phase1_intake_agent import Phase1IntakeAgentService


@pytest.fixture
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_res
    return session


@pytest.mark.asyncio
async def test_phase1_orchestration_pipeline(mock_db_session: AsyncMock):
    intake_agent = Phase1IntakeAgentService(db_session=mock_db_session)
    raw_input = """
    Gartner Magic Quadrant for DevSecOps Platforms 2026 Criteria
    Target GA Cutoff: 2026-03-02
    GAAP Revenue >= $25M with 30% CAGR
    Mandatory features: CI/CD build automation, security scanning (SLSA L3), and agentic multi-file code generation.
    """
    matrix, telemetry = await intake_agent.run_phase1_agentic_intake(raw_input)
    assert matrix.data_driven_recommendation is not None
    assert len(telemetry) == 4
    assert telemetry[0].agent_name == "RfiDocumentParserSubAgent"
    assert telemetry[1].agent_name == "CriteriaExtractionSubAgent"
    assert telemetry[2].agent_name == "PortfolioMappingSubAgent"
    assert telemetry[3].agent_name == "GovernanceGoNoGoSubAgent"


@pytest.mark.asyncio
async def test_phase1_chat_routing_integration(mock_db_session: AsyncMock):
    req = A2UIChatRequest(
        message="Evaluate portfolio matrix criteria for Gartner MQ DevSecOps 2026",
        action_id="submit_criteria_analysis",
        context_data={"report_name": "Gartner MQ DevSecOps 2026", "analyst_notes": "GAAP Revenue $50M, 500 customers."}
    )
    resp = await handle_a2ui_chat(payload=req, db=mock_db_session)
    assert resp.response_text is not None
    assert "Phase 1: Agentic Multi-Sub-Agent Intake" in resp.response_text
    assert len(resp.a2ui_payloads) == 1


@pytest.mark.asyncio
async def test_phase1_unhappy_path_malformed_user_input(mock_db_session: AsyncMock):
    # Simulate an end-user providing invalid/malformed text to chat
    req = A2UIChatRequest(
        message="Evaluate criteria scorecard ??? invalid prompt <<< >>>",
        action_id="submit_criteria_analysis",
        context_data={"analyst_notes": "xyz123 empty invalid input"}
    )
    resp = await handle_a2ui_chat(payload=req, db=mock_db_session)
    assert resp.response_text is not None
    # Verify defensive recovery and baseline matrix generation without server crashing
    assert len(resp.a2ui_payloads) == 1
