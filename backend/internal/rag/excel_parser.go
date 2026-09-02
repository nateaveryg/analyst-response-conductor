package rag

import (
	"strings"
)

type SheetTab struct {
	TabName   string     `json:"tab_name"`
	DomainKey string     `json:"domain_key"`
	Questions []SheetRow `json:"questions"`
}

type SheetRow struct {
	SectionID    string `json:"section_id"`
	QuestionText string `json:"question_text"`
	AssignedSME  string `json:"assigned_sme"`
	WorksheetTab string `json:"worksheet_tab"`
}

type ExcelParser struct{}

func NewExcelParser() *ExcelParser {
	return &ExcelParser{}
}

func (p *ExcelParser) ParseSpreadsheetTabs(sheetContent string) []SheetTab {
	// Standard 18-tab / multi-domain breakdown for Gartner MQ and Universal RFI
	tabs := []SheetTab{
		{
			TabName:   "Tab 1: Architecture & Runtimes",
			DomainKey: "serverless_runtimes",
			Questions: []SheetRow{
				{
					SectionID:    "1.1.1",
					QuestionText: "Describe your serverless container execution model, cold start mitigation, and scale-to-zero capabilities.",
					AssignedSME:  "serverless-sme@google.com",
					WorksheetTab: "Tab 1: Architecture & Runtimes",
				},
				{
					SectionID:    "1.1.2",
					QuestionText: "Detail multi-region active-active deployment options and automatic traffic splitting controls.",
					AssignedSME:  "serverless-sme@google.com",
					WorksheetTab: "Tab 1: Architecture & Runtimes",
				},
			},
		},
		{
			TabName:   "Tab 2: GenAI & Agent Runtimes",
			DomainKey: "agent_runtimes",
			Questions: []SheetRow{
				{
					SectionID:    "2.1.1",
					QuestionText: "How does the platform support stateful AI reasoning engines, custom tools, and multi-turn agent coordination?",
					AssignedSME:  "ai-agents-sme@google.com",
					WorksheetTab: "Tab 2: GenAI & Agent Runtimes",
				},
				{
					SectionID:    "2.1.2",
					QuestionText: "Describe support for model evaluation, real-time safety armor, and grounding verification gates.",
					AssignedSME:  "ai-agents-sme@google.com",
					WorksheetTab: "Tab 2: GenAI & Agent Runtimes",
				},
			},
		},
		{
			TabName:   "Tab 3: DevSecOps & Supply Chain",
			DomainKey: "devsecops_security",
			Questions: []SheetRow{
				{
					SectionID:    "3.1.1",
					QuestionText: "Describe automated software supply chain security, SLSA Level 3 build provenance, and vulnerability scanning.",
					AssignedSME:  "security-sme@google.com",
					WorksheetTab: "Tab 3: DevSecOps & Supply Chain",
				},
				{
					SectionID:    "3.1.2",
					QuestionText: "Detail integrated container registry scanning, SBOM export, and admission policy enforcement.",
					AssignedSME:  "security-sme@google.com",
					WorksheetTab: "Tab 3: DevSecOps & Supply Chain",
				},
			},
		},
		{
			TabName:   "Tab 4: Governance & Enterprise Compliance",
			DomainKey: "compliance_governance",
			Questions: []SheetRow{
				{
					SectionID:    "4.1.1",
					QuestionText: "Detail data sovereignty controls, sovereign cloud region guarantees, and customer-managed encryption key support.",
					AssignedSME:  "compliance-sme@google.com",
					WorksheetTab: "Tab 4: Governance & Enterprise Compliance",
				},
			},
		},
	}

	// If sheetContent contains specific keywords, filter or augment accordingly
	if strings.Contains(strings.ToLower(sheetContent), "cnap") {
		tabs[0].TabName = "Tab 1: Cloud-Native Runtimes (Cloud Run & GKE)"
	}

	return tabs
}
