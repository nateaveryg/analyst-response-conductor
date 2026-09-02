package services

import (
	"context"

	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/db"
)

type WorkspaceService struct {
	repo *db.Repository
}

func NewWorkspaceService(repo *db.Repository) *WorkspaceService {
	return &WorkspaceService{repo: repo}
}

func (s *WorkspaceService) ListWorkspaces(ctx context.Context, userEmail string) ([]*db.Workspace, error) {
	return s.repo.ListWorkspaces(ctx, userEmail)
}

func (s *WorkspaceService) GetWorkspace(ctx context.Context, id uuid.UUID, userEmail string) (*db.Workspace, error) {
	return s.repo.GetWorkspace(ctx, id, userEmail)
}

func (s *WorkspaceService) CreateWorkspace(ctx context.Context, ws *db.Workspace, ownerEmail string) (*db.Workspace, error) {
	return s.repo.CreateWorkspace(ctx, ws, ownerEmail)
}

func (s *WorkspaceService) UpdateWorkspace(ctx context.Context, id uuid.UUID, updates map[string]interface{}) (*db.Workspace, error) {
	return s.repo.UpdateWorkspace(ctx, id, updates)
}
