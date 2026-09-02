package agentengine

import "time"

// QueryRequest represents a request to the Vertex AI Agent Engine.
type QueryRequest struct {
	Prompt         string                 `json:"prompt" binding:"required"`
	WorkspaceID    string                 `json:"workspace_id,omitempty"`
	EvaluationType string                 `json:"evaluation_type,omitempty"`
	Parameters     map[string]interface{} `json:"parameters,omitempty"`
}

// QueryResponse represents the structured response returned by Vertex AI Agent Engine.
type QueryResponse struct {
	Status               string   `json:"status"`
	AgentEngineVersion   string   `json:"agent_engine_version"`
	Runtime              string   `json:"runtime"`
	Model                string   `json:"model"`
	WorkspaceID          string   `json:"workspace_id"`
	Category             string   `json:"category"`
	AssignedSME          string   `json:"assigned_sme"`
	ConfidenceScore      float64  `json:"confidence_score"`
	MatchedRubrics       []string `json:"matched_rubrics"`
	ComplianceFrameworks []string `json:"compliance_frameworks"`
	Response             string   `json:"response"`
	LatencyMs            float64  `json:"latency_ms"`
	Timestamp            string   `json:"timestamp"`
}

// StreamStageUpdate represents an intermediate reasoning stage event during streaming execution.
type StreamStageUpdate struct {
	Type      string         `json:"type"` // "stage_update" or "completion"
	Phase     string         `json:"phase,omitempty"`
	Message   string         `json:"message,omitempty"`
	Timestamp string         `json:"timestamp,omitempty"`
	Result    *QueryResponse `json:"result,omitempty"`
}

// AgentCard represents the A2A and Vertex Agent Engine registration card.
type AgentCard struct {
	Name         string            `json:"name"`
	Description  string            `json:"description"`
	Version      string            `json:"version"`
	Runtime      string            `json:"runtime"`
	Framework    string            `json:"framework"`
	Capabilities []string          `json:"capabilities"`
	Taxonomies   []string          `json:"taxonomies"`
	Protocols    []ProtocolVersion `json:"protocols"`
}

// ProtocolVersion represents supported communication protocol formats.
type ProtocolVersion struct {
	Type    string `json:"type"`
	Version string `json:"version"`
}

// EvaluationResult represents quality, groundedness, and compliance audit scoring.
type EvaluationResult struct {
	Question                 string    `json:"question"`
	OverallQualityScore      float64   `json:"overall_quality_score"`
	GroundednessScore        float64   `json:"groundedness_score"`
	ComplianceAdherenceScore float64   `json:"compliance_adherence_score"`
	PassedEvaluation         bool      `json:"passed_evaluation"`
	EvaluationEngine         string    `json:"evaluation_engine"`
	EvaluatedAt              time.Time `json:"evaluated_at"`
}
