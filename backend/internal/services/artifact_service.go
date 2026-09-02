package services

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/db"
)

type ArtifactService struct {
	repo          *db.Repository
	a2uiGenerator *A2UIGenerator
}

func NewArtifactService(repo *db.Repository, a2ui *A2UIGenerator) *ArtifactService {
	return &ArtifactService{
		repo:          repo,
		a2uiGenerator: a2ui,
	}
}

func (s *ArtifactService) ListArtifacts(ctx context.Context, artifactType *string, workspaceID *uuid.UUID) ([]*db.SavedArtifact, error) {
	return s.repo.ListArtifacts(ctx, artifactType, workspaceID)
}

func (s *ArtifactService) GetArtifact(ctx context.Context, id uuid.UUID) (*db.SavedArtifact, error) {
	return s.repo.GetArtifact(ctx, id)
}

func (s *ArtifactService) CreateArtifact(ctx context.Context, art *db.SavedArtifact) (*db.SavedArtifact, error) {
	return s.repo.CreateArtifact(ctx, art)
}

func (s *ArtifactService) UpdateArtifact(ctx context.Context, id uuid.UUID, updates map[string]interface{}) (*db.SavedArtifact, error) {
	return s.repo.UpdateArtifact(ctx, id, updates)
}

func (s *ArtifactService) DeleteArtifact(ctx context.Context, id uuid.UUID) bool {
	return s.repo.DeleteArtifact(ctx, id)
}

func (s *ArtifactService) RestoreSessionContext(ctx context.Context, artifactID *uuid.UUID, workspaceID *uuid.UUID) (map[string]interface{}, error) {
	artifacts, err := s.repo.ListArtifacts(ctx, nil, workspaceID)
	if err != nil {
		return nil, err
	}

	restoredData := make(map[string]interface{})
	for _, art := range artifacts {
		if art.MetadataJSON != nil && *art.MetadataJSON != "" {
			var meta map[string]interface{}
			if err := json.Unmarshal([]byte(*art.MetadataJSON), &meta); err == nil {
				for k, v := range meta {
					restoredData[k] = v
				}
			}
		}
	}

	surface := s.a2uiGenerator.GeneratePhase1IntakeSurface("DevSecOps Platforms, 2026")
	msg := fmt.Sprintf("Restored session state from %d saved artifact(s). Ready to resume analyst evaluation.", len(artifacts))

	return map[string]interface{}{
		"status":           "restored",
		"message":          msg,
		"response_text":    msg,
		"restored_context": restoredData,
		"a2ui_payloads":    []string{surface},
	}, nil
}
