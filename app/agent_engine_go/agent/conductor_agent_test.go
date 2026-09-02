package agent

import (
	"context"
	"testing"
)

func TestClassification(t *testing.T) {
	engine := NewConductorAgentEngine()

	tests := []struct {
		prompt           string
		expectedCategory string
		expectedSME      string
	}{
		{
			prompt:           "How do we configure agentless workload scanning and CSPM policies?",
			expectedCategory: "CNAPP",
			expectedSME:      "security-sme@google.com",
		},
		{
			prompt:           "Describe your multi-tier canary deployment pipeline and SLSA provenance.",
			expectedCategory: "DEVSECOPS",
			expectedSME:      "devops-sme@google.com",
		},
		{
			prompt:           "Explain Gemini RAG grounding, vector retrieval, and MCP tools.",
			expectedCategory: "ENTERPRISE_AI",
			expectedSME:      "ai-sme@google.com",
		},
	}

	for _, tt := range tests {
		cat, sme, conf := engine.ClassifyPrompt(tt.prompt)
		if cat != tt.expectedCategory {
			t.Errorf("Prompt '%s': expected category %s, got %s", tt.prompt, tt.expectedCategory, cat)
		}
		if sme != tt.expectedSME {
			t.Errorf("Prompt '%s': expected SME %s, got %s", tt.prompt, tt.expectedSME, sme)
		}
		if conf < 0.90 {
			t.Errorf("Prompt '%s': expected confidence >= 0.90, got %f", tt.prompt, conf)
		}
	}
}

func TestQuery(t *testing.T) {
	engine := NewConductorAgentEngine()
	ctx := context.Background()

	res, err := engine.Query(ctx, "Evaluate our CI/CD pipeline and SLSA Level 3 security gateways.")
	if err != nil {
		t.Fatalf("Query failed: %v", err)
	}

	if res.Category != "DEVSECOPS" {
		t.Errorf("Expected category DEVSECOPS, got %s", res.Category)
	}
	if res.AssignedSME != "devops-sme@google.com" {
		t.Errorf("Expected devops-sme@google.com, got %s", res.AssignedSME)
	}
	if len(res.Rubrics) == 0 {
		t.Errorf("Expected non-empty rubrics list")
	}
	if res.Version != "3.2.0-adk-go" {
		t.Errorf("Expected version 3.2.0-adk-go, got %s", res.Version)
	}
	if res.Runtime != "vertex-ai-agent-engine-adk-go" {
		t.Errorf("Expected runtime vertex-ai-agent-engine-adk-go, got %s", res.Runtime)
	}

	// Verify new ENTERPRISE_AI validation rubric
	aiTax, ok := engine.Taxonomies["ENTERPRISE_AI"]
	if !ok {
		t.Fatalf("Missing ENTERPRISE_AI taxonomy")
	}
	hasGovernance := false
	for _, r := range aiTax.Rubrics {
		if r == "Continuous Automated Governance" {
			hasGovernance = true
			break
		}
	}
	if !hasGovernance {
		t.Errorf("Expected 'Continuous Automated Governance' in ENTERPRISE_AI rubrics, got %v", aiTax.Rubrics)
	}
}
