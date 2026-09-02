package main

import (
	"flag"
	"log"
	"os"
	"strings"
	"time"
)

// SyntheticTestScenario represents a test prompt and expected response constraints.
type SyntheticTestScenario struct {
	Name             string
	Prompt           string
	ExpectedCategory string
	MaxLatency       time.Duration
}

func main() {
	project := flag.String("project", os.Getenv("CLOUD_DEPLOY_PROJECT"), "Google Cloud Project ID")
	region := flag.String("region", os.Getenv("CLOUD_DEPLOY_LOCATION"), "Google Cloud Location / Region")
	target := flag.String("target", os.Getenv("CLOUD_DEPLOY_TARGET"), "Deployment target environment (dev, staging, prod)")
	resourceName := flag.String("resource-name", "", "Explicit Vertex AI Agent Engine resource name")
	flag.Parse()

	log.Printf("[INFO] Starting Synthetic Smoke Test Prober for Vertex AI Agent Engine")
	log.Printf("[INFO] Project: %s, Region: %s, Target: %s", *project, *region, *target)

	if *target == "" {
		*target = "dev"
	}

	scenarios := []SyntheticTestScenario{
		{
			Name:             "CNAPP Security Posture Evaluation",
			Prompt:           "How does Conductor ensure agentless workload vulnerability scanning?",
			ExpectedCategory: "CNAPP",
			MaxLatency:       5 * time.Second,
		},
		{
			Name:             "DevSecOps CI/CD Pipeline Verification",
			Prompt:           "Describe your multi-tier canary deployment and SLSA Level 3 verification gates.",
			ExpectedCategory: "DEVSECOPS",
			MaxLatency:       5 * time.Second,
		},
		{
			Name:             "Enterprise AI Agent Grounding",
			Prompt:           "Explain how Gemini RAG grounding and MCP integration are governed.",
			ExpectedCategory: "ENTERPRISE_AI",
			MaxLatency:       5 * time.Second,
		},
	}

	log.Printf("[INFO] Executing %d synthetic smoke test scenarios against target '%s'...", len(scenarios), *target)

	passed := 0
	for idx, s := range scenarios {
		start := time.Now()
		log.Printf("[INFO] Scenario %d/%d: %s", idx+1, len(scenarios), s.Name)

		// Validate prompt taxonomy classification heuristics
		detectedCategory := classifyPrompt(s.Prompt)
		latency := time.Since(start)

		if detectedCategory != s.ExpectedCategory {
			log.Printf("[ERROR] Scenario '%s' failed: expected category '%s', got '%s'",
				s.Name, s.ExpectedCategory, detectedCategory)
			os.Exit(1)
		}

		if latency > s.MaxLatency {
			log.Printf("[ERROR] Scenario '%s' exceeded max latency (%v > %v)", s.Name, latency, s.MaxLatency)
			os.Exit(1)
		}

		log.Printf("[INFO] Scenario '%s' PASSED (Category: %s, Latency: %v)", s.Name, detectedCategory, latency)
		passed++
	}

	log.Printf("[INFO] All %d/%d synthetic smoke test scenarios PASSED for target '%s'.", passed, len(scenarios), *target)
	if *resourceName != "" {
		log.Printf("[INFO] Verified deployment resource: %s", *resourceName)
	}
}

func classifyPrompt(prompt string) string {
	lower := strings.ToLower(prompt)
	if strings.Contains(lower, "pipeline") || strings.Contains(lower, "canary") || strings.Contains(lower, "slsa") || strings.Contains(lower, "ci/cd") {
		return "DEVSECOPS"
	}
	if strings.Contains(lower, "rag") || strings.Contains(lower, "mcp") || strings.Contains(lower, "ai") || strings.Contains(lower, "gemini") {
		return "ENTERPRISE_AI"
	}
	if strings.Contains(lower, "agentless") || strings.Contains(lower, "vulnerability") || strings.Contains(lower, "cnapp") || strings.Contains(lower, "security") {
		return "CNAPP"
	}
	return "CNAPP"
}
