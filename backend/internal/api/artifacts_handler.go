package api

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/db"
	"github.com/google/rficonductorv2/backend/internal/services"
)

type ArtifactsHandler struct {
	svc          *services.ArtifactService
	workspaceSvc *services.WorkspaceService
}

func NewArtifactsHandler(svc *services.ArtifactService, wsSvc *services.WorkspaceService) *ArtifactsHandler {
	return &ArtifactsHandler{
		svc:          svc,
		workspaceSvc: wsSvc,
	}
}

func (h *ArtifactsHandler) ListArtifacts(c *gin.Context) {
	artType := c.Query("artifact_type")
	var artTypePtr *string
	if artType != "" {
		artTypePtr = &artType
	}

	wsIDStr := c.Query("workspace_id")
	var wsIDPtr *uuid.UUID
	if wsIDStr != "" {
		if u, err := uuid.Parse(wsIDStr); err == nil {
			wsIDPtr = &u
		}
	}

	artifacts, err := h.svc.ListArtifacts(c.Request.Context(), artTypePtr, wsIDPtr)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	if artifacts == nil {
		artifacts = []*db.SavedArtifact{}
	}
	c.JSON(http.StatusOK, artifacts)
}

func (h *ArtifactsHandler) CreateArtifact(c *gin.Context) {
	userEmail := c.GetString(CtxUserEmailKey)
	var raw map[string]interface{}
	if err := c.ShouldBindJSON(&raw); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"body"}, "msg": "Invalid JSON format", "type": "value_error.json"},
			},
		})
		return
	}

	// Validate required fields: title, artifact_type, content
	title, hasTitle := raw["title"].(string)
	artType, hasType := raw["artifact_type"].(string)
	content, hasContent := raw["content"].(string)

	var missingFields []gin.H
	if !hasTitle || title == "" {
		missingFields = append(missingFields, gin.H{"loc": []string{"body", "title"}, "msg": "field required", "type": "value_error.missing"})
	}
	if !hasType || artType == "" {
		missingFields = append(missingFields, gin.H{"loc": []string{"body", "artifact_type"}, "msg": "field required", "type": "value_error.missing"})
	}
	if !hasContent || content == "" {
		missingFields = append(missingFields, gin.H{"loc": []string{"body", "content"}, "msg": "field required", "type": "value_error.missing"})
	}

	if len(missingFields) > 0 {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"detail": missingFields})
		return
	}

	summary, _ := raw["summary"].(string)
	var metaJSON *string
	if mStr, ok := raw["metadata_json"].(string); ok && mStr != "" {
		metaJSON = &mStr
	}

	var wsUUID *uuid.UUID
	if wsStr, ok := raw["workspace_id"].(string); ok && wsStr != "" {
		if u, err := uuid.Parse(wsStr); err == nil {
			wsUUID = &u
			// Check read-only policy
			ws, _ := h.workspaceSvc.GetWorkspace(c.Request.Context(), u, userEmail)
			if ws != nil && !ws.CanEdit {
				c.JSON(http.StatusForbidden, gin.H{
					"detail": "Enterprise Read-Only Policy: You cannot save session artifacts to a read-only workspace.",
				})
				return
			}
		}
	}

	art := &db.SavedArtifact{
		Title:        title,
		ArtifactType: artType,
		Summary:      summary,
		Content:      content,
		MetadataJSON: metaJSON,
		WorkspaceID:  wsUUID,
	}

	created, err := h.svc.CreateArtifact(c.Request.Context(), art)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, created)
}

func (h *ArtifactsHandler) GetArtifact(c *gin.Context) {
	idStr := c.Param("artifact_id")
	artID, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"path", "artifact_id"}, "msg": "value is not a valid uuid: " + idStr, "type": "type_error.uuid"},
			},
		})
		return
	}

	art, err := h.svc.GetArtifact(c.Request.Context(), artID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	if art == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"detail": fmt.Sprintf("Artifact [%s] not found", idStr),
		})
		return
	}
	c.JSON(http.StatusOK, art)
}

func (h *ArtifactsHandler) UpdateArtifact(c *gin.Context) {
	idStr := c.Param("artifact_id")
	artID, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"path", "artifact_id"}, "msg": "value is not a valid uuid: " + idStr, "type": "type_error.uuid"},
			},
		})
		return
	}

	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"detail": err.Error()})
		return
	}

	updated, err := h.svc.UpdateArtifact(c.Request.Context(), artID, updates)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"detail": fmt.Sprintf("Artifact [%s] not found", idStr)})
		return
	}
	c.JSON(http.StatusOK, updated)
}

func (h *ArtifactsHandler) DeleteArtifact(c *gin.Context) {
	idStr := c.Param("artifact_id")
	artID, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"path", "artifact_id"}, "msg": "value is not a valid uuid: " + idStr, "type": "type_error.uuid"},
			},
		})
		return
	}

	success := h.svc.DeleteArtifact(c.Request.Context(), artID)
	if !success {
		c.JSON(http.StatusNotFound, gin.H{
			"detail": fmt.Sprintf("Artifact [%s] not found", idStr),
		})
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *ArtifactsHandler) RestoreSessionContext(c *gin.Context) {
	var body struct {
		ArtifactID  *string `json:"artifact_id"`
		WorkspaceID *string `json:"workspace_id"`
	}
	_ = c.ShouldBindJSON(&body)

	var artUUID *uuid.UUID
	if body.ArtifactID != nil && *body.ArtifactID != "" {
		if u, err := uuid.Parse(*body.ArtifactID); err == nil {
			artUUID = &u
		}
	}
	var wsUUID *uuid.UUID
	if body.WorkspaceID != nil && *body.WorkspaceID != "" {
		if u, err := uuid.Parse(*body.WorkspaceID); err == nil {
			wsUUID = &u
		}
	}

	res, err := h.svc.RestoreSessionContext(c.Request.Context(), artUUID, wsUUID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}
