package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/rficonductorv2/backend/internal/services"
)

type InclusionHandler struct {
	analyzer *services.InclusionAnalyzer
}

func NewInclusionHandler(analyzer *services.InclusionAnalyzer) *InclusionHandler {
	return &InclusionHandler{analyzer: analyzer}
}

func (h *InclusionHandler) AnalyzeInclusion(c *gin.Context) {
	var req struct {
		RawRfiText string `json:"raw_rfi_text" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"detail": []gin.H{
				{"loc": []string{"body", "raw_rfi_text"}, "msg": "field required", "type": "value_error.missing"},
			},
		})
		return
	}

	matrix := h.analyzer.AnalyzeInclusion(c.Request.Context(), req.RawRfiText)
	c.JSON(http.StatusOK, matrix)
}
