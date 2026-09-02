from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Core application configuration loaded via Pydantic BaseSettings from environment variables
    and/or Google Secret Manager injected variables.
    """
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/conductor_v2",
        description="PostgreSQL async connection string supporting TCP and Unix sockets (/cloudsql/...)"
    )
    VERTEX_AI_PROJECT: str = Field(
        default="local-dev-project",
        description="Google Cloud Project ID where Vertex AI resources are provisioned"
    )
    VERTEX_AI_MODEL: str = Field(
        default="gemini-3.5-flash",
        description="Vertex AI / Google GenAI model endpoint (e.g., gemini-3.5-flash)"
    )
    SECURITY_SECRET_KEY: str = Field(
        default="super-secret-local-key-change-in-prod",
        description="Secret key injected by Secret Manager for securing sensitive operations"
    )
    CLOUD_SQL_INSTANCE_CONNECTION_NAME: str | None = Field(
        default=None,
        description="Cloud SQL connection string format: PROJECT:REGION:INSTANCE"
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment: development, staging, or production"
    )
    DEFAULT_ENTERPRISE_USER_EMAIL: str = Field(
        default="enterprise-analyst@google.com",
        description="Robust organization group identity fallback for unauthenticated local developer and CI execution"
    )
    AGENT_REGISTRY_ENABLED: bool = Field(
        default=True,
        description="Flag indicating if the service registers in Agent Platform Agent Registry (App Hub)"
    )
    AGENT_FUNCTIONAL_TYPE: str = Field(
        default="agent",
        description="Agent Registry functional type ('agent' or 'mcp-server')"
    )
    AGENT_IDENTITY_TYPE: str = Field(
        default="agent-identity",
        description="Agent Platform identity type ('agent-identity' or 'service-account')"
    )
    AGENT_NAME: str = Field(
        default="conductor-v2",
        description="Canonical Agent identifier in the Agent Registry"
    )
    AGENT_DISPLAY_NAME: str = Field(
        default="Analyst Response Agent (Conductor v2)",
        description="Human-readable display name for the agent in the Agent Registry"
    )
    AGENT_DESCRIPTION: str = Field(
        default="Autonomous multi-agent enterprise response platform for Gartner, Forrester, and IDC analyst evaluations",
        description="Agent description and capability summary for Agent Registry catalog"
    )

    AGENT_RUNTIME: str = Field(
        default="agent_engine",
        description="Execution runtime mode: 'agent_engine' (Vertex AI Reasoning Engine) or 'in_process' (local Gemini)"
    )
    AGENT_ENGINE_DEV_RESOURCE: str = Field(
        default="projects/105792947502/locations/us-central1/reasoningEngines/6138588261280382976",
        description="Vertex AI Reasoning Engine resource path for Dev tier"
    )
    AGENT_ENGINE_STAGING_RESOURCE: str = Field(
        default="projects/105792947502/locations/us-central1/reasoningEngines/99261160976547840",
        description="Vertex AI Reasoning Engine resource path for Staging tier"
    )
    AGENT_ENGINE_PROD_RESOURCE: str = Field(
        default="projects/105792947502/locations/us-central1/reasoningEngines/1252182665583394816",
        description="Vertex AI Reasoning Engine resource path for Production tier"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def active_agent_engine_resource(self) -> str:
        """
        Resolves the active Vertex AI Reasoning Engine resource name for the current runtime environment.
        """
        env = self.ENVIRONMENT.lower()
        if env in ["prod", "production"]:
            return self.AGENT_ENGINE_PROD_RESOURCE
        if env in ["stage", "staging"]:
            return self.AGENT_ENGINE_STAGING_RESOURCE
        return self.AGENT_ENGINE_DEV_RESOURCE

    @property
    def get_async_database_url(self) -> str:
        """
        Returns the formatted async database URL.
        Supports Unix socket paths when running inside Cloud Run with the Cloud SQL Auth Proxy sidecar:
        postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
