package db

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

type Repository struct {
	db        *Database
	mu        sync.RWMutex
	workspaces map[uuid.UUID]*Workspace
	artifacts  map[uuid.UUID]*SavedArtifact
	products   map[uuid.UUID]*Product
	questions  map[uuid.UUID]*RfiQuestion
}

func NewRepository(database *Database) *Repository {
	repo := &Repository{
		db:         database,
		workspaces: make(map[uuid.UUID]*Workspace),
		artifacts:  make(map[uuid.UUID]*SavedArtifact),
		products:   make(map[uuid.UUID]*Product),
		questions:  make(map[uuid.UUID]*RfiQuestion),
	}
	repo.seedInitialData()
	return repo
}

func (r *Repository) seedInitialData() {
	r.mu.Lock()
	defer r.mu.Unlock()

	defaultWSID := uuid.MustParse("11111111-1111-1111-1111-111111111111")
	now := time.Now().UTC()
	defaultWS := &Workspace{
		ID:                defaultWSID,
		Name:              "Default Enterprise Workspace",
		ReportType:        "DevSecOps Platforms, 2026",
		Description:       ptr("Primary enterprise evaluation workspace for DevSecOps & CNAP MQs"),
		OwnerEmail:        "enterprise-analyst@google.com",
		CoEditorsJSON:     `["pm-lead@google.com", "devops-lead@google.com"]`,
		IsDefault:         true,
		CurrentPhase:      1,
		LastCompletedStep: "Phase 1: Document Intake",
		LastActionID:      ptr("open_intake"),
		ContextDataJSON:   ptr(`{"report_name": "DevSecOps Platforms, 2026"}`),
		CanEdit:           true,
		CreatedAt:         now,
		UpdatedAt:         now,
	}
	r.workspaces[defaultWSID] = defaultWS
}

func ptr[T any](v T) *T {
	return &v
}

// Workspaces
func (r *Repository) ListWorkspaces(ctx context.Context, userEmail string) ([]*Workspace, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var result []*Workspace
	for _, ws := range r.workspaces {
		wsCopy := *ws
		wsCopy.CanEdit = r.evaluateCanEdit(ws, userEmail)
		result = append(result, &wsCopy)
	}
	return result, nil
}

func (r *Repository) GetWorkspace(ctx context.Context, id uuid.UUID, userEmail string) (*Workspace, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	ws, ok := r.workspaces[id]
	if !ok {
		return nil, nil
	}
	wsCopy := *ws
	wsCopy.CanEdit = r.evaluateCanEdit(ws, userEmail)
	return &wsCopy, nil
}

func (r *Repository) CreateWorkspace(ctx context.Context, ws *Workspace, ownerEmail string) (*Workspace, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if ws.ID == uuid.Nil {
		ws.ID = uuid.New()
	}
	now := time.Now().UTC()
	ws.CreatedAt = now
	ws.UpdatedAt = now
	ws.OwnerEmail = ownerEmail
	ws.CanEdit = true
	if ws.CoEditorsJSON == "" {
		ws.CoEditorsJSON = "[]"
	}
	if ws.CurrentPhase == 0 {
		ws.CurrentPhase = 1
	}
	if ws.LastCompletedStep == "" {
		ws.LastCompletedStep = "Phase 1: Document Intake"
	}
	if ws.LastActionID == nil {
		ws.LastActionID = ptr("open_intake")
	}
	if ws.ContextDataJSON == nil {
		ws.ContextDataJSON = ptr("{}")
	}

	r.workspaces[ws.ID] = ws
	wsCopy := *ws
	return &wsCopy, nil
}

func (r *Repository) UpdateWorkspace(ctx context.Context, id uuid.UUID, updates map[string]interface{}) (*Workspace, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	ws, ok := r.workspaces[id]
	if !ok {
		return nil, fmt.Errorf("workspace not found")
	}

	for k, v := range updates {
		switch k {
		case "name":
			if val, ok := v.(string); ok {
				ws.Name = val
			}
		case "report_type":
			if val, ok := v.(string); ok {
				ws.ReportType = val
			}
		case "description":
			if val, ok := v.(string); ok {
				ws.Description = &val
			}
		case "current_phase":
			if val, ok := v.(int); ok {
				ws.CurrentPhase = val
			} else if val, ok := v.(float64); ok {
				ws.CurrentPhase = int(val)
			}
		case "last_completed_step":
			if val, ok := v.(string); ok {
				ws.LastCompletedStep = val
			}
		case "last_action_id":
			if val, ok := v.(string); ok {
				ws.LastActionID = &val
			}
		case "context_data_json":
			if val, ok := v.(string); ok {
				ws.ContextDataJSON = &val
			}
		case "co_editors_json":
			if val, ok := v.(string); ok {
				ws.CoEditorsJSON = val
			}
		}
	}
	ws.UpdatedAt = time.Now().UTC()
	wsCopy := *ws
	return &wsCopy, nil
}

func (r *Repository) evaluateCanEdit(ws *Workspace, userEmail string) bool {
	if userEmail == "" || userEmail == "enterprise-analyst@google.com" {
		return true
	}
	if strings.EqualFold(ws.OwnerEmail, userEmail) {
		return true
	}
	var coEditors []string
	if err := json.Unmarshal([]byte(ws.CoEditorsJSON), &coEditors); err == nil {
		for _, editor := range coEditors {
			if strings.EqualFold(editor, userEmail) {
				return true
			}
		}
	}
	return false
}

// Artifacts
func (r *Repository) ListArtifacts(ctx context.Context, artifactType *string, workspaceID *uuid.UUID) ([]*SavedArtifact, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var result []*SavedArtifact
	for _, art := range r.artifacts {
		if artifactType != nil && *artifactType != "" && art.ArtifactType != *artifactType {
			continue
		}
		if workspaceID != nil && *workspaceID != uuid.Nil {
			if art.WorkspaceID == nil || *art.WorkspaceID != *workspaceID {
				continue
			}
		}
		artCopy := *art
		result = append(result, &artCopy)
	}
	return result, nil
}

func (r *Repository) GetArtifact(ctx context.Context, id uuid.UUID) (*SavedArtifact, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	art, ok := r.artifacts[id]
	if !ok {
		return nil, nil
	}
	artCopy := *art
	return &artCopy, nil
}

func (r *Repository) CreateArtifact(ctx context.Context, art *SavedArtifact) (*SavedArtifact, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if art.ID == uuid.Nil {
		art.ID = uuid.New()
	}
	now := time.Now().UTC()
	art.CreatedAt = now
	art.UpdatedAt = now
	r.artifacts[art.ID] = art
	artCopy := *art
	return &artCopy, nil
}

func (r *Repository) UpdateArtifact(ctx context.Context, id uuid.UUID, updates map[string]interface{}) (*SavedArtifact, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	art, ok := r.artifacts[id]
	if !ok {
		return nil, fmt.Errorf("artifact not found")
	}

	for k, v := range updates {
		switch k {
		case "title":
			if val, ok := v.(string); ok {
				art.Title = val
			}
		case "artifact_type":
			if val, ok := v.(string); ok {
				art.ArtifactType = val
			}
		case "summary":
			if val, ok := v.(string); ok {
				art.Summary = val
			}
		case "content":
			if val, ok := v.(string); ok {
				art.Content = val
			}
		case "metadata_json":
			if val, ok := v.(string); ok {
				art.MetadataJSON = &val
			}
		}
	}
	art.UpdatedAt = time.Now().UTC()
	artCopy := *art
	return &artCopy, nil
}

func (r *Repository) DeleteArtifact(ctx context.Context, id uuid.UUID) bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, ok := r.artifacts[id]; ok {
		delete(r.artifacts, id)
		return true
	}
	return false
}
