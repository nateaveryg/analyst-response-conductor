package agentengine

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestVertexAgentEngineClient_Query(t *testing.T) {
	client := NewClient(ClientConfig{
		ProjectID: "riccardo-blog-test-v1",
		Location:  "us-central1",
		ModelName: "gemini-3.5-flash",
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	t.Run("Query CNAPP questionnaire prompt", func(t *testing.T) {
		req := QueryRequest{
			Prompt:      "Explain container vulnerability scanning and agentless workload security.",
			WorkspaceID: "ws-cnap-001",
		}
		resp, err := client.Query(ctx, req)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if resp.Category != "CNAPP" {
			t.Errorf("expected category CNAPP, got %s", resp.Category)
		}
		if resp.AssignedSME != "security-sme@google.com" {
			t.Errorf("expected security-sme, got %s", resp.AssignedSME)
		}
		if resp.ConfidenceScore < 0.80 {
			t.Errorf("expected confidence >= 0.80, got %f", resp.ConfidenceScore)
		}
		if !strings.Contains(resp.Response, "Google Cloud provides comprehensive enterprise-grade support") {
			t.Errorf("expected response text to contain solution capability, got %s", resp.Response)
		}
	})

	t.Run("Query DevSecOps continuous delivery prompt", func(t *testing.T) {
		req := QueryRequest{
			Prompt:      "Explain SLSA Level 3 automated build provenance in Cloud Build and Cloud Deploy pipelines.",
			WorkspaceID: "ws-devsecops-001",
		}
		resp, err := client.Query(ctx, req)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if resp.Category != "DEVSECOPS" {
			t.Errorf("expected category DEVSECOPS, got %s", resp.Category)
		}
		if resp.AssignedSME != "devops-sme@google.com" {
			t.Errorf("expected devops-sme, got %s", resp.AssignedSME)
		}
	})

	t.Run("Query Enterprise AI agent prompt", func(t *testing.T) {
		req := QueryRequest{
			Prompt:      "Describe multi-agent orchestration, pgvector RAG retrieval, and Vertex AI Agent Engine.",
			WorkspaceID: "ws-ai-001",
		}
		resp, err := client.Query(ctx, req)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if resp.Category != "ENTERPRISE_AI" {
			t.Errorf("expected category ENTERPRISE_AI, got %s", resp.Category)
		}
		if resp.AssignedSME != "ai-sme@google.com" {
			t.Errorf("expected ai-sme, got %s", resp.AssignedSME)
		}
	})
}

func TestVertexAgentEngineClient_StreamQuery(t *testing.T) {
	client := NewClient(ClientConfig{
		ModelName: "gemini-3.5-flash",
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	req := QueryRequest{
		Prompt: "Describe Canary deployments in Cloud Deploy.",
	}

	updates, errChan := client.StreamQuery(ctx, req)
	var stagesCount int
	var receivedCompletion bool

	for update := range updates {
		if update.Type == "stage_update" {
			stagesCount++
		} else if update.Type == "completion" {
			receivedCompletion = true
			if update.Result == nil || update.Result.Response == "" {
				t.Errorf("expected non-empty completion result")
			}
		}
	}

	if err := <-errChan; err != nil {
		t.Fatalf("stream returned unexpected error: %v", err)
	}

	if stagesCount != 4 {
		t.Errorf("expected 4 intermediate stages, got %d", stagesCount)
	}
	if !receivedCompletion {
		t.Errorf("expected completion event in stream")
	}
}

func TestVertexAgentEngineClient_GetAgentCard(t *testing.T) {
	client := NewClient(ClientConfig{})
	card, err := client.GetAgentCard(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if card.Name != "Analyst Response Agent (Agent Engine)" {
		t.Errorf("unexpected name: %s", card.Name)
	}
	if len(card.Protocols) != 2 {
		t.Errorf("expected 2 protocols, got %d", len(card.Protocols))
	}
}

func TestVertexAgentEngineClient_EvaluateResponse(t *testing.T) {
	client := NewClient(ClientConfig{})

	t.Run("High quality response with compliance standards passes", func(t *testing.T) {
		res, err := client.EvaluateResponse(
			context.Background(),
			"How do you ensure container security?",
			"Google Cloud Artifact Registry provides automated vulnerability scanning and SLSA Level 3 provenance attestations with SOC2 Type II compliance.",
			"",
		)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !res.PassedEvaluation {
			t.Errorf("expected passed evaluation, got false (score: %f)", res.OverallQualityScore)
		}
	})

	t.Run("Short response without compliance fails threshold", func(t *testing.T) {
		res, err := client.EvaluateResponse(
			context.Background(),
			"How do you ensure container security?",
			"We scan containers.",
			"",
		)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.PassedEvaluation {
			t.Errorf("expected failure, got passed")
		}
	})
}
