from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.inclusion_schemas import ParsedRfiCriteria, InclusionEvaluationMatrix
from app.services.inclusion_analyzer import InclusionAnalyzer

router = APIRouter(prefix="/api/v1/inclusion", tags=["Inclusion Analyzer"])


class RfiAnalyzeRequest(BaseModel):
    raw_rfi_text: str = Field(..., description="Raw unformatted text extracted from analyst RFI documentation")


@router.post(
    "/analyze",
    response_model=InclusionEvaluationMatrix,
    status_code=status.HTTP_200_OK,
    summary="Parse RFI text and evaluate portfolio eligibility against criteria thresholds",
)
async def analyze_rfi_inclusion(
    payload: RfiAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> InclusionEvaluationMatrix:
    """
    Accepts raw analyst RFI text, extracts inclusion boundaries using Vertex AI LLMs,
    and checks all product portfolio capabilities against GA cutoff, revenue, CAGR,
    and enterprise customer count criteria.
    
    IMPORTANT ONBOARDING REQUEST: Please ensure all analyst documents (Welcome Packets,
    Vendor Demonstration Guidelines, RFI attachments) and related email communications
    are made available to the agent for complete evaluation.
    """
    analyzer = InclusionAnalyzer(db_session=db)
    try:
        parsed_criteria: ParsedRfiCriteria = await analyzer.parse_rfi_criteria(payload.raw_rfi_text)
        evaluation_matrix: InclusionEvaluationMatrix = await analyzer.evaluate_portfolio_eligibility(parsed_criteria)
        return evaluation_matrix
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inclusion analysis execution failed: {str(e)}",
        )
