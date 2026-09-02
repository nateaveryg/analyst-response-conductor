import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class VectorRetrievalTaskResult(BaseModel):
    """
    Output contract returned by VectorRetrievalSubAgent.
    """
    matched_chunks: list[dict[str, Any]] = Field(default_factory=list, description="List of top ANN cosine similarity vector search chunks")
    total_matches_found: int = Field(default=0, description="Count of historical RFI / doc chunks retrieved")
    query_text: str = Field(..., description="Target search query or question text")
    execution_duration_ms: float = Field(default=0.0, description="Vector search execution timing in milliseconds")


class GroundedSynthesisTaskResult(BaseModel):
    """
    Output contract returned by GroundedSynthesisSubAgent.
    """
    question_id: uuid.UUID | None = Field(default=None, description="UUID of RfiQuestion model")
    section_identifier: str = Field(..., description="Section identifier code (e.g. 3.2.1)")
    question_text: str = Field(..., description="Full text of analyst question")
    draft_response: str = Field(..., description="Purple-wrapped markdown draft answer")
    grounding_confidence_score: float = Field(default=0.0, description="Grounding confidence score between 0.0 and 1.0")
    source_rfi_title: str | None = Field(default=None, description="Title of historical RFI or documentation source")
    execution_duration_ms: float = Field(default=0.0, description="Synthesis execution timing in milliseconds")


class ComplianceAuditTaskResult(BaseModel):
    """
    Output contract returned by ComplianceAuditSubAgent.
    """
    is_compliant: bool = Field(default=True, description="Whether the synthesized answer complies with GA and data residency rules")
    compliance_score: float = Field(default=1.0, description="Compliance rating score between 0.0 and 1.0")
    audit_notes: str = Field(default="Compliant", description="Audit notes or non-GA feature warnings")
    flagged_terms: list[str] = Field(default_factory=list, description="List of flagged non-GA or unapproved product terms")
    execution_duration_ms: float = Field(default=0.0, description="Compliance audit execution timing in milliseconds")


class Phase4BSubAgentTelemetry(BaseModel):
    """
    Aggregated telemetry emitted by Phase 4B sub-agent orchestration.
    """
    retrieval_duration_ms: float = Field(default=0.0)
    synthesis_duration_ms: float = Field(default=0.0)
    compliance_duration_ms: float = Field(default=0.0)
    total_duration_ms: float = Field(default=0.0)
    questions_processed: int = Field(default=0)

    model_config = ConfigDict(from_attributes=True)
