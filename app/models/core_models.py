import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class Product(Base):
    """
    Represents an internal product portfolio capability used to evaluate eligibility
    against analyst RFI criteria thresholds (GA cutoff, revenue, CAGR, customer count).
    """
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    current_ga_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_revenue_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0.0, nullable=False)
    cagr_percentage: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0.0, nullable=False)
    enterprise_customer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Product(name={self.name}, ga_date={self.current_ga_date}, revenue={self.total_revenue_usd})>"


class ReportEvaluation(Base):
    """
    Represents an active analyst evaluation lifecycle instance (e.g., Gartner Magic Quadrant).
    Tracks market boundaries, overall status, and submission milestones.
    """
    __tablename__ = "report_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    report_type: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    market_definition: Mapped[str] = mapped_column(Text, nullable=False)
    submission_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="Evaluating",
        nullable=False,
        comment="Allowed states: Evaluating, In_Progress, Approved, Declined"
    )

    questions: Mapped[list["RfiQuestion"]] = relationship(
        "RfiQuestion",
        back_populates="evaluation",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ReportEvaluation(firm={self.firm_name}, report={self.report_type}, status={self.status})>"


class RfiQuestion(Base):
    """
    Represents an individual question/section parsed from an analyst RFI document.
    Assigned to SMEs and populated with machine-generated RAG drafts wrapped in purple markdown.
    """
    __tablename__ = "rfi_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_evaluations.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    section_identifier: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_sme_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    draft_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    worksheet_tab: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True, comment="e.g., Tab 3: Security & Supply Chain")
    source_rfi_title: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Cited historical RFI report or official document source")
    source_question_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Original historical question matched via vector search")
    source_answer_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Historical approved text leveraged for synthesis")
    grounding_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Algorithmic grounding score between 0.0 and 1.0")
    response_status: Mapped[str] = mapped_column(
        String(50),
        default="Unassigned",
        nullable=False,
        comment="Allowed states: Unassigned, Drafted, SME_Review, Approved"
    )

    evaluation: Mapped["ReportEvaluation"] = relationship(
        "ReportEvaluation",
        back_populates="questions"
    )

    def __repr__(self) -> str:
        return f"<RfiQuestion(section={self.section_identifier}, status={self.response_status})>"


class RagDocumentChunk(Base):
    """
    Unified vector/relational storage table using pgvector inside PostgreSQL.
    Stores historical RFI chunks, release notes, and feature docs along with 768-dimensional embeddings.
    Includes an HNSW index configured with cosine distance for sub-millisecond ANN lookups.
    """
    __tablename__ = "rag_document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_document_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    publication_year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    product_tag: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    ga_status_at_time_of_writing: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="e.g., GA, Pre-GA, Preview, Deprecated"
    )
    chunk_type: Mapped[str] = mapped_column(
        String(50),
        default="Official_Doc",
        nullable=False,
        index=True,
        comment="Official_Doc, Release_Note, or Prior_RFI_Answer"
    )
    source_rfi_title: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Exact prior RFI name and worksheet tab origin")
    original_question_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Original prompt if chunk_type is Prior_RFI_Answer")
    original_answer_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Approved response text from prior RFI")
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(Vector(768), nullable=True)

    __table_args__ = (
        Index(
            "ix_rag_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<RagDocumentChunk(source={self.source_document_id}, tag={self.product_tag}, year={self.publication_year})>"


class Workspace(Base):
    """
    Represents an isolated multi-tenant enterprise workspace for evaluating specific analyst reports
    with designated owner and group co-editor visibility rules.
    """
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    report_type: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    co_editors_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_phase: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_completed_step: Mapped[str] = mapped_column(String(255), default="Phase 1: Document Intake", nullable=False)
    last_action_id: Mapped[str | None] = mapped_column(String(100), default="open_intake", nullable=True)
    context_data_json: Mapped[str | None] = mapped_column(Text, default="{}", nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    artifacts: Mapped[list["SavedArtifact"]] = relationship(
        "SavedArtifact",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Workspace(name={self.name}, owner={self.owner_email}, phase={self.current_phase})>"


class SavedArtifact(Base):
    """
    Represents a saved artifact or session context snapshot produced by the agent or user during an evaluation.
    Allows users to save and restore context across sessions (e.g., when reopening the app or resuming work)
    to continue replying to the analyst's request.
    """
    __tablename__ = "saved_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    workspace: Mapped["Workspace | None"] = relationship(
        "Workspace",
        back_populates="artifacts"
    )

    def __repr__(self) -> str:
        return f"<SavedArtifact(title={self.title}, type={self.artifact_type})>"

