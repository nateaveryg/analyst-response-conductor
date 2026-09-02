package agent

import (
	"context"
	"fmt"
	"regexp"
	"strings"
)

var (
	reDevSecOps    = regexp.MustCompile(`(?i)\b(pipeline|deploy|build|canary|slsa|ci/cd|cd|continuous delivery)\b`)
	reEnterpriseAI = regexp.MustCompile(`(?i)\b(ai|llm|gemini|rag|vector|embedding|mcp|model|autonomous agent)\b`)
	reCNAPP        = regexp.MustCompile(`(?i)\b(cnapp|cwpp|cspm|ciem|vulnerability|agentless|workload|security|iam|encryption|kms)\b`)
)

// TaxonomyCategory defines the metadata and rubrics for an analyst evaluation category.
type TaxonomyCategory struct {
	Name                string   `json:"name"`
	Rubrics             []string `json:"rubrics"`
	DefaultSME          string   `json:"default_sme"`
	ComplianceStandards []string `json:"compliance_standards"`
}

// ConductorAgentEngine manages enterprise analyst evaluations for Conductor v3.
type ConductorAgentEngine struct {
	Version      string
	Taxonomies   map[string]TaxonomyCategory
	RoutingRules map[string]string
}

// EvaluationResult represents the synthesized assessment response.
type EvaluationResult struct {
	Response            string   `json:"response"`
	Category            string   `json:"category"`
	AssignedSME         string   `json:"assigned_sme"`
	Confidence          float64  `json:"confidence"`
	Rubrics             []string `json:"rubrics"`
	ComplianceStandards []string `json:"compliance_standards"`
	Version             string   `json:"version"`
	Runtime             string   `json:"runtime"`
}

// NewConductorAgentEngine instantiates the engine with default taxonomies and SME routing.
func NewConductorAgentEngine() *ConductorAgentEngine {
	return &ConductorAgentEngine{
		Version: "3.2.0-adk-go",
		Taxonomies: map[string]TaxonomyCategory{
			"CNAPP": {
				Name: "Cloud-Native Application Protection Platform (CNAPP)",
				Rubrics: []string{
					"Agentless Workload Scanning",
					"Container Vulnerability Lifecycle",
					"CI/CD Pipeline Security Gateways",
					"Cloud Security Posture Management (CSPM)",
					"Cloud Workload Protection (CWPP)",
					"Cloud Infrastructure Entitlement Management (CIEM)",
					"Real-Time Container Threat Detection",
				},
				DefaultSME:          "security-sme@google.com",
				ComplianceStandards: []string{"SOC2 Type II", "FedRAMP High", "ISO 27001", "NIST SP 800-53"},
			},
			"DEVSECOPS": {
				Name: "Enterprise DevSecOps & Continuous Delivery",
				Rubrics: []string{
					"Automated Multi-Stage Pipelines",
					"Canary & Blue/Green Deployments",
					"Artifact Provenance & SLSA Level 3",
					"Policy-as-Code & Open Policy Agent (OPA)",
					"Continuous Automated Verification Testing",
					"Automated Canary Rollback Verification",
				},
				DefaultSME:          "devops-sme@google.com",
				ComplianceStandards: []string{"SLSA v1.0 Level 3", "Supply-chain Levels for Software Artifacts"},
			},
			"ENTERPRISE_AI": {
				Name: "Enterprise AI & Autonomous Agent Platforms",
				Rubrics: []string{
					"Multi-Agent Orchestration & A2A Routing",
					"pgvector & Enterprise Knowledge Retrieval",
					"Model Context Protocol (MCP) Integration",
					"Agent Identity & IAM Governance",
					"Automated RAG Evaluation & Grounding",
					"Continuous Automated Governance",
				},
				DefaultSME:          "ai-sme@google.com",
				ComplianceStandards: []string{"Responsible AI Guardrails", "Enterprise Data Confidentiality"},
			},
		},
		RoutingRules: map[string]string{
			"pipeline":      "devops-sme@google.com",
			"cloud deploy":  "devops-sme@google.com",
			"canary":        "devops-sme@google.com",
			"slsa":          "devops-sme@google.com",
			"security":      "security-sme@google.com",
			"vulnerability": "security-sme@google.com",
			"ciem":          "security-sme@google.com",
			"cspm":          "security-sme@google.com",
			"gemini":        "ai-sme@google.com",
			"rag":           "ai-sme@google.com",
			"mcp":           "ai-sme@google.com",
			"agent":         "ai-sme@google.com",
		},
	}
}

// ClassifyPrompt categorizes a questionnaire prompt and determines the assigned SME.
func (e *ConductorAgentEngine) ClassifyPrompt(prompt string) (string, string, float64) {
	if reDevSecOps.MatchString(prompt) {
		return "DEVSECOPS", e.Taxonomies["DEVSECOPS"].DefaultSME, 0.96
	}

	if reEnterpriseAI.MatchString(prompt) {
		return "ENTERPRISE_AI", e.Taxonomies["ENTERPRISE_AI"].DefaultSME, 0.94
	}

	if reCNAPP.MatchString(prompt) {
		return "CNAPP", e.Taxonomies["CNAPP"].DefaultSME, 0.92
	}

	return "CNAPP", e.Taxonomies["CNAPP"].DefaultSME, 0.85
}

// Query performs a synchronous evaluation of an analyst questionnaire prompt.
func (e *ConductorAgentEngine) Query(ctx context.Context, prompt string) (*EvaluationResult, error) {
	category, sme, confidence := e.ClassifyPrompt(prompt)
	tax, exists := e.Taxonomies[category]
	if !exists {
		return nil, fmt.Errorf("unknown taxonomy category: %s", category)
	}

	response := fmt.Sprintf("Conductor v3 evaluates prompt under rubric '%s'. Compliance standards: %s. Assigned SME: %s.",
		tax.Name, strings.Join(tax.ComplianceStandards, ", "), sme)

	return &EvaluationResult{
		Response:            response,
		Category:            category,
		AssignedSME:         sme,
		Confidence:          confidence,
		Rubrics:             tax.Rubrics,
		ComplianceStandards: tax.ComplianceStandards,
		Version:             e.Version,
		Runtime:             "vertex-ai-agent-engine-adk-go",
	}, nil
}
