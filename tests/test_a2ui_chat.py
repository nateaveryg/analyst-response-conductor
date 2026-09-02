from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_serve_a2ui_portal():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "A2UI Executive Portal" in response.text
        assert "Analyst Response Agent (ARA)" in response.text


@pytest.mark.asyncio
async def test_a2ui_chat_welcome():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "hello"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Welcome to the Analyst Response Agent (ARA)" in data["response_text"]
        assert "Purpose of Application:" in data["response_text"]
        assert "Analyst Relations**, **Product Managers**, and **Technical Program Managers**" in data["response_text"]
        assert len(data["a2ui_payloads"]) > 0
        assert "<a2ui-json>" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_intake_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "open intake form", "action_id": "open_intake"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response_text"] == ""
        assert "Criteria & Demonstration Document Intake" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_timeline_action():
    mock_db = AsyncMock()
    app.dependency_overrides[from_app_db_dependency()] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "generate workback schedule", "action_id": "generate_timeline"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "workback timeline" in data["response_text"]
        assert "Cloud Next 2026 Conference Freeze" in data["response_text"]
        assert "Workback Schedule & Corporate Blackout Windows" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_show_workback_schedule_routing():
    mock_db = AsyncMock()
    app.dependency_overrides[from_app_db_dependency()] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "show workback schedule for our portfolio"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "workback timeline" in data["response_text"]
        assert "Workback Schedule & Corporate Blackout Windows" in data["a2ui_payloads"][0]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_a2ui_chat_leadership_email_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "draft leadership email", "action_id": "draft_leadership_email"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "drafted an executive notification email ready to send to leadership" in data["response_text"]
        assert "Draft Executive Notification Email for Leadership" in data["a2ui_payloads"][0]
        assert "Everest" not in data["response_text"]
        assert "Everest" not in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_general_ai_response():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "What is the GAAP revenue floor threshold?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert any(k in data["response_text"] for k in ["Executive Technical Response", "Google Cloud", "GAAP Revenue", "General Availability", "Analyst Response Agent"])
        # Ensure arbitrary chat queries return AI reasoning instead of throwing the upload/intake form surface back
        assert data["a2ui_payloads"] == []


def from_app_db_dependency():
    from app.core.database import get_db
    return get_db


@pytest.mark.asyncio
async def test_a2ui_chat_phase_2_routing_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "assign tasks", "action_id": "assign_tasks", "context_data": {"analyst_notes": "devsecops evaluation"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Phase 2: SME Task Routing & Workstream Assignment" in data["response_text"]
        assert "David Jacobs" in data["a2ui_payloads"][0]
        assert "Nathen Harvey" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_phase_3_kickoff_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "align teams", "action_id": "kickoff_project"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter" in data["response_text"]
        assert "T-14 Storyboard & Narrative Freeze" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_phase_4_upload_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "upload rfi", "action_id": "upload_rfi"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Phase 4A: RFI Questionnaire Spreadsheet Intake" in data["response_text"]
        assert "/intake/rfi_spreadsheet_url" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_phase_4_rfi_response_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "generate rfi responses", "action_id": "generate_rfi_responses"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts" in data["response_text"]
        assert "98.2% Grounded" in data["a2ui_payloads"][0]
        assert "download_rfi_md" in data["a2ui_payloads"][0]
        assert "download_rfi_csv" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_phase_5_demo_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "deploy demo environments", "action_id": "open_demo_sandboxes"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Phase 5: On-Demand Demo Environments & Storyboard Playbook" in data["response_text"]
        assert "download_demo_playbook" in data["a2ui_payloads"][0]
        assert "71% Complete" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_phase_6_review_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "executive review", "action_id": "open_executive_review"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Phase 6: Executive Review Panel & GA Deficit Attestation Waivers" in data["response_text"]
        assert "download_executive_memo" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_a2ui_chat_phase_7_publication_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "publication and recognitions", "action_id": "open_publication_recognition"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Phase 7: Master Portal Publication & Contributor Recognition Manifesto" in data["response_text"]
        assert "download_publication_bundle" in data["a2ui_payloads"][0]
        assert "100% Complete" in data["a2ui_payloads"][0]
