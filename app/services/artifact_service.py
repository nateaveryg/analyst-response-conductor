import json
import logging
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core_models import SavedArtifact
from app.schemas.core_schemas import SavedArtifactCreate

logger = logging.getLogger("conductor.artifact_service")


class ArtifactService:
    """
    Service layer responsible for persisting and restoring evaluation artifacts, executive drafts,
    and session context across conversations and application restarts.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session

    async def list_artifacts(self, artifact_type: str | None = None, workspace_id: uuid.UUID | None = None) -> list[SavedArtifact]:
        """
        Retrieves saved artifacts ordered by most recently updated, optionally scoped by workspace or type.
        """
        if self.db is None:
            return []
        try:
            query = select(SavedArtifact).order_by(SavedArtifact.updated_at.desc())
            if artifact_type:
                query = query.where(SavedArtifact.artifact_type == artifact_type)
            if workspace_id:
                query = query.where(SavedArtifact.workspace_id == workspace_id)
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.warning(f"Failed to list artifacts from database: {e}")
            return []

    async def get_artifact(self, artifact_id: uuid.UUID) -> SavedArtifact | None:
        """
        Retrieves a specific saved artifact by UUID.
        """
        if self.db is None:
            return None
        try:
            query = select(SavedArtifact).where(SavedArtifact.id == artifact_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"Failed to get artifact [{artifact_id}] from database: {e}")
            return None

    async def create_artifact(self, payload: SavedArtifactCreate) -> SavedArtifact:
        """
        Creates and persists a new artifact snapshot.
        """
        from datetime import datetime, timezone
        artifact = SavedArtifact(
            id=uuid.uuid4(),
            workspace_id=getattr(payload, "workspace_id", None),
            title=payload.title,
            artifact_type=payload.artifact_type,
            summary=payload.summary,
            content=payload.content,
            metadata_json=payload.metadata_json,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        if self.db is not None:
            try:
                self.db.add(artifact)
                await self.db.commit()
                await self.db.refresh(artifact)
            except Exception as e:
                logger.warning(f"Failed to persist artifact to database: {e}")
        logger.info(f"Persisted saved artifact [{artifact.id}]: {artifact.title} (workspace: {artifact.workspace_id})")
        return artifact

    async def delete_artifact(self, artifact_id: uuid.UUID) -> bool:
        """
        Deletes a saved artifact from storage.
        """
        if self.db is None:
            return False
        try:
            artifact = await self.get_artifact(artifact_id)
            if not artifact:
                return False
            await self.db.delete(artifact)
            await self.db.commit()
            logger.info(f"Deleted saved artifact [{artifact_id}]")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete artifact [{artifact_id}] from database: {e}")
            return False

    async def restore_session_context(self, artifact_id: uuid.UUID | None = None, workspace_id: uuid.UUID | None = None) -> dict[str, Any]:
        """
        Restores saved artifacts and synthesizes actionable context from which the end user can pick up
        the conversation right where they left off and move to the next step of replying to the analyst request.
        """
        if artifact_id:
            artifact = await self.get_artifact(artifact_id)
            artifacts = [artifact] if artifact else []
        else:
            artifacts = await self.list_artifacts(workspace_id=workspace_id)
            if not artifacts and workspace_id:
                # Fallback to globally seeded or general unassigned artifacts if this workspace has no exclusive assets yet
                artifacts = await self.list_artifacts(workspace_id=None)

        if not artifacts:
            return {
                "restored_context": {},
                "response_text": (
                    "⚠️ No saved session artifacts were found in storage. "
                    "You can save your current evaluation, intake form variables, or leadership drafts at any time "
                    "using the **Save Current Session Snapshot** action."
                ),
                "a2ui_payloads": []
            }

        # Merge metadata from all restored artifacts into a consolidated context dictionary
        merged_context: dict[str, Any] = {}
        context_items_summary: list[str] = []
        next_step_recommendation = "Continue reviewing criteria thresholds and proceed with your analyst response."

        for art in artifacts:
            context_items_summary.append(f"* **{art.title}** (`{art.artifact_type}`): {art.summary}")
            if art.metadata_json:
                try:
                    data = json.loads(art.metadata_json)
                    if isinstance(data, dict):
                        merged_context.update(data)
                        if "next_step" in data:
                            next_step_recommendation = str(data["next_step"])
                except Exception as e:
                    logger.warning(f"Could not parse metadata_json for artifact {art.id}: {e}")

        # Build natural language response
        from app.services.a2ui_generator import A2UIGenerator
        report_name = A2UIGenerator.resolve_analyst_report_name(merged_context)
        merged_context["report_name"] = report_name

        response_text = (
            f"### ⚡ Session Context & Artifacts Successfully Restored!{f' ({report_name})' if report_name else ''}\n\n"
            f"We have retrieved **{len(artifacts)} saved asset(s)**{f' for **{report_name}**' if report_name else ''} from storage to pick up right where you left off. "
            f"All associated form variables and evaluation states{f' for **{report_name}**' if report_name else ''} have been reloaded into your active conversation context.\n\n"
            f"**Restored Assets in Scope:**\n" + "\n".join(context_items_summary) + "\n\n"
            f"--- \n\n"
            f"### 🎯 Recommended Next Step for {f'**{report_name}** ' if report_name else ''}Analyst Reply\n"
            f"**{next_step_recommendation}**\n\n"
            f"Use the interactive Quick Actions below or select any restored asset card to proceed directly with your {f'**{report_name}** ' if report_name else ''}analyst response workflow."
        )

        restored_surface = A2UIGenerator.generate_saved_artifacts_surface(artifacts, is_restored_view=True)

        return {
            "restored_context": merged_context,
            "response_text": response_text,
            "a2ui_payloads": [restored_surface]
        }
