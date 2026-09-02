"""
Vertex AI Agent Engine Client Service.

Provides a unified client interface for the FastAPI Web / BFF layer to connect,
query, stream, and evaluate responses via Vertex AI Agent Engine (Reasoning Engine).
"""
import asyncio
import logging
import os
import time
from typing import Any, AsyncGenerator, Generator, Optional
from app.core.config import settings

logger = logging.getLogger("conductor.services.agent_engine_client")

_SENTINEL = object()


class AgentEngineClientService:
    """
    Client service for interacting with Vertex AI Agent Engine (Reasoning Engine) resources.
    Manages connection pooling, credential resolution, streaming delegation, and fallback.
    """

    _engine_cache: dict[str, Any] = {}
    _initialized_project: Optional[str] = None

    @classmethod
    def _init_vertexai(cls) -> None:
        """Initializes Vertex AI SDK if not already initialized."""
        target_project = settings.VERTEX_AI_PROJECT
        if cls._initialized_project != target_project:
            try:
                import vertexai
                import google.auth
                creds, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                vertexai.init(
                    project=target_project if target_project != "local-dev-project" else os.environ.get("PROJECT_ID", "riccardo-blog-test-v1"),
                    location="us-central1",
                    credentials=creds,
                )
                cls._initialized_project = target_project
                logger.info(f"Initialized Vertex AI for Agent Engine client: {target_project}")
            except Exception as e:
                logger.warning(f"Vertex AI initialization warning (will retry on demand): {e}")

    @classmethod
    def get_engine(cls, resource_name: Optional[str] = None) -> Any:
        """
        Retrieves or initializes a cached Vertex AI Agent Engine client handle.
        """
        target_resource = resource_name or settings.active_agent_engine_resource
        if target_resource in cls._engine_cache:
            return cls._engine_cache[target_resource]

        cls._init_vertexai()
        try:
            from vertexai import agent_engines
            engine = agent_engines.get(target_resource)
            cls._engine_cache[target_resource] = engine
            logger.info(f"Successfully connected to Vertex AI Reasoning Engine: {target_resource}")
            return engine
        except Exception as e:
            logger.error(f"Failed to fetch Reasoning Engine resource '{target_resource}': {e}")
            raise e

    @classmethod
    def query(
        cls,
        prompt: str,
        workspace_id: str = "ws-default",
        evaluation_type: Optional[str] = None,
        context_data: Optional[dict[str, Any]] = None,
        resource_name: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Synchronously queries the active Vertex AI Reasoning Engine endpoint.
        """
        engine = cls.get_engine(resource_name)
        return engine.query(
            prompt=prompt,
            workspace_id=workspace_id,
            evaluation_type=evaluation_type,
            context_data=context_data or {},
            **kwargs,
        )

    @classmethod
    async def async_query(
        cls,
        prompt: str,
        workspace_id: str = "ws-default",
        evaluation_type: Optional[str] = None,
        context_data: Optional[dict[str, Any]] = None,
        resource_name: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Asynchronously queries the active Vertex AI Reasoning Engine endpoint.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: cls.query(
                prompt=prompt,
                workspace_id=workspace_id,
                evaluation_type=evaluation_type,
                context_data=context_data,
                resource_name=resource_name,
                **kwargs,
            ),
        )

    @classmethod
    def stream_query(
        cls,
        prompt: str,
        workspace_id: str = "ws-default",
        evaluation_type: Optional[str] = None,
        context_data: Optional[dict[str, Any]] = None,
        resource_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Streams intermediate stage updates and the final response from the Reasoning Engine.
        """
        engine = cls.get_engine(resource_name)
        for chunk in engine.stream_query(
            prompt=prompt,
            workspace_id=workspace_id,
            evaluation_type=evaluation_type,
            context_data=context_data or {},
            **kwargs,
        ):
            yield chunk

    @classmethod
    async def async_stream_query(
        cls,
        prompt: str,
        workspace_id: str = "ws-default",
        evaluation_type: Optional[str] = None,
        context_data: Optional[dict[str, Any]] = None,
        resource_name: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Asynchronously yields stream chunks from the active Reasoning Engine.
        """
        loop = asyncio.get_running_loop()
        iterator = iter(cls.stream_query(
            prompt=prompt,
            workspace_id=workspace_id,
            evaluation_type=evaluation_type,
            context_data=context_data,
            resource_name=resource_name,
            **kwargs,
        ))

        while True:
            item = await loop.run_in_executor(None, next, iterator, _SENTINEL)
            if item is _SENTINEL:
                break
            yield item

    @classmethod
    def clear_cache(cls) -> None:
        """Clears cached engine references."""
        cls._engine_cache.clear()
        cls._initialized_project = None
