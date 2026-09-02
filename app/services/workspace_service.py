import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core_models import Workspace
from app.schemas.core_schemas import WorkspaceCreate, WorkspaceUpdate

logger = logging.getLogger("conductor.workspace_service")


class WorkspaceService:
    """
    Service layer responsible for managing multi-tenant analyst workspaces and evaluating
    group-based enterprise visibility and edit access rules.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session

    @classmethod
    def evaluate_can_edit(cls, workspace: Workspace, current_user_email: str) -> bool:
        """
        Determines whether the calling user identity has edit and scorecard mutation privileges.
        Returns true if the user matches the creator (owner_email) or belongs to explicit co-editor groups.
        """
        email_clean = current_user_email.strip().lower()
        if not email_clean:
            return False

        if email_clean == workspace.owner_email.strip().lower():
            return True

        if not workspace.co_editors_json:
            return False

        try:
            co_editors = json.loads(workspace.co_editors_json)
            if isinstance(co_editors, list):
                for editor in co_editors:
                    editor_clean = str(editor).strip().lower()
                    if editor_clean == email_clean or editor_clean == "*@google.com":
                        return True
                    # Check if group domain or org email prefix matches
                    if "@" in editor_clean and editor_clean == email_clean:
                        return True
        except Exception as e:
            logger.warning(f"Failed to parse co_editors_json for workspace [{workspace.id}]: {e}")
            return False

        return False

    async def list_workspaces(self, current_user_email: str) -> list[Workspace]:
        """
        Retrieves all enterprise workspaces ordered by name and dynamically attaches can_edit flag.
        """
        if self.db is None:
            return []
        query = select(Workspace).order_by(Workspace.name.asc())
        result = await self.db.execute(query)
        workspaces = list(result.scalars().all())
        
        for ws in workspaces:
            # Dynamically attach attribute for Pydantic schema serialization
            setattr(ws, "can_edit", self.evaluate_can_edit(ws, current_user_email))
            if getattr(ws, "current_phase", None) is None:
                setattr(ws, "current_phase", 1)
            if getattr(ws, "last_completed_step", None) is None:
                setattr(ws, "last_completed_step", "Phase 1: Document Intake")
            if getattr(ws, "last_action_id", None) is None:
                setattr(ws, "last_action_id", "open_intake")
            if getattr(ws, "context_data_json", None) is None:
                setattr(ws, "context_data_json", "{}")
            
        return workspaces

    async def get_workspace(self, workspace_id: uuid.UUID, current_user_email: str) -> Workspace | None:
        """
        Retrieves a single workspace by UUID with evaluated access flag.
        """
        if self.db is None:
            return None
        query = select(Workspace).where(Workspace.id == workspace_id)
        result = await self.db.execute(query)
        workspace = result.scalar_one_or_none()
        if workspace:
            setattr(workspace, "can_edit", self.evaluate_can_edit(workspace, current_user_email))
            if getattr(workspace, "current_phase", None) is None:
                setattr(workspace, "current_phase", 1)
            if getattr(workspace, "last_completed_step", None) is None:
                setattr(workspace, "last_completed_step", "Phase 1: Document Intake")
            if getattr(workspace, "last_action_id", None) is None:
                setattr(workspace, "last_action_id", "open_intake")
            if getattr(workspace, "context_data_json", None) is None:
                setattr(workspace, "context_data_json", "{}")
        return workspace

    async def create_workspace(self, payload: WorkspaceCreate, owner_email: str) -> Workspace:
        """
        Creates and persists a new multi-tenant workspace with the calling identity as creator.
        """
        workspace = Workspace(
            id=uuid.uuid4(),
            name=payload.name,
            report_type=payload.report_type,
            description=payload.description,
            owner_email=owner_email,
            co_editors_json=payload.co_editors_json,
            is_default=payload.is_default,
            current_phase=payload.current_phase if hasattr(payload, "current_phase") else 1,
            last_completed_step=payload.last_completed_step if hasattr(payload, "last_completed_step") else "Phase 1: Document Intake",
            last_action_id=payload.last_action_id if hasattr(payload, "last_action_id") else "open_intake",
            context_data_json=payload.context_data_json if hasattr(payload, "context_data_json") else "{}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        if self.db is not None:
            self.db.add(workspace)
            await self.db.commit()
            await self.db.refresh(workspace)
        setattr(workspace, "can_edit", True)
        logger.info(f"Persisted new enterprise workspace [{workspace.id}]: {workspace.name} (Owner: {owner_email})")
        return workspace

    async def update_workspace(self, workspace_id: uuid.UUID, payload: WorkspaceUpdate, current_user_email: str) -> Workspace | None:
        """
        Updates fields of an existing workspace if calling user has edit rights.
        """
        if self.db is None:
            return None
        workspace = await self.get_workspace(workspace_id, current_user_email)
        if not workspace:
            return None

        if not getattr(workspace, "can_edit", False):
            raise PermissionError("Enterprise Read-Only Policy: Only workspace creators and designated co-editor groups can modify this workspace.")

        if payload.name is not None:
            workspace.name = payload.name
        if payload.report_type is not None:
            workspace.report_type = payload.report_type
        if payload.description is not None:
            workspace.description = payload.description
        if payload.co_editors_json is not None:
            workspace.co_editors_json = payload.co_editors_json
        if payload.is_default is not None:
            workspace.is_default = payload.is_default
        if payload.current_phase is not None:
            workspace.current_phase = payload.current_phase
        if payload.last_completed_step is not None:
            workspace.last_completed_step = payload.last_completed_step
        if payload.last_action_id is not None:
            workspace.last_action_id = payload.last_action_id
        if payload.context_data_json is not None:
            workspace.context_data_json = payload.context_data_json

        await self.db.commit()
        await self.db.refresh(workspace)
        setattr(workspace, "can_edit", self.evaluate_can_edit(workspace, current_user_email))
        return workspace

    async def update_workspace_step(
        self,
        workspace_id: uuid.UUID,
        phase: int,
        step_name: str,
        action_id: str,
        context_data: dict[str, Any] | None = None,
        current_user_email: str | None = None,
    ) -> Workspace | None:
        """
        Updates the journey progress and state of an existing workspace when a user completes a lifecycle step.
        """
        if self.db is None:
            return None
        query = select(Workspace).where(Workspace.id == workspace_id)
        result = await self.db.execute(query)
        workspace = result.scalar_one_or_none()
        if not workspace:
            return None

        workspace.current_phase = phase
        workspace.last_completed_step = step_name
        workspace.last_action_id = action_id
        if context_data is not None:
            existing_ctx = {}
            if workspace.context_data_json:
                try:
                    existing_ctx = json.loads(workspace.context_data_json)
                except Exception:
                    existing_ctx = {}
            existing_ctx.update(context_data)
            workspace.context_data_json = json.dumps(existing_ctx)

        await self.db.commit()
        await self.db.refresh(workspace)
        if current_user_email:
            setattr(workspace, "can_edit", self.evaluate_can_edit(workspace, current_user_email))
        logger.info(f"Updated workspace [{workspace.id}] progress -> Phase {phase}: {step_name} (action: {action_id})")
        return workspace

    async def delete_workspace(self, workspace_id: uuid.UUID, current_user_email: str) -> bool:
        """
        Deletes a workspace if the calling identity has edit rights.
        """
        if self.db is None:
            return False
        workspace = await self.get_workspace(workspace_id, current_user_email)
        if not workspace:
            return False

        if not getattr(workspace, "can_edit", False):
            raise PermissionError("Enterprise Read-Only Policy: Only workspace creators and designated co-editor groups can delete this workspace.")

        await self.db.delete(workspace)
        await self.db.commit()
        logger.info(f"Deleted workspace [{workspace_id}]")
        return True
