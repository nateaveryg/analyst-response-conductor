import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_stream_telemetry_endpoint():
    response = client.get("/api/v1/stream/telemetry")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "data:" in content
    assert any(k in content for k in ["VertexAIAgentEngine", "Phase1IntakeAgentService", "agent_engine_stage"])
