from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.core_models import RfiQuestion
from app.schemas.orchestration_schemas import (
    TimelineRequest,
    WorkbackTimeline,
    RoutingRequest,
    RoutingResult,
)
from app.services.timeline_engine import TimelineEngine
from app.services.routing_engine import RoutingEngine

router = APIRouter(prefix="/api/v1/orchestration", tags=["Orchestration & Routing"])


async def verify_oidc_token(authorization: Annotated[str | None, Header()] = None) -> str:
    """
    Dependency verifying OIDC Bearer authentication header required for sensitive orchestration triggers.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization Bearer OIDC token header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Extract token
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty OIDC token")
    return token


@router.post(
    "/timeline",
    response_model=WorkbackTimeline,
    status_code=status.HTTP_200_OK,
    summary="Calculate workback schedule backwards from target submission deadline",
)
async def create_workback_timeline(payload: TimelineRequest) -> WorkbackTimeline:
    """
    Generates dynamic project workback schedule with offsets for RAG ingestion, SME curation,
    and executive panel review, shifting backwards around corporate exclusion windows.
    """
    try:
        timeline = TimelineEngine.generate_timeline(
            target_deadline=payload.target_deadline,
            exclusion_windows=payload.exclusion_windows,
        )
        return timeline
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate workback timeline: {str(e)}",
        )


@router.post(
    "/route",
    response_model=list[RoutingResult],
    status_code=status.HTTP_200_OK,
    summary="Route unassigned RfiQuestion instances to subject matter experts (SMEs)",
)
async def route_rfi_questions(
    payload: RoutingRequest,
    db: AsyncSession = Depends(get_db),
    _oidc_token: str = Depends(verify_oidc_token),
) -> list[RoutingResult]:
    """
    Protected endpoint requiring OIDC token authentication.
    Automatically assigns domain SMEs to RFI questions using keyword/semantic matching,
    falling back to the OPM coordinator if confidence threshold is not met.
    """
    stmt = select(RfiQuestion)
    if payload.question_ids:
        stmt = stmt.where(RfiQuestion.id.in_(payload.question_ids))
    elif payload.evaluation_id:
        stmt = stmt.where(RfiQuestion.evaluation_id == payload.evaluation_id)
    else:
        # If neither specified, route all unassigned questions
        stmt = stmt.where(RfiQuestion.response_status == "Unassigned")

    result = await db.execute(stmt)
    questions = result.scalars().all()

    if not questions:
        return []

    routing_engine = RoutingEngine(db_session=db)
    try:
        routing_results = await routing_engine.route_questions(
            questions=list(questions),
            confidence_threshold=payload.confidence_threshold,
        )
        return routing_results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Routing execution failed: {str(e)}",
        )
