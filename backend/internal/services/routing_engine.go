package services

import (
	"context"

	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/db"
)

type RoutingResult struct {
	QuestionID          uuid.UUID `json:"question_id"`
	SectionIdentifier   string    `json:"section_identifier"`
	AssignedSMEEmail    string    `json:"assigned_sme_email"`
	AssignedSMEName     string    `json:"assigned_sme_name"`
	DomainCategory      string    `json:"domain_category"`
	ConfidenceScore     float64   `json:"confidence_score"`
	FallbackCoordinator bool      `json:"fallback_coordinator"`
}

type RoutingEngine struct {
	repo *db.Repository
}

func NewRoutingEngine(repo *db.Repository) *RoutingEngine {
	return &RoutingEngine{repo: repo}
}

func (e *RoutingEngine) RouteQuestions(ctx context.Context, questionIDs []uuid.UUID) []RoutingResult {
	// Sample domain allocation
	results := []RoutingResult{
		{
			QuestionID:          uuid.New(),
			SectionIdentifier:   "1.1.1",
			AssignedSMEEmail:    "davidjacobs@google.com",
			AssignedSMEName:     "David Jacobs",
			DomainCategory:      "Serverless Runtime & Concurrency",
			ConfidenceScore:     0.96,
			FallbackCoordinator: false,
		},
		{
			QuestionID:          uuid.New(),
			SectionIdentifier:   "2.1.1",
			AssignedSMEEmail:    "nathenharvey@google.com",
			AssignedSMEName:     "Nathen Harvey",
			DomainCategory:      "DevSecOps & DORA Metrics",
			ConfidenceScore:     0.94,
			FallbackCoordinator: false,
		},
		{
			QuestionID:          uuid.New(),
			SectionIdentifier:   "3.1.1",
			AssignedSMEEmail:    "sarahmiller@google.com",
			AssignedSMEName:     "Sarah Miller",
			DomainCategory:      "Software Supply Chain & Security",
			ConfidenceScore:     0.98,
			FallbackCoordinator: false,
		},
	}
	return results
}
