package db

import (
	"time"

	"github.com/google/uuid"
	"github.com/pgvector/pgvector-go"
)

type Product struct {
	ID                     uuid.UUID  `json:"id"`
	Name                   string     `json:"name"`
	CurrentGADate          *time.Time `json:"current_ga_date"`
	TotalRevenueUSD        float64    `json:"total_revenue_usd"`
	CAGRPercentage         float64    `json:"cagr_percentage"`
	EnterpriseCustomerCount int       `json:"enterprise_customer_count"`
}

type ReportEvaluation struct {
	ID                 uuid.UUID `json:"id"`
	FirmName           string    `json:"firm_name"`
	ReportType         string    `json:"report_type"`
	MarketDefinition   string    `json:"market_definition"`
	SubmissionDeadline time.Time `json:"submission_deadline"`
	Status             string    `json:"status"` // Evaluating, In_Progress, Approved, Declined
}

type RfiQuestion struct {
	ID                       uuid.UUID `json:"id"`
	EvaluationID             uuid.UUID `json:"evaluation_id"`
	SectionIdentifier        string    `json:"section_identifier"`
	QuestionText             string    `json:"question_text"`
	AssignedSMEID            *string   `json:"assigned_sme_id"`
	DraftResponse            *string   `json:"draft_response"`
	WorksheetTab             *string   `json:"worksheet_tab"`
	SourceRfiTitle           *string   `json:"source_rfi_title"`
	SourceQuestionText       *string   `json:"source_question_text"`
	SourceAnswerText         *string   `json:"source_answer_text"`
	GroundingConfidenceScore *float64  `json:"grounding_confidence_score"`
	ResponseStatus           string    `json:"response_status"` // Unassigned, Drafted, SME_Review, Approved
}

type RagDocumentChunk struct {
	ID                       uuid.UUID        `json:"id"`
	SourceDocumentID         string           `json:"source_document_id"`
	PublicationYear          int              `json:"publication_year"`
	ProductTag               string           `json:"product_tag"`
	GAStatusAtTimeOfWriting  string           `json:"ga_status_at_time_of_writing"`
	ChunkType                string           `json:"chunk_type"` // Official_Doc, Release_Note, Prior_RFI_Answer
	SourceRfiTitle           *string          `json:"source_rfi_title"`
	OriginalQuestionText     *string          `json:"original_question_text"`
	OriginalAnswerText       *string          `json:"original_answer_text"`
	ChunkText                string           `json:"chunk_text"`
	Embedding                *pgvector.Vector `json:"-"`
}

type Workspace struct {
	ID                uuid.UUID `json:"id"`
	Name              string    `json:"name"`
	ReportType        string    `json:"report_type"`
	Description       *string   `json:"description"`
	OwnerEmail        string    `json:"owner_email"`
	CoEditorsJSON     string    `json:"co_editors_json"`
	IsDefault         bool      `json:"is_default"`
	CurrentPhase      int       `json:"current_phase"`
	LastCompletedStep string    `json:"last_completed_step"`
	LastActionID      *string   `json:"last_action_id"`
	ContextDataJSON   *string   `json:"context_data_json"`
	CanEdit           bool      `json:"can_edit"`
	CreatedAt         time.Time `json:"created_at"`
	UpdatedAt         time.Time `json:"updated_at"`
}

type SavedArtifact struct {
	ID           uuid.UUID  `json:"id"`
	WorkspaceID  *uuid.UUID `json:"workspace_id"`
	Title        string     `json:"title"`
	ArtifactType string     `json:"artifact_type"`
	Summary      string     `json:"summary"`
	Content      string     `json:"content"`
	MetadataJSON *string    `json:"metadata_json"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
}
