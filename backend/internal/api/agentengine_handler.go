package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/rficonductorv2/backend/internal/agentengine"
	"github.com/google/rficonductorv2/backend/internal/governance"
)

type AgentEngineHandler struct {
	client     agentengine.AgentEngineClient
	modelArmor *governance.ModelArmorFilter
}

func NewAgentEngineHandler(client agentengine.AgentEngineClient, modelArmor ...*governance.ModelArmorFilter) *AgentEngineHandler {
	var armor *governance.ModelArmorFilter
	if len(modelArmor) > 0 && modelArmor[0] != nil {
		armor = modelArmor[0]
	} else {
		armor = governance.NewModelArmorFilter()
	}
	return &AgentEngineHandler{
		client:     client,
		modelArmor: armor,
	}
}

type queryEnvelope struct {
	Prompt         string                 `json:"prompt"`
	Message        string                 `json:"message"`
	WorkspaceID    string                 `json:"workspace_id"`
	EvaluationType string                 `json:"evaluation_type"`
	Parameters     map[string]interface{} `json:"parameters"`
	Input          json.RawMessage        `json:"input"`
	ClassMethod    string                 `json:"class_method"`
}

type nestedInputEnvelope struct {
	Prompt         string                 `json:"prompt"`
	Message        string                 `json:"message"`
	WorkspaceID    string                 `json:"workspace_id"`
	EvaluationType string                 `json:"evaluation_type"`
	Parameters     map[string]interface{} `json:"parameters"`
}

func (h *AgentEngineHandler) bindQueryRequest(c *gin.Context) (agentengine.QueryRequest, error) {
	var raw queryEnvelope
	if err := c.ShouldBindJSON(&raw); err != nil {
		return agentengine.QueryRequest{}, err
	}

	req := agentengine.QueryRequest{
		Prompt:         raw.Prompt,
		WorkspaceID:    raw.WorkspaceID,
		EvaluationType: raw.EvaluationType,
		Parameters:     raw.Parameters,
	}

	if req.Prompt == "" && raw.Message != "" {
		req.Prompt = raw.Message
	}

	// Unpack nested input envelope if provided
	if len(raw.Input) > 0 {
		var strInput string
		if err := json.Unmarshal(raw.Input, &strInput); err == nil && strInput != "" {
			if req.Prompt == "" {
				req.Prompt = strInput
			}
		} else {
			var nested nestedInputEnvelope
			if err := json.Unmarshal(raw.Input, &nested); err == nil {
				if req.Prompt == "" {
					if nested.Prompt != "" {
						req.Prompt = nested.Prompt
					} else if nested.Message != "" {
						req.Prompt = nested.Message
					}
				}
				if req.WorkspaceID == "" && nested.WorkspaceID != "" {
					req.WorkspaceID = nested.WorkspaceID
				}
				if req.EvaluationType == "" && nested.EvaluationType != "" {
					req.EvaluationType = nested.EvaluationType
				}
				if req.Parameters == nil && nested.Parameters != nil {
					req.Parameters = nested.Parameters
				}
			}
		}
	}

	if strings.TrimSpace(req.Prompt) == "" {
		return agentengine.QueryRequest{}, fmt.Errorf("field 'prompt' (or 'input.prompt') is required")
	}

	return req, nil
}

func (h *AgentEngineHandler) Query(c *gin.Context) {
	req, err := h.bindQueryRequest(c)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"detail": err.Error()})
		return
	}

	if h.modelArmor != nil {
		sanitizedPrompt, err := h.modelArmor.InspectPrompt(c.Request.Context(), req.Prompt)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"detail": err.Error()})
			return
		}
		req.Prompt = sanitizedPrompt
	}

	res, err := h.client.Query(c.Request.Context(), req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}

	if h.modelArmor != nil && res != nil {
		sanitizedOutput, _ := h.modelArmor.InspectOutput(c.Request.Context(), res.Response)
		res.Response = sanitizedOutput
	}

	c.JSON(http.StatusOK, res)
}

func (h *AgentEngineHandler) Stream(c *gin.Context) {
	req, err := h.bindQueryRequest(c)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"detail": err.Error()})
		return
	}

	if h.modelArmor != nil {
		sanitizedPrompt, err := h.modelArmor.InspectPrompt(c.Request.Context(), req.Prompt)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"detail": err.Error()})
			return
		}
		req.Prompt = sanitizedPrompt
	}

	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("Transfer-Encoding", "chunked")

	updates, errChan := h.client.StreamQuery(c.Request.Context(), req)

	c.Stream(func(w io.Writer) bool {
		select {
		case update, ok := <-updates:
			if !ok {
				return false
			}
			if h.modelArmor != nil {
				if update.Message != "" {
					update.Message, _ = h.modelArmor.InspectOutput(c.Request.Context(), update.Message)
				}
				if update.Result != nil && update.Result.Response != "" {
					update.Result.Response, _ = h.modelArmor.InspectOutput(c.Request.Context(), update.Result.Response)
				}
			}
			bytesData, _ := json.Marshal(update)
			fmt.Fprintf(w, "data: %s\n\n", string(bytesData))
			return true
		case err := <-errChan:
			if err != nil {
				fmt.Fprintf(w, "event: error\ndata: %s\n\n", err.Error())
			}
			return false
		case <-c.Request.Context().Done():
			return false
		}
	})
}

func (h *AgentEngineHandler) GetAgentCard(c *gin.Context) {
	card, err := h.client.GetAgentCard(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, card)
}

func (h *AgentEngineHandler) Evaluate(c *gin.Context) {
	var req struct {
		Question        string `json:"question" binding:"required"`
		GeneratedAnswer string `json:"generated_answer" binding:"required"`
		GroundTruth     string `json:"ground_truth"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"detail": err.Error()})
		return
	}

	if h.modelArmor != nil {
		req.Question, _ = h.modelArmor.InspectPrompt(c.Request.Context(), req.Question)
		req.GeneratedAnswer, _ = h.modelArmor.InspectOutput(c.Request.Context(), req.GeneratedAnswer)
	}

	eval, err := h.client.EvaluateResponse(c.Request.Context(), req.Question, req.GeneratedAnswer, req.GroundTruth)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}

	c.JSON(http.StatusOK, eval)
}
