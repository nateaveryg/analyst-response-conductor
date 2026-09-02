import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.database import get_db
from app.models.core_models import Workspace, SavedArtifact


@pytest.fixture
def sample_workspaces() -> list[Workspace]:
    return [
        Workspace(
            id=uuid.uuid4(),
            name="Gartner MQ 2026 - CNAP",
            report_type="Gartner Magic Quadrant",
            description="Primary enterprise evaluation workspace for Cloud-Native Application Platforms (CNAP) 2026.",
            owner_email="analyst-relations-core@google.com",
            co_editors_json=json.dumps(["enterprise-analyst@google.com", "cloud-ar-leads@google.com", "opm-leadership@google.com"]),
            is_default=True,
            current_phase=4,
            last_completed_step="Phase 4B: Automated RAG Ingestion & Initial Technical Drafts",
            last_action_id="generate_rfi_responses",
            context_data_json="{}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Workspace(
            id=uuid.uuid4(),
            name="Forrester Wave - DevSecOps 2026",
            report_type="Forrester Wave",
            description="Multi-tenant collaboration workspace for Forrester Wave DevSecOps evaluation.",
            owner_email="sec-ops-leadership@google.com",
            co_editors_json=json.dumps(["enterprise-analyst@google.com", "cloud-sec-team@google.com"]),
            is_default=False,
            current_phase=3,
            last_completed_step="Phase 3: Stakeholder Kickoff & OPM Alignment Charter",
            last_action_id="kickoff_project",
            context_data_json="{}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Workspace(
            id=uuid.uuid4(),
            name="IDC MarketScape - Universal Platforms 2026",
            report_type="IDC MarketScape",
            description="Restricted analyst response workspace for IDC MarketScape evaluation.",
            owner_email="cloud-pm-execs@google.com",
            co_editors_json=json.dumps(["restricted-idc-leads@google.com"]),
            is_default=False,
            current_phase=1,
            last_completed_step="Phase 1A: Criteria Document Intake",
            last_action_id="open_intake",
            context_data_json="{}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    ]


@pytest.mark.asyncio
async def test_list_seeded_workspaces(sample_workspaces: list[Workspace]) -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = sample_workspaces
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/v1/workspaces/", headers={"X-User-Email": "enterprise-analyst@google.com"})
            assert response.status_code == 200
            workspaces = response.json()
            assert len(workspaces) == 3
            
            by_name = {w["name"]: w for w in workspaces}
            assert "Gartner MQ 2026 - CNAP" in by_name
            assert by_name["Gartner MQ 2026 - CNAP"]["can_edit"] is True
            
            assert "Forrester Wave - DevSecOps 2026" in by_name
            assert by_name["Forrester Wave - DevSecOps 2026"]["can_edit"] is True
            
            # IDC MarketScape should evaluate as Read-Only for enterprise-analyst@google.com
            assert "IDC MarketScape - Universal Platforms 2026" in by_name
            assert by_name["IDC MarketScape - Universal Platforms 2026"]["can_edit"] is False
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_new_workspace() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            payload = {
                "name": "Gartner Magic Quadrant 2026 - Data Analytics",
                "report_type": "Gartner Magic Quadrant",
                "description": "Custom evaluation workspace for BigQuery and Gemini AI in Data Analytics.",
                "co_editors_json": '["data-pm-group@google.com"]',
                "is_default": False
            }
            headers = {"X-User-Email": "lead-opm@google.com"}
            response = await client.post("/api/v1/workspaces/", json=payload, headers=headers)
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == payload["name"]
            assert data["owner_email"] == "lead-opm@google.com"
            assert data["can_edit"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_enterprise_read_only_protection(sample_workspaces: list[Workspace]) -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    # When querying for specific workspace by UUID, return the restricted IDC workspace
    idc_ws = sample_workspaces[2]
    mock_result.scalar_one_or_none.return_value = idc_ws
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Attempt to modify workspace description as read-only user
            update_resp = await client.put(
                f"/api/v1/workspaces/{idc_ws.id}",
                json={"description": "Unauthorized tamper attempt"},
                headers={"X-User-Email": "enterprise-analyst@google.com"}
            )
            assert update_resp.status_code == 403
            assert "Enterprise Read-Only Policy" in update_resp.json()["detail"]

            # Attempt to save a session artifact to the read-only workspace
            art_payload = {
                "title": "Unauthorized Scorecard Save",
                "artifact_type": "scorecard",
                "summary": "Attempting to save scorecard in peer read-only workspace.",
                "content": "### Scorecard content",
                "workspace_id": str(idc_ws.id)
            }
            save_resp = await client.post(
                "/api/v1/artifacts/",
                json=art_payload,
                headers={"X-User-Email": "enterprise-analyst@google.com"}
            )
            assert save_resp.status_code == 403
            assert "Enterprise Read-Only Policy" in save_resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_workspace_scoped_artifact_restoration(sample_workspaces: list[Workspace]) -> None:
    cnap_ws = sample_workspaces[0]
    sample_art = SavedArtifact(
        id=uuid.uuid4(),
        workspace_id=cnap_ws.id,
        title="Scoped CNAP Evaluation Report",
        artifact_type="deep_dive_report",
        summary="Summary of CNAP evaluation.",
        content="# CNAP evaluation",
        metadata_json=json.dumps({"report_name": "Magic Quadrant and Critical Capabilities for Cloud-Native Application Platforms (CNAP), 2026"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_art]
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            restore_resp = await client.post("/api/v1/artifacts/restore", json={"workspace_id": str(cnap_ws.id)})
            assert restore_resp.status_code == 200
            data = restore_resp.json()
            assert "response_text" in data
            assert len(data.get("a2ui_payloads", [])) >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_workspace_step_resumption_chat(sample_workspaces: list[Workspace]) -> None:
    """
    Verifies that loading or switching to a workspace automatically resumes at the last completed step
    and renders the journey coordinates (e.g. Step 4 of 7, 57% Complete).
    """
    cnap_ws = sample_workspaces[0]
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cnap_ws
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/a2ui/chat",
                json={
                    "message": "Switched workspace context",
                    "action_id": "resume_workspace",
                    "workspace_id": str(cnap_ws.id),
                }
            )
            assert response.status_code == 200
            data = response.json()
            # Verify prominent Journey Resumption banner
            assert "Resumed Workspace: **Gartner MQ 2026 - CNAP**" in data["response_text"]
            assert "Current Journey Position:** Step 4 of 7" in data["response_text"]
            assert "Phase 4B: Automated RAG Ingestion & Initial Technical Drafts" in data["response_text"]
            assert "57% Overall Lifecycle Complete" in data["response_text"]
            
            # Verify restored context coordinates
            assert data["restored_context"]["current_phase"] == 4
            assert data["restored_context"]["journey_percentage"] == 57
            assert len(data["a2ui_payloads"]) > 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_workspace_step_progression_service(sample_workspaces: list[Workspace]) -> None:
    """
    Verifies that WorkspaceService.update_workspace_step records forward phase progression.
    """
    from app.services.workspace_service import WorkspaceService
    cnap_ws = sample_workspaces[0]
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cnap_ws
    mock_db.execute.return_value = mock_result

    service = WorkspaceService(db_session=mock_db)
    updated = await service.update_workspace_step(
        workspace_id=cnap_ws.id,
        phase=5,
        step_name="Phase 5A: On-Demand Demo Environments & Sandboxes",
        action_id="open_demo_sandboxes",
        context_data={"demo_env": "provisioned"},
        current_user_email="enterprise-analyst@google.com"
    )
    assert updated is not None
    assert updated.current_phase == 5
    assert updated.last_completed_step == "Phase 5A: On-Demand Demo Environments & Sandboxes"
    assert updated.last_action_id == "open_demo_sandboxes"
    assert "demo_env" in updated.context_data_json
