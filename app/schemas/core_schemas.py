import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


# --- Product Schemas ---
class ProductBase(BaseModel):
    name: str = Field(..., description="Unique product capability name")
    current_ga_date: date | None = Field(default=None, description="General availability date")
    total_revenue_usd: Decimal = Field(default=Decimal("0.0"), description="Annualized revenue in USD")
    cagr_percentage: Decimal = Field(default=Decimal("0.0"), description="Compound Annual Growth Rate percentage")
    enterprise_customer_count: int = Field(default=0, description="Count of enterprise paying customers")


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# --- ReportEvaluation Schemas ---
class ReportEvaluationBase(BaseModel):
    firm_name: str = Field(..., description="Analyst firm name (e.g. Gartner)")
    report_type: str = Field(..., description="Report category (e.g. Magic Quadrant)")
    market_definition: str = Field(..., description="Scope and boundaries of the evaluated market")
    submission_deadline: datetime = Field(..., description="External analyst submission target date")
    status: Literal["Evaluating", "In_Progress", "Approved", "Declined"] = Field(
        default="Evaluating", description="Current lifecycle evaluation status"
    )


class ReportEvaluationCreate(ReportEvaluationBase):
    pass


class ReportEvaluationRead(ReportEvaluationBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# --- RfiQuestion Schemas ---
class RfiQuestionBase(BaseModel):
    section_identifier: str = Field(..., description="RFI document section code (e.g. 2.1.4)")
    question_text: str = Field(..., description="Full text of the analyst question")
    assigned_sme_id: str | None = Field(default=None, description="Assigned Subject Matter Expert email")
    draft_response: str | None = Field(default=None, description="Draft response text wrapped in purple markdown")
    worksheet_tab: str | None = Field(default=None, description="Parent worksheet tab header")
    source_rfi_title: str | None = Field(default=None, description="Historical RFI source title")
    source_question_text: str | None = Field(default=None, description="Matched historical question text")
    source_answer_text: str | None = Field(default=None, description="Leveraged approved answer text")
    grounding_confidence_score: float | None = Field(default=None, description="Grounding similarity percentage")
    response_status: Literal["Unassigned", "Drafted", "SME_Review", "Approved"] = Field(
        default="Unassigned", description="Workflow state of this answer"
    )


class RfiQuestionCreate(RfiQuestionBase):
    evaluation_id: uuid.UUID


class RfiQuestionUpdate(BaseModel):
    assigned_sme_id: str | None = None
    draft_response: str | None = None
    response_status: Literal["Unassigned", "Drafted", "SME_Review", "Approved"] | None = None
    worksheet_tab: str | None = None
    source_rfi_title: str | None = None
    source_question_text: str | None = None
    source_answer_text: str | None = None
    grounding_confidence_score: float | None = None


class RfiQuestionRead(RfiQuestionBase):
    id: uuid.UUID
    evaluation_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# --- RagDocumentChunk Schemas ---
class RagDocumentChunkBase(BaseModel):
    source_document_id: str = Field(..., description="Origin document filename or uri")
    publication_year: int = Field(..., description="Year the source document was published")
    product_tag: str = Field(..., description="Associated product or category identifier")
    ga_status_at_time_of_writing: str = Field(..., description="Lifecycle status at writing time (e.g. GA, Pre-GA)")
    chunk_type: str = Field(default="Official_Doc", description="Official_Doc, Release_Note, or Prior_RFI_Answer")
    source_rfi_title: str | None = Field(default=None, description="Prior RFI report and tab origin")
    original_question_text: str | None = Field(default=None, description="Original question prompt")
    original_answer_text: str | None = Field(default=None, description="Approved response text")
    chunk_text: str = Field(..., description="The ~500 character text segment with 50-char overlap")


class RagDocumentChunkCreate(RagDocumentChunkBase):
    embedding: list[float] | None = Field(default=None, description="768-dimensional vector embedding")


class RagDocumentChunkRead(RagDocumentChunkBase):
    id: uuid.UUID
    # Note: we omit embedding from default read schema for response size optimization unless explicitly requested

    model_config = ConfigDict(from_attributes=True)


# --- SavedArtifact Schemas ---
class SavedArtifactBase(BaseModel):
    title: str = Field(..., description="Descriptive title of the saved artifact")
    artifact_type: str = Field(..., description="Type of artifact (e.g., scorecard, email_draft, deep_dive_report, intake_context)")
    summary: str = Field(..., description="Summary of the artifact and how it assists with the analyst response")
    content: str = Field(..., description="Raw content of the artifact or markdown output")
    metadata_json: str | None = Field(default=None, description="Serialized JSON context data or bound form variables")
    workspace_id: uuid.UUID | None = Field(default=None, description="Optional UUID of associated workspace for tenancy scoping")


class SavedArtifactCreate(SavedArtifactBase):
    pass


class SavedArtifactUpdate(BaseModel):
    title: str | None = None
    artifact_type: str | None = None
    summary: str | None = None
    content: str | None = None
    metadata_json: str | None = None
    workspace_id: uuid.UUID | None = None


class SavedArtifactRead(SavedArtifactBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Workspace Schemas ---
class WorkspaceBase(BaseModel):
    name: str = Field(..., description="Unique enterprise workspace name")
    report_type: str = Field(..., description="Target analyst report type (e.g., Gartner Magic Quadrant)")
    description: str | None = Field(default=None, description="Detailed description of the evaluation scope")
    co_editors_json: str = Field(default="[]", description="JSON array of group emails with edit permissions")
    is_default: bool = Field(default=False, description="Whether this is the default initial workspace")
    current_phase: int | None = Field(default=1, description="Active 1-to-7 lifecycle phase number")
    last_completed_step: str | None = Field(default="Phase 1: Document Intake", description="Name of the last completed or active step in the journey")
    last_action_id: str | None = Field(default="open_intake", description="Action ID corresponding to the current/last step")
    context_data_json: str | None = Field(default="{}", description="Serialized JSON context data for restoring step state")


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    report_type: str | None = None
    description: str | None = None
    co_editors_json: str | None = None
    is_default: bool | None = None
    current_phase: int | None = None
    last_completed_step: str | None = None
    last_action_id: str | None = None
    context_data_json: str | None = None


class WorkspaceRead(WorkspaceBase):
    id: uuid.UUID
    owner_email: str
    can_edit: bool = Field(default=True, description="Evaluated edit authorization flag for calling user identity")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


