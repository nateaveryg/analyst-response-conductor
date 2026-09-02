import logging
from pathlib import Path
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db
from app.core.observability import setup_observability

logger = logging.getLogger("conductor.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager handling application startup and shutdown events.
    Executes database verification and pgvector extension checks during cold start.
    """
    logger.info(f"Starting up Analyst Response Agent (ARA) in [{settings.ENVIRONMENT}] mode...")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database during cold start: {e}")
        # We catch here so the container can start and report structured health diagnostics if needed
    yield
    logger.info("Shutting down Analyst Response Agent (ARA) service...")


app = FastAPI(
    title="Analyst Response Agent (ARA) - Universal Analyst RFI & Evaluation Orchestrator",
    description=(
        "Universal AI orchestration platform for industry analyst evaluations (Gartner MQ/CC,"
        " Forrester Wave, and IDC MarketScape). Handles criteria parsing, portfolio eligibility"
        " matrices, workback schedules, and deep dive reports. IMPORTANT ONBOARDING REQUEST: End"
        " users must make all documents (Welcome Packets, Demo Guidelines, Questionnaires) and"
        " analyst communications/emails related to criteria available to the agent to ensure"
        " complete evaluation and schedule accuracy."
    ),
    version="2.2.0",
    lifespan=lifespan,
)

# Attach OpenTelemetry and Cloud Logging structured instrumentation
setup_observability(app)

from app.api.v1.a2ui_chat import router as a2ui_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.export import router as export_router
from app.api.v1.inclusion import router as inclusion_router
from app.api.v1.orchestration import router as orchestration_router
from app.api.v1.stream import router as stream_router
from app.api.v1.workspaces import router as workspaces_router

app.include_router(a2ui_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(stream_router, prefix="/api/v1")
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(inclusion_router)
app.include_router(orchestration_router)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse, tags=["A2UI Web Portal"])
async def serve_a2ui_portal() -> FileResponse:
    """
    Serves the web-accessible A2UI executive portal where end users can chat with the agent,
    share document links, and view rendered A2UI declarative components.
    """
    html_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(path=html_path, media_type="text/html")


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health & Diagnostics"])
async def health_check() -> dict[str, str]:
    """
    Basic liveness probe for Cloud Run container checks.
    """
    return {
        "status": "healthy",
        "service": "Analyst Response Agent (ARA)",
        "environment": settings.ENVIRONMENT,
        "version": "2.2.0",
    }


@app.get("/ready", status_code=status.HTTP_200_OK, tags=["Health & Diagnostics"])
async def readiness_check() -> JSONResponse:
    """
    Readiness probe that checks database connection responsiveness.
    """
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "database": "connected"},
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unready", "database": str(e)},
        )


@app.get("/api/v1/agent-card", tags=["Agent Platform & Registry"])
@app.get("/.well-known/agent.json", tags=["Agent Platform & Registry"])
async def get_agent_card() -> dict:
    """
    Exposes the standardized Agent Card metadata for Agent Registry discovery (App Hub)
    and Agent-to-Agent (A2A) protocol orchestration.
    """
    return {
        "name": settings.AGENT_NAME,
        "displayName": settings.AGENT_DISPLAY_NAME,
        "description": settings.AGENT_DESCRIPTION,
        "functionalType": settings.AGENT_FUNCTIONAL_TYPE,
        "identityType": settings.AGENT_IDENTITY_TYPE,
        "version": "2.2.0",
        "runtime": "cloud-run-and-agent-engine" if settings.AGENT_RUNTIME == "agent_engine" else "cloud-run",
        "agentEngineResource": settings.active_agent_engine_resource if settings.AGENT_RUNTIME == "agent_engine" else None,
        "supportedProtocols": ["A2A", "REST", "A2UI", "VERTEX_REASONING_ENGINE"],
        "capabilities": [
            "criteria_parsing_and_intake",
            "scoring_matrix_gap_analysis",
            "workback_schedule_generation",
            "multi_tab_rfi_spreadsheet_ingestion",
            "pgvector_grounded_synthesis",
            "demo_script_and_storyboard_synthesis",
            "executive_governance_and_deficit_waiver"
        ],
        "provider": {
            "name": "Google Cloud",
            "project": settings.VERTEX_AI_PROJECT,
            "region": "us-central1"
        }
    }

