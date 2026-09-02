package main

import (
	"context"
	"encoding/json"
	"iter"
	"log"
	"os"

	"conductor/agent_engine_go/agent"

	adkAgent "google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/agentengine"
	"google.golang.org/adk/v2/model"
	"google.golang.org/adk/v2/session"
	"google.golang.org/adk/v2/session/vertexai"
	"google.golang.org/genai"
)

func main() {
	engine := agent.NewConductorAgentEngine()
	ctx := context.Background()

	agentEngineID := os.Getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
	location := os.Getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION")
	if location == "" {
		location = "us-central1"
	}

	conductorAgent, err := adkAgent.New(adkAgent.Config{
		Name:        "conductor_agent",
		Description: "Evaluates enterprise analyst questionnaire rubrics across CNAPP, DEVSECOPS, and ENTERPRISE_AI.",
		Run: func(ic adkAgent.InvocationContext) iter.Seq2[*session.Event, error] {
			return func(yield func(*session.Event, error) bool) {
				var userText string
				if ic.UserContent() != nil {
					for _, p := range ic.UserContent().Parts {
						if p != nil && p.Text != "" {
							userText += p.Text
						}
					}
				}
				res, err := engine.Query(ic, userText)
				if err != nil {
					yield(nil, err)
					return
				}
				jsonBytes, err := json.Marshal(res)
				if err != nil {
					yield(nil, err)
					return
				}
				event := session.NewEvent(ic, ic.InvocationID())
				event.Author = ic.Agent().Name()
				event.Branch = ic.Branch()
				event.LLMResponse = model.LLMResponse{
					Content: &genai.Content{
						Role: genai.RoleModel,
						Parts: []*genai.Part{
							{Text: string(jsonBytes)},
						},
					},
				}
				yield(event, nil)
			}
		},
	})
	if err != nil {
		log.Fatalf("Failed to initialize conductor agent: %v", err)
	}

	var sessionService session.Service
	if agentEngineID != "" && projectID != "" {
		sessionService, err = vertexai.NewSessionService(ctx, vertexai.VertexAIServiceConfig{
			ProjectID:       projectID,
			Location:        location,
			ReasoningEngine: agentEngineID,
		})
		if err != nil {
			log.Printf("[WARN] Vertex AI session service unavailable, using InMemoryService: %v", err)
			sessionService = session.InMemoryService()
		}
	} else {
		sessionService = session.InMemoryService()
	}

	config := &launcher.Config{
		SessionService: sessionService,
		AgentLoader:    adkAgent.NewSingleLoader(conductorAgent),
	}

	l := agentengine.NewLauncher(agentEngineID)
	log.Printf("[INFO] Starting Conductor ADK Go Agent Engine v%s", engine.Version)

	if len(os.Args) > 1 {
		if err := l.Execute(ctx, config, os.Args[1:]); err != nil {
			log.Fatalf("Launcher execution failure: %v", err)
		}
		return
	}

	if err := l.Execute(ctx, config, []string{"web", "-port", "8080", "agentengine"}); err != nil {
		log.Fatalf("Default server execution failure: %v", err)
	}
}

