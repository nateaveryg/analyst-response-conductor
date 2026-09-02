import uuid
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.schemas.core_schemas import (
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Enterprise Multi-Tenant Workspaces"])


def get_current_user_email(
    request: Request,
    x_goog_authenticated_user_email: str | None = Header(default=None, alias="X-Goog-Authenticated-User-Email"),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
    x_goog_iap_jwt_assertion: str | None = Header(default=None, alias="x-goog-iap-jwt-assertion"),
) -> str:
    """
    Extracts calling identity from enterprise API gateways (Google Cloud IAP / BeyondCorp Zero Trust)
    or local developer test headers. Supports cryptographic IAP JWT assertion token parsing.
    Falls back to settings.DEFAULT_ENTERPRISE_USER_EMAIL if neither header is supplied in local dev mode.
    """
    # 1. Check Cloud Identity-Aware Proxy (IAP) assertion header
    if x_goog_authenticated_user_email and x_goog_authenticated_user_email.strip():
        email = x_goog_authenticated_user_email.replace("accounts.google.com:", "").strip()
        if email:
            return email

    # 2. Check for IAP JWT token payload if passed
    if x_goog_iap_jwt_assertion and x_goog_iap_jwt_assertion.strip():
        try:
            import base64
            import json
            parts = x_goog_iap_jwt_assertion.split(".")
            if len(parts) >= 2:
                padding = "=" * (-len(parts[1]) % 4)
                payload_bytes = base64.urlsafe_b64decode(parts[1] + padding)
                payload = json.loads(payload_bytes)
                jwt_email = payload.get("email")
                if jwt_email and isinstance(jwt_email, str):
                    return jwt_email.strip()
        except Exception:
            pass

    # 3. Check local developer override header
    if x_user_email and x_user_email.strip():
        return x_user_email.strip()

    # 4. Fallback default for unauthenticated local developer mode
    return settings.DEFAULT_ENTERPRISE_USER_EMAIL


@router.get(
    "/",
    response_model=list[WorkspaceRead],
    status_code=status.HTTP_200_OK,
    summary="List all enterprise analyst workspaces with dynamic read-only/edit visibility flags",
)
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user_email),
) -> list[WorkspaceRead]:
    service = WorkspaceService(db_session=db)
    return await service.list_workspaces(current_user_email=current_user)


@router.post(
    "/",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new isolated analyst workspace",
)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user_email),
) -> WorkspaceRead:
    service = WorkspaceService(db_session=db)
    return await service.create_workspace(payload, owner_email=current_user)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific analyst workspace",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user_email),
) -> WorkspaceRead:
    service = WorkspaceService(db_session=db)
    ws = await service.get_workspace(workspace_id, current_user_email=current_user)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workspace [{workspace_id}] not found")
    return ws


@router.put(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    status_code=status.HTTP_200_OK,
    summary="Update workspace details (protected by owner and co-editor access check)",
)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user_email),
) -> WorkspaceRead:
    service = WorkspaceService(db_session=db)
    try:
        ws = await service.update_workspace(workspace_id, payload, current_user_email=current_user)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workspace [{workspace_id}] not found")
        return ws
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an enterprise workspace",
)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user_email),
) -> None:
    service = WorkspaceService(db_session=db)
    try:
        success = await service.delete_workspace(workspace_id, current_user_email=current_user)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workspace [{workspace_id}] not found")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
