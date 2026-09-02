package api

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/services"
)

type TimelineRequest struct {
	TargetDeadline   time.Time                  `json:"target_deadline"`
	ExclusionWindows []services.ExclusionWindow `json:"exclusion_windows"`
}

type RoutingRequest struct {
	QuestionIDs         []uuid.UUID `json:"question_ids"`
	EvaluationID        *uuid.UUID  `json:"evaluation_id"`
	ConfidenceThreshold float64     `json:"confidence_threshold"`
}

type OrchestrationHandler struct {
	timeline *services.TimelineEngine
	routing  *services.RoutingEngine
}

func NewOrchestrationHandler(timeline *services.TimelineEngine, routing *services.RoutingEngine) *OrchestrationHandler {
	return &OrchestrationHandler{
		timeline: timeline,
		routing:  routing,
	}
}

func (h *OrchestrationHandler) CreateWorkbackTimeline(c *gin.Context) {
	var req TimelineRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"body"}, "msg": err.Error(), "type": "value_error"},
			},
		})
		return
	}

	timeline := h.timeline.GenerateTimeline(req.TargetDeadline, req.ExclusionWindows)
	c.JSON(http.StatusOK, timeline)
}

func (h *OrchestrationHandler) RouteRfiQuestions(c *gin.Context) {
	var req RoutingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"body"}, "msg": err.Error(), "type": "value_error"},
			},
		})
		return
	}

	results := h.routing.RouteQuestions(c.Request.Context(), req.QuestionIDs)
	c.JSON(http.StatusOK, results)
}
