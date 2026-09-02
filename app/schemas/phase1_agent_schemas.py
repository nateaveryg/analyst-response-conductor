import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from app.schemas.inclusion_schemas import (
    ParsedRfiCriteria,
    InclusionEvaluationMatrix,
    EvaluationCriterionWeight,
    CriticalCapabilityUseCase,
)


class DocumentParsingTaskResult(BaseModel):
    """Result payload from RfiDocumentParserSubAgent."""
    parsed_layout_blocks: List[str] = Field(default_factory=list)
    extracted_tables: List[dict[str, Any]] = Field(default_factory=list)
    raw_text_cleaned: str = ""
    detected_report_title: Optional[str] = None
    is_multi_tab_spreadsheet: bool = False
    status: str = "success"
    error_message: Optional[str] = None


class CriteriaExtractionTaskResult(BaseModel):
    """Result payload from CriteriaExtractionSubAgent."""
    parsed_criteria: ParsedRfiCriteria
    confidence_score: float = 1.0
    extraction_notes: List[str] = Field(default_factory=list)
    status: str = "success"
    error_message: Optional[str] = None


class PortfolioMappingTaskResult(BaseModel):
    """Result payload from PortfolioMappingSubAgent."""
    matched_products: List[dict[str, Any]] = Field(default_factory=list)
    portfolio_ga_coverage_percentage: float = 0.0
    mandatory_features_met_count: int = 0
    mandatory_features_total_count: int = 0
    capability_attributions: List[dict[str, Any]] = Field(default_factory=list)
    status: str = "success"
    error_message: Optional[str] = None


class GoNoGoDecisionTaskResult(BaseModel):
    """Result payload from GovernanceGoNoGoSubAgent."""
    recommendation: str = "Proceed_With_Participation"
    risk_level: str = "Low"
    justification_summary: str = ""
    financial_thresholds_met: bool = True
    ga_cutoff_met: bool = True
    deficit_waivers_required: List[str] = Field(default_factory=list)
    status: str = "success"
    error_message: Optional[str] = None


class Phase1SubAgentTelemetry(BaseModel):
    """Execution progress and status telemetry for Phase 1 Sub-Agents."""
    agent_name: str
    stage: str
    status: str = "completed"  # pending, in_progress, completed, warning, failed
    duration_ms: float = 0.0
    summary_message: str = ""
