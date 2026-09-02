"""
Hermetic Unit Tests for ConductorAgentEngine (Vertex AI Agent Engine Runtime).
"""
import pytest
from app.agent_engine.conductor_engine import ConductorAgentEngine


@pytest.fixture
def agent_engine():
    engine = ConductorAgentEngine(
        model_name="gemini-2.5-flash",
        project="riccardo-blog-test-v1",
        location="us-central1",
    )
    engine.set_up()
    return engine


def test_agent_engine_initialization(agent_engine):
    assert agent_engine.VERSION == "2.2.0"
    assert agent_engine.model_name == "gemini-2.5-flash"
    assert agent_engine.project == "riccardo-blog-test-v1"
    assert agent_engine.location == "us-central1"
    assert agent_engine._is_initialized is True


def test_agent_engine_query_cnapp(agent_engine):
    result = agent_engine.query(
        prompt="How does Google Cloud manage container vulnerability lifecycle and agentless workload scanning?",
        workspace_id="ws-test-01",
    )
    assert result["status"] == "success"
    assert result["agent_engine_version"] == "2.2.0"
    assert result["category"] == "CNAPP"
    assert result["assigned_sme"] == "security-sme@google.com"
    assert result["confidence_score"] >= 0.80
    assert "Executive Technical Response" in result["response"]
    assert "SOC2 Type II" in result["compliance_frameworks"]
    assert result["latency_ms"] >= 0.0


def test_agent_engine_query_devsecops(agent_engine):
    result = agent_engine.query(
        prompt="Describe the automated multi-stage CI/CD pipeline and canary deployment strategy in Cloud Deploy",
        workspace_id="ws-test-02",
    )
    assert result["status"] == "success"
    assert result["category"] == "DEVSECOPS"
    assert result["assigned_sme"] == "devops-sme@google.com"
    assert result["confidence_score"] >= 0.85
    assert "Canary" in result["response"]


def test_agent_engine_query_ai(agent_engine):
    result = agent_engine.query(
        prompt="Explain the multi-agent orchestration, pgvector RAG retrieval, and Gemini reasoning engine setup",
        workspace_id="ws-test-03",
    )
    assert result["status"] == "success"
    assert result["category"] == "ENTERPRISE_AI"
    assert result["assigned_sme"] == "ai-sme@google.com"


def test_agent_engine_streaming(agent_engine):
    generator = agent_engine.stream_query(
        prompt="Evaluate Cloud Security Posture Management (CSPM) compliance"
    )
    events = list(generator)
    assert len(events) >= 5
    # First 4 are stage updates
    stage_phases = [e["phase"] for e in events if e.get("type") == "stage_update"]
    assert "INTAKE_VALIDATION" in stage_phases
    assert "GROUNDED_RETRIEVAL" in stage_phases
    # Last event is the completion result
    completion = events[-1]
    assert completion["type"] == "completion"
    assert completion["result"]["status"] == "success"


@pytest.mark.asyncio
async def test_agent_engine_async_methods(agent_engine):
    result = await agent_engine.async_query("How are Cloud IAM permissions audited?")
    assert result["status"] == "success"
    assert result["category"] == "CNAPP"

    streamed_events = []
    async for event in agent_engine.async_stream_query("Audit CI/CD pipeline"):
        streamed_events.append(event)
    assert len(streamed_events) >= 5


def test_agent_engine_agent_card(agent_engine):
    card = agent_engine.get_agent_card()
    assert card["name"] == "Analyst Response Agent (Agent Engine)"
    assert card["version"] == "2.2.0"
    assert "Vertex AI Agent Engine" in card["runtime"]
    assert "RFI Multi-Tab Spreadsheet Ingestion" in card["capabilities"]
    protocols = [p["type"] for p in card["protocols"]]
    assert "A2A_AGENT" in protocols
    assert "VERTEX_REASONING_ENGINE" in protocols


def test_agent_engine_evaluation(agent_engine):
    eval_result = agent_engine.evaluate_response(
        question="How does Conductor ensure SOC2 compliance?",
        generated_answer="Google Cloud adheres to strict SOC2 Type II and ISO 27001 data isolation policies across all container runtimes.",
    )
    assert eval_result["passed_evaluation"] is True
    assert eval_result["overall_quality_score"] >= 0.85
    assert eval_result["groundedness_score"] >= 0.90
    assert eval_result["compliance_adherence_score"] >= 0.90
