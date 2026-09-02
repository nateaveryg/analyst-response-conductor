import json
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.core_models import SavedArtifact


@pytest.fixture
def sample_saved_artifact() -> SavedArtifact:
    from datetime import datetime, timezone
    return SavedArtifact(
        id=uuid.uuid4(),
        title="Gartner MQ 2026 Scorecard Snapshot",
        artifact_type="scorecard",
        summary="Portfolio qualification scorecard evaluating GAAP revenue ($25M floor).",
        content="### Portfolio Eligibility Scorecard Results\n1. Gemini Code Assist Enterprise: Qualified.",
        metadata_json=json.dumps({"analyst_notes": "GAAP revenue >= $25M with 40% CAGR."}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_list_artifacts_endpoint(sample_saved_artifact: SavedArtifact) -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_saved_artifact]
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/artifacts/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Gartner MQ 2026 Scorecard Snapshot"
        assert data[0]["artifact_type"] == "scorecard"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_artifact_endpoint() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "title": "New Executive Email Draft",
        "artifact_type": "email_draft",
        "summary": "Draft email to pm-leadership@.",
        "content": "To: pm-leadership@...",
        "metadata_json": json.dumps({"next_step": "Send email"})
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/artifacts/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Executive Email Draft"
        assert data["artifact_type"] == "email_draft"
        assert mock_db.add.called
        assert mock_db.commit.called

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_restore_session_context_endpoint(sample_saved_artifact: SavedArtifact) -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_saved_artifact]
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/artifacts/restore", json={})
        assert response.status_code == 200
        data = response.json()
        assert "Session Context & Artifacts Successfully Restored" in data["response_text"]
        assert "GAAP revenue >= $25M with 40% CAGR." in data["restored_context"]["analyst_notes"]
        assert len(data["a2ui_payloads"]) > 0

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_a2ui_chat_open_saved_artifacts(sample_saved_artifact: SavedArtifact) -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_saved_artifact]
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "view saved artifacts", "action_id": "open_saved_artifacts"}
        )
        data = response.json()
        assert "Right-Side Saved Artifacts Modal" in data["response_text"]
        assert "Gartner MQ 2026 Scorecard Snapshot" in data["a2ui_payloads"][0]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_a2ui_chat_save_current_context() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={
                "message": "save current context",
                "action_id": "save_current_context",
                "context_data": {"analyst_notes": "Important note", "welcome_packet_url": "http://doc.url"}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "Session Context Successfully Saved" in data["response_text"]
        assert mock_db.add.called
        assert mock_db.commit.called

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_artifact_endpoint(sample_saved_artifact: SavedArtifact) -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_saved_artifact
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/artifacts/{sample_saved_artifact.id}")
        assert response.status_code == 204
        assert mock_db.delete.called
        assert mock_db.commit.called

    app.dependency_overrides.clear()
