package api

import (
	"encoding/json"
	"io"
	"time"

	"github.com/gin-gonic/gin"
)

type StreamHandler struct{}

func NewStreamHandler() *StreamHandler {
	return &StreamHandler{}
}

func (h *StreamHandler) StreamTelemetry(c *gin.Context) {
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")

	subagentEvents := []map[string]interface{}{
		{"event": "subagent_started", "agent": "Phase1IntakeAgentService", "status": "Initializing multi-sub-agent delegation cluster..."},
		{"event": "subagent_progress", "agent": "RfiDocumentParserAgent", "status": "Parsed 14 layout blocks, 6 tables, and 4 tabs from RFI workbook."},
		{"event": "subagent_progress", "agent": "CriteriaExtractionAgent", "status": "Audited analyst rubric: GA cutoff 2026-06-01, revenue floor $25M."},
		{"event": "subagent_progress", "agent": "PortfolioMappingAgent", "status": "Matched 12 GA SKUs across PRODUCT_DATABASE & UNIVERSAL_CORPUS."},
		{"event": "subagent_progress", "agent": "GovernanceGoNoGoAgent", "status": "Evaluated financial compliance: Proceed with Participation."},
		{"event": "subagent_completed", "agent": "Phase1IntakeAgentService", "status": "100% Scorecard synthesis complete with real-time telemetry."},
	}

	c.Stream(func(w io.Writer) bool {
		for _, ev := range subagentEvents {
			data, err := json.Marshal(ev)
			if err != nil {
				continue
			}
			c.SSEvent("", string(data))
			c.Writer.Flush()
			time.Sleep(200 * time.Millisecond)
		}
		return false
	})
}
