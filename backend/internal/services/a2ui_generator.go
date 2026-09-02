package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
)

type A2UIGenerator struct{}

func NewA2UIGenerator() *A2UIGenerator {
	return &A2UIGenerator{}
}

func (g *A2UIGenerator) WrapInA2UITags(payload interface{}) string {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(payload); err != nil {
		return "<a2ui-json>\n{}\n</a2ui-json>"
	}
	jsonStr := strings.TrimSpace(buf.String())
	return fmt.Sprintf("<a2ui-json>\n%s\n</a2ui-json>", jsonStr)
}

func (g *A2UIGenerator) BuildProgressTracker(phaseNum int) []map[string]interface{} {
	// Exact match with Python 7-Phase completion rates
	percentages := map[int]int{
		1: 14,
		2: 29,
		3: 43,
		4: 57,
		5: 71,
		6: 86,
		7: 100,
	}
	percentage := percentages[phaseNum]
	if percentage == 0 {
		percentage = int(float64(phaseNum) / 7.0 * 100)
	}

	phases := []struct {
		Label string
		Num   int
	}{
		{"1. Evaluate", 1},
		{"2. Assign", 2},
		{"3. Kickoff", 3},
		{"4. RFI Answers", 4},
		{"5. Demo", 5},
		{"6. Exec Review", 6},
		{"7. Publish", 7},
	}

	var crumbs []string
	for _, p := range phases {
		if p.Num < phaseNum {
			crumbs = append(crumbs, fmt.Sprintf("[✅ %s]", p.Label))
		} else if p.Num == phaseNum {
			crumbs = append(crumbs, fmt.Sprintf("[🟢 %s (Active)]", p.Label))
		} else {
			crumbs = append(crumbs, fmt.Sprintf("[⚪ %s]", p.Label))
		}
	}

	breadcrumbStr := strings.Join(crumbs, " ➔ ")

	return []map[string]interface{}{
		{
			"type": "Container",
			"properties": map[string]interface{}{
				"style": map[string]interface{}{
					"padding":         "12px",
					"backgroundColor": "#f8fafc",
					"borderRadius":    "8px",
					"marginBottom":   "12px",
					"border":           "1px solid #e2e8f0",
				},
				"children": []map[string]interface{}{
					{
						"type": "Text",
						"properties": map[string]interface{}{
							"content": fmt.Sprintf("📊 7-Phase Operational Lifecycle Progress (%d%% Complete)", percentage),
							"style": map[string]interface{}{
								"fontWeight": "bold",
								"fontSize":   "14px",
								"color":      "#1e293b",
							},
						},
					},
					{
						"type": "Text",
						"properties": map[string]interface{}{
							"content": breadcrumbStr,
							"style": map[string]interface{}{
								"fontSize": "12px",
								"color":    "#475569",
							},
						},
					},
				},
			},
		},
	}
}

func (g *A2UIGenerator) GeneratePhase1IntakeSurface(reportName string) string {
	if reportName == "" {
		reportName = "DevSecOps Platforms, 2026"
	}
	tracker := g.BuildProgressTracker(1)

	surface := map[string]interface{}{
		"surface_id":       "phase1_intake",
		"card_id":          "card-intake",
		"phase":            1,
		"progress_percent": 14.0,
		"title":            "Phase 1: Universal Analyst Document Intake & Evaluation Scope",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 1: Universal Analyst Document Intake & Evaluation Scope",
				"subtitle":    "Step 1A: Document Link Intake & Context Ingestion",
				"description": fmt.Sprintf("Active Evaluation Scope: %s. Upload Welcome Packet, Demonstration Guidelines, and Analyst Criteria documents. 1A: Document Link Intake confirmed.", reportName),
				"fields": []map[string]interface{}{
					{"name": "welcome_packet_url", "label": "Welcome Packet URL / Drive Link", "type": "text", "placeholder": "https://docs.google.com/..."},
					{"name": "demo_guidelines_url", "label": "Demo Guidelines URL / Drive Link", "type": "text", "placeholder": "https://docs.google.com/..."},
					{"name": "analyst_notes", "label": "Analyst Context & Specific Notes", "type": "textarea", "placeholder": "Enter specific rubric constraints..."},
				},
				"actions": []map[string]interface{}{
					{"action_id": "submit_criteria_analysis", "label": "Run Portfolio Eligibility Evaluation", "primary": true},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase1ScorecardSurface(reportName string, qualifyingCount int) string {
	tracker := g.BuildProgressTracker(1)

	surface := map[string]interface{}{
		"surface_id":       "phase1_scorecard",
		"card_id":          "card-evaluation-matrix",
		"phase":            1,
		"progress_percent": 14.0,
		"title":            "Portfolio Eligibility Scorecard & Go/No-Go Decision",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Portfolio Eligibility Scorecard & Go/No-Go Decision",
				"subtitle":    "Step 1B: Criteria Qualification & Strategy Formulation",
				"description": fmt.Sprintf("PROCEED WITH PARTICIPATION. Found %d qualifying Google Cloud offerings meeting $25M revenue floor and 500 logo floor.", qualifyingCount),
				"metrics": map[string]interface{}{
					"status":          "PROCEED WITH PARTICIPATION",
					"qualifying_skus": qualifyingCount,
					"revenue_floor":   "$25,000,000",
					"logo_floor":      500,
					"flagship_sku":    "Gemini Code Assist Enterprise ($35M Rev / 620 Logos)",
				},
				"actions": []map[string]interface{}{
					{"action_id": "assign_tasks", "label": "Advance to Phase 2: SME Task Routing", "primary": true},
					{"action_id": "download_deep_dive_report", "label": "Download Comprehensive Deep Dive Report (.md)", "primary": false},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase2RoutingSurface() string {
	tracker := g.BuildProgressTracker(2)

	surface := map[string]interface{}{
		"surface_id":       "phase2_routing",
		"card_id":          "card-task-assignment",
		"phase":            2,
		"progress_percent": 29.0,
		"title":            "Phase 2: SME Task Routing & Workstream Assignment",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 2: SME Task Routing & Workstream Assignment",
				"subtitle":    "Step 2: Automated Routing & Domain Ownership Matrix",
				"description": "Assigned domain leads across qualifying portfolio capabilities. Domain SMEs allocated: David Jacobs (Serverless Runtime), Nathen Harvey (DevSecOps & DORA), Sarah Miller (Security & Supply Chain).",
				"sme_allocations": []map[string]interface{}{
					{"domain": "Serverless Runtime & Concurrency", "sme": "David Jacobs", "email": "davidjacobs@google.com", "questions_count": 42},
					{"domain": "DevSecOps & DORA Metrics", "sme": "Nathen Harvey", "email": "nathenharvey@google.com", "questions_count": 38},
					{"domain": "Software Supply Chain & Artifacts", "sme": "Sarah Miller", "email": "sarahmiller@google.com", "questions_count": 41},
				},
				"actions": []map[string]interface{}{
					{"action_id": "kickoff_project", "label": "Advance to Phase 3: Stakeholder Kickoff", "primary": true},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase3KickoffSurface() string {
	tracker := g.BuildProgressTracker(3)

	surface := map[string]interface{}{
		"surface_id":       "phase3_kickoff",
		"card_id":          "card-timeline",
		"phase":            3,
		"progress_percent": 43.0,
		"title":            "Phase 3: Stakeholder Kickoff & Workback Schedule",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 3: Stakeholder Kickoff & OPM/SME Alignment Charter",
				"subtitle":    "Step 3: Milestone Commitments & Corporate Freeze Alignment",
				"description": "Stakeholder Kickoff Charter established. Phase 5 Video Recording Budget Guidelines enforced (<=60 min total cap across demonstrated use cases). Calendar freezes locked: T-14 Storyboard & Narrative Freeze, T-12 Demo Sandbox Deployment.",
				"guidelines": []string{
					"Phase 5 Video Recording Budget Guidelines: <=60 minutes total cap (720p+ .mp4, <4GB)",
					"T-14 Storyboard & Narrative Freeze",
					"T-12 Demo Sandbox Deployment",
					"T-8 Final Video Capture & Table of Contents (TOC) Freeze",
				},
				"actions": []map[string]interface{}{
					{"action_id": "upload_rfi", "label": "Advance to Phase 4: RFI Ingestion", "primary": true},
					{"action_id": "download_kickoff_deck", "label": "Download Kickoff Deck (.md)", "primary": false},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase4ASurface() string {
	tracker := g.BuildProgressTracker(4)

	surface := map[string]interface{}{
		"surface_id":       "phase4a_upload",
		"card_id":          "card-rfi-upload",
		"phase":            4,
		"progress_percent": 57.0,
		"title":            "Phase 4A: RFI Questionnaire Spreadsheet Intake",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 4A: RFI Questionnaire Spreadsheet Intake",
				"subtitle":    "Step 4A: RFI Questionnaire Spreadsheet Upload & Intake (Active)",
				"description": "Upload analyst RFI questionnaire spreadsheet (.xlsx or .csv) containing capability questions across tabs.",
				"fields": []map[string]interface{}{
					{"name": "rfi_spreadsheet_file", "label": "RFI Spreadsheet (.xlsx / .csv)", "type": "file"},
				},
				"actions": []map[string]interface{}{
					{"action_id": "generate_rfi_responses", "label": "Execute Parallel RAG Ingestion & Draft Generation", "primary": true},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase4BSurface() string {
	tracker := g.BuildProgressTracker(4)

	surface := map[string]interface{}{
		"surface_id":       "phase4b_drafts",
		"card_id":          "card-rfi-responses",
		"phase":            4,
		"progress_percent": 57.0,
		"title":            "Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 4B: Automated RAG Ingestion & Initial RFI Technical Drafts",
				"subtitle":    "Step 4B: Grounded Synthesis & Citations",
				"description": "Pre-populated 121 questionnaire responses across all worksheet tabs with 98.2% Grounded confidence against Google Cloud official documentation and historical approved RFIs.",
				"metrics": map[string]interface{}{
					"grounding_fidelity": "98.2% Grounded",
					"total_questions":    121,
					"completed_tabs":     4,
				},
				"actions": []map[string]interface{}{
					{"action_id": "download_rfi_md", "label": "Download Completed RFI (Markdown)", "primary": false},
					{"action_id": "download_rfi_csv", "label": "Download Completed RFI (CSV)", "primary": false},
					{"action_id": "open_demo_sandboxes", "label": "Advance to Phase 5: Demo Sandboxes", "primary": true},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase5Surface() string {
	tracker := g.BuildProgressTracker(5)

	surface := map[string]interface{}{
		"surface_id":       "phase5_demo",
		"card_id":          "card-demo-sandbox",
		"phase":            5,
		"progress_percent": 71.0,
		"title":            "Phase 5: On-Demand Demo Environments & Storyboard Playbook",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 5: On-Demand Demo Environments & Storyboard Playbook",
				"subtitle":    "Step 5: Demonstration Sandboxes & Script Synthesis",
				"description": "On-demand demo sandboxes deployed. Full step-by-step storyboard playbooks synthesized with timecoded table of contents bookmarks.",
				"actions": []map[string]interface{}{
					{"action_id": "download_demo_playbook", "label": "Download Demo Script Playbook (.md)", "primary": false},
					{"action_id": "open_executive_review", "label": "Advance to Phase 6: Executive Review", "primary": true},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase6Surface() string {
	tracker := g.BuildProgressTracker(6)

	surface := map[string]interface{}{
		"surface_id":       "phase6_review",
		"card_id":          "card-executive-review",
		"phase":            6,
		"progress_percent": 86.0,
		"title":            "Phase 6: Executive Review Panel & GA Deficit Attestation Waivers",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 6: Executive Review Panel & GA Deficit Attestation Waivers",
				"subtitle":    "Step 6: Executive Attestation & Dual-Custody Governance",
				"description": "Executive review dossier generated. Dual-custody Deficit Attestation Waiver approved by Product GM and Legal Counsel for preview features.",
				"actions": []map[string]interface{}{
					{"action_id": "download_executive_memo", "label": "Download Executive Waiver Memo (.md)", "primary": false},
					{"action_id": "open_publication_recognition", "label": "Advance to Phase 7: Master Portal Publication", "primary": true},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GeneratePhase7Surface() string {
	tracker := g.BuildProgressTracker(7)

	surface := map[string]interface{}{
		"surface_id":       "phase7_publication",
		"card_id":          "card-publication-recognition",
		"phase":            7,
		"progress_percent": 100.0,
		"title":            "Phase 7: Master Portal Publication & Contributor Recognition Manifesto",
		"components": append(tracker, map[string]interface{}{
			"type": "Card",
			"properties": map[string]interface{}{
				"title":       "Phase 7: Master Portal Publication & Contributor Recognition Manifesto",
				"subtitle":    "Step 7: Portal Upload & Leadership Recognition",
				"description": "All 7 lifecycle phases 100% complete! Master portal submission package ready for upload.",
				"actions": []map[string]interface{}{
					{"action_id": "download_publication_bundle", "label": "Download Final Publication Bundle (.md)", "primary": false},
				},
			},
		}),
	}
	return g.WrapInA2UITags(surface)
}

func (g *A2UIGenerator) GenerateGovernanceRadarSurface(report map[string]interface{}) string {
	surface := map[string]interface{}{
		"surface_id": "governance_radar",
		"title":      "Enterprise AI Governance Radar & Compliance Scorecard",
		"components": []map[string]interface{}{
			{
				"type": "Card",
				"properties": map[string]interface{}{
					"title":       "Enterprise AI Governance Radar & Compliance Scorecard",
					"subtitle":    "Model Armor, DLP Inspection & Dual-Custody Deficit Attestations",
					"report_data": report,
					"actions": []map[string]interface{}{
						{"action_id": "sign_executive_waiver", "label": "Executive Dual-Custody Sign-Off", "primary": true},
						{"action_id": "export_audit_bundle", "label": "Export Audit Bundle (PDF/MD)", "primary": false},
					},
				},
			},
		},
	}
	return g.WrapInA2UITags(surface)
}
