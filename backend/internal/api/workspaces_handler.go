package api

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/db"
	"github.com/google/rficonductorv2/backend/internal/services"
)

type WorkspaceCreateRequest struct {
	Name            string  `json:"name" binding:"required"`
	ReportType      string  `json:"report_type" binding:"required"`
	Description     *string `json:"description"`
	CoEditorsJSON   string  `json:"co_editors_json"`
	IsDefault       bool    `json:"is_default"`
	CurrentPhase    int     `json:"current_phase"`
	LastCompletedStep string `json:"last_completed_step"`
	LastActionID    *string `json:"last_action_id"`
	ContextDataJSON *string `json:"context_data_json"`
}

type WorkspacesHandler struct {
	svc *services.WorkspaceService
}

func NewWorkspacesHandler(svc *services.WorkspaceService) *WorkspacesHandler {
	return &WorkspacesHandler{svc: svc}
}

func (h *WorkspacesHandler) ListWorkspaces(c *gin.Context) {
	userEmail := c.GetString(CtxUserEmailKey)
	workspaces, err := h.svc.ListWorkspaces(c.Request.Context(), userEmail)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, workspaces)
}

func (h *WorkspacesHandler) CreateWorkspace(c *gin.Context) {
	userEmail := c.GetString(CtxUserEmailKey)
	var req WorkspaceCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"body"}, "msg": err.Error(), "type": "value_error"},
			},
		})
		return
	}

	ws := &db.Workspace{
		Name:              req.Name,
		ReportType:        req.ReportType,
		Description:       req.Description,
		CoEditorsJSON:     req.CoEditorsJSON,
		IsDefault:         req.IsDefault,
		CurrentPhase:      req.CurrentPhase,
		LastCompletedStep: req.LastCompletedStep,
		LastActionID:      req.LastActionID,
		ContextDataJSON:   req.ContextDataJSON,
	}

	created, err := h.svc.CreateWorkspace(c.Request.Context(), ws, userEmail)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, created)
}

func (h *WorkspacesHandler) GetWorkspace(c *gin.Context) {
	idStr := c.Param("workspace_id")
	wsID, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"path", "workspace_id"}, "msg": "value is not a valid uuid: " + idStr, "type": "type_error.uuid"},
			},
		})
		return
	}

	userEmail := c.GetString(CtxUserEmailKey)
	ws, err := h.svc.GetWorkspace(c.Request.Context(), wsID, userEmail)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	if ws == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"detail": fmt.Sprintf("Workspace [%s] not found", idStr),
		})
		return
	}
	c.JSON(http.StatusOK, ws)
}

func (h *WorkspacesHandler) UpdateWorkspace(c *gin.Context) {
	idStr := c.Param("workspace_id")
	wsID, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"path", "workspace_id"}, "msg": "value is not a valid uuid: " + idStr, "type": "type_error.uuid"},
			},
		})
		return
	}

	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"body"}, "msg": err.Error(), "type": "value_error"},
			},
		})
		return
	}

	updated, err := h.svc.UpdateWorkspace(c.Request.Context(), wsID, updates)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, updated)
}
