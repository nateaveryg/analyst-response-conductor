"""
Unit tests for Vertex AI Agent Engine Client Service and Runtime Integration.
"""
from unittest.mock import MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.config import settings
from app.services.agent_engine_client import AgentEngineClientService
from app.main import app


@pytest.fixture(autouse=True)
def reset_client_cache():
    AgentEngineClientService.clear_cache()
    yield
    AgentEngineClientService.clear_cache()


def test_agent_engine_client_query_mocked():
    mock_engine = MagicMock()
    mock_engine.query.return_value = {
        "status": "success",
        "category": "DEVSECOPS",
        "assigned_sme": "devops-sme@google.com",
        "response": "Automated canary pipelines via Cloud Deploy."
    }

    with patch("vertexai.agent_engines.get", return_value=mock_engine) as mock_get:
        result = AgentEngineClientService.query(
            prompt="How do we deploy with canary strategy?",
            workspace_id="ws-test-1",
            resource_name="projects/123/locations/us-central1/reasoningEngines/456"
        )
        assert result["status"] == "success"
        assert result["category"] == "DEVSECOPS"
        assert "Cloud Deploy" in result["response"]
        mock_get.assert_called_once_with("projects/123/locations/us-central1/reasoningEngines/456")


@pytest.mark.asyncio
async def test_agent_engine_client_async_query_mocked():
    mock_engine = MagicMock()
    mock_engine.query.return_value = {
        "status": "success",
        "category": "CNAPP",
        "assigned_sme": "security-sme@google.com",
        "response": "Zero-trust IAM and posture verification."
    }

    with patch("vertexai.agent_engines.get", return_value=mock_engine):
        result = await AgentEngineClientService.async_query(
            prompt="What are our security posture controls?",
            workspace_id="ws-test-2"
        )
        assert result["status"] == "success"
        assert result["assigned_sme"] == "security-sme@google.com"


def test_agent_engine_client_stream_query_mocked():
    mock_engine = MagicMock()
    mock_engine.stream_query.return_value = [
        {"type": "stage_update", "phase": "INTAKE_VALIDATION", "message": "Validating..."},
        {"type": "stage_update", "phase": "SME_ROUTING", "message": "Routing to DevOps SME..."},
        {"type": "completion", "result": {"response": "Final Grounded Synthesis"}}
    ]

    with patch("vertexai.agent_engines.get", return_value=mock_engine):
        chunks = list(AgentEngineClientService.stream_query(prompt="Evaluate RFI criteria"))
        assert len(chunks) == 3
        assert chunks[0]["phase"] == "INTAKE_VALIDATION"
        assert chunks[1]["phase"] == "SME_ROUTING"
        assert chunks[2]["result"]["response"] == "Final Grounded Synthesis"


@pytest.mark.asyncio
async def test_agent_engine_client_async_stream_query_mocked():
    mock_engine = MagicMock()
    mock_engine.stream_query.return_value = [
        {"phase": "STAGE_1", "message": "Deconstructing worksheets..."},
        {"phase": "STAGE_2", "message": "Auditing rubric thresholds..."}
    ]

    with patch("vertexai.agent_engines.get", return_value=mock_engine):
        collected = []
        async for chunk in AgentEngineClientService.async_stream_query(prompt="Deconstruct tabs"):
            collected.append(chunk)
        assert len(collected) == 2
        assert collected[0]["phase"] == "STAGE_1"


def test_agent_engine_client_caching():
    mock_engine = MagicMock()
    with patch("vertexai.agent_engines.get", return_value=mock_engine) as mock_get:
        engine1 = AgentEngineClientService.get_engine("projects/test/locations/us-central1/reasoningEngines/999")
        engine2 = AgentEngineClientService.get_engine("projects/test/locations/us-central1/reasoningEngines/999")
        assert engine1 is engine2
        # Only one call because of caching
        assert mock_get.call_count == 1


def test_environment_resource_resolution():
    with patch.object(settings, "ENVIRONMENT", "development"):
        assert settings.active_agent_engine_resource == settings.AGENT_ENGINE_DEV_RESOURCE

    with patch.object(settings, "ENVIRONMENT", "staging"):
        assert settings.active_agent_engine_resource == settings.AGENT_ENGINE_STAGING_RESOURCE

    with patch.object(settings, "ENVIRONMENT", "production"):
        assert settings.active_agent_engine_resource == settings.AGENT_ENGINE_PROD_RESOURCE


@pytest.mark.asyncio
async def test_agent_card_runtime_advertisement():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/agent-card")
        assert response.status_code == 200
        card = response.json()
        assert "cloud-run-and-agent-engine" in card["runtime"] or "cloud-run" in card["runtime"]
        assert "VERTEX_REASONING_ENGINE" in card["supportedProtocols"]
        assert "Analyst Response Agent" in card["displayName"]
