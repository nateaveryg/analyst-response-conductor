import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.core_schemas import (
    SavedArtifactCreate,
    SavedArtifactRead,
    SavedArtifactUpdate,
)
from app.services.artifact_service import ArtifactService
from app.services.workspace_service import WorkspaceService
from app.api.v1.workspaces import get_current_user_email

router = APIRouter(prefix="/artifacts", tags=["Saved Session Artifacts & Context Restoration"])


class RestoreRequest(BaseModel):
    """
    Optional payload when requesting session context restoration.
    """
    artifact_id: uuid.UUID | None = Field(default=None, description="Optional UUID of a specific artifact to restore")
    workspace_id: uuid.UUID | None = Field(default=None, description="Optional UUID of workspace to filter restored context")


@router.get(
    "/",
    response_model=list[SavedArtifactRead],
    status_code=status.HTTP_200_OK,
    summary="List all saved artifacts and session snapshots"
)
async def list_artifacts(
    artifact_type: str | None = None,
    workspace_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db)
) -> list[SavedArtifactRead]:
    """
    Retrieves all saved artifacts across conversations, optionally filtered by artifact_type and workspace_id.
    """
    service = ArtifactService(db_session=db)
    items = await service.list_artifacts(artifact_type=artifact_type, workspace_id=workspace_id)
    return [
        SavedArtifactRead(
            id=item.id,
            workspace_id=item.workspace_id,
            title=item.title,
            artifact_type=item.artifact_type,
            summary=item.summary,
            content=item.content,
            metadata_json=item.metadata_json,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


@router.post(
    "/",
    response_model=SavedArtifactRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new session artifact snapshot"
)
async def create_artifact(
    payload: SavedArtifactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user_email),
) -> SavedArtifactRead:
    """
    Persists a new artifact snapshot (scorecard, draft, or report) so it can be restored in future sessions.
    Enforces enterprise read-only protection if a workspace_id is specified.
    """
    if payload.workspace_id:
        ws_service = WorkspaceService(db_session=db)
        ws = await ws_service.get_workspace(payload.workspace_id, current_user_email=current_user)
        if ws and not getattr(ws, "can_edit", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enterprise Read-Only Policy: You cannot save session artifacts to a read-only workspace."
            )
    service = ArtifactService(db_session=db)
    art = await service.create_artifact(payload)
    return SavedArtifactRead(
        id=art.id,
        workspace_id=art.workspace_id,
        title=art.title,
        artifact_type=art.artifact_type,
        summary=art.summary,
        content=art.content,
        metadata_json=art.metadata_json,
        created_at=art.created_at,
        updated_at=art.updated_at,
    )


@router.get(
    "/{artifact_id}",
    response_model=SavedArtifactRead,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific saved artifact"
)
async def get_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> SavedArtifactRead:
    """
    Retrieves the content, summary, and metadata of a specific saved artifact.
    """
    service = ArtifactService(db_session=db)
    artifact = await service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact [{artifact_id}] not found")
    return SavedArtifactRead(
        id=artifact.id,
        workspace_id=artifact.workspace_id,
        title=artifact.title,
        artifact_type=artifact.artifact_type,
        summary=artifact.summary,
        content=artifact.content,
        metadata_json=artifact.metadata_json,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.put(
    "/{artifact_id}",
    response_model=SavedArtifactRead,
    status_code=status.HTTP_200_OK,
    summary="Update an existing saved artifact"
)
async def update_artifact(
    artifact_id: uuid.UUID,
    payload: SavedArtifactUpdate,
    db: AsyncSession = Depends(get_db)
) -> SavedArtifactRead:
    """
    Updates fields (title, summary, content, or metadata_json) of an existing saved artifact.
    """
    service = ArtifactService(db_session=db)
    artifact = await service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact [{artifact_id}] not found")

    if payload.title is not None:
        artifact.title = payload.title
    if payload.artifact_type is not None:
        artifact.artifact_type = payload.artifact_type
    if payload.summary is not None:
        artifact.summary = payload.summary
    if payload.content is not None:
        artifact.content = payload.content
    if payload.metadata_json is not None:
        artifact.metadata_json = payload.metadata_json

    if db is not None:
        await db.commit()
        await db.refresh(artifact)
    return SavedArtifactRead(
        id=artifact.id,
        workspace_id=artifact.workspace_id,
        title=artifact.title,
        artifact_type=artifact.artifact_type,
        summary=artifact.summary,
        content=artifact.content,
        metadata_json=artifact.metadata_json,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.delete(
    "/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved artifact"
)
async def delete_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Deletes a saved artifact from storage.
    """
    service = ArtifactService(db_session=db)
    success = await service.delete_artifact(artifact_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact [{artifact_id}] not found")


@router.post(
    "/restore",
    status_code=status.HTTP_200_OK,
    summary="Restore session context and get next-step guidance from saved artifacts"
)
async def restore_session_context(
    payload: RestoreRequest | None = None,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Restores saved artifacts into active conversation context and generates A2UI components
    with next-step guidance for replying to the analyst.
    """
    service = ArtifactService(db_session=db)
    artifact_id = payload.artifact_id if payload else None
    workspace_id = payload.workspace_id if payload else None
    return await service.restore_session_context(artifact_id=artifact_id, workspace_id=workspace_id)

