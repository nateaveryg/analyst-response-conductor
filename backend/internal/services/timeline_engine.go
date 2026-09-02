package services

import (
	"fmt"
	"time"
)

type ExclusionWindow struct {
	Name      string    `json:"name"`
	StartDate time.Time `json:"start_date"`
	EndDate   time.Time `json:"end_date"`
}

type Milestone struct {
	Name             string    `json:"name"`
	OffsetDays       int       `json:"offset_days"`
	TargetDate       time.Time `json:"target_date"`
	OperationalPhase string    `json:"operational_phase"`
	Shifted          bool      `json:"shifted"`
	ShiftReason      string    `json:"shift_reason"`
	LeadRole         string    `json:"lead_role"`
}

type WorkbackTimeline struct {
	TargetDeadline   time.Time         `json:"target_deadline"`
	Milestones       []Milestone       `json:"milestones"`
	ExclusionWindows []ExclusionWindow `json:"exclusion_windows"`
}

type TimelineEngine struct{}

func NewTimelineEngine() *TimelineEngine {
	return &TimelineEngine{}
}

func (e *TimelineEngine) GenerateTimeline(targetDeadline time.Time, exclusions []ExclusionWindow) *WorkbackTimeline {
	if targetDeadline.IsZero() {
		targetDeadline = time.Date(2026, 6, 20, 17, 0, 0, 0, time.UTC)
	}

	if len(exclusions) == 0 {
		exclusions = []ExclusionWindow{
			{
				Name:      "Cloud Next 2026 Conference Freeze",
				StartDate: time.Date(2026, 6, 14, 0, 0, 0, 0, time.UTC),
				EndDate:   time.Date(2026, 6, 16, 23, 59, 59, 0, time.UTC),
			},
		}
	}

	baseMilestones := []struct {
		Name     string
		Offset   int
		Phase    string
		LeadRole string
	}{
		{"Portfolio Eligibility & Go/No-Go Decision Review", 20, "1. Evaluate Inclusion Criteria & Strategic Participation", "OPM & AR Leads"},
		{"Automated Workback Schedule Generation & Routing", 19, "2. Auto-Generate Schedules & Assign Tasks", "Analyst Response Agent (ARA)"},
		{"Stakeholder Kickoff & OPM/SME Workstream Alignment", 18, "3. Kick Off Response Project & Align Teams", "pm-leadership@ & opm-coordinator@"},
		{"Automated RAG Ingestion & Draft Pre-population", 16, "4. Generate Initial RFI Responses", "Analyst Response Agent (ARA)"},
		{"Initial SME Curation Draft & Technical Sign-Off", 15, "4. Generate Initial RFI Responses", "Domain SMEs"},
		{"Storyboard Freeze & On-Demand Demo Sandbox Deployment", 12, "5. Deploy On-Demand Demo Environments", "DevSecOps Engineers & SMEs"},
		{"Demo Script Rehearsal & Dry-Run", 10, "5. Deploy On-Demand Demo Environments", "Domain SMEs (devops, sec)"},
		{"Consolidated OPM/SME Technical Review Session", 9, "5. Deploy On-Demand Demo Environments", "OPM & Technical SMEs"},
		{"Final Video Recording & TOC Bookmark Verification", 8, "5. Deploy On-Demand Demo Environments", "opm-coordinator@ & SMEs"},
		{"Executive Approval Panel Review & Waiver Requests", 5, "6. Manage Executive Reviews & Address Inaccuracies", "Executive Review Panel"},
		{"Final QA, Packaging, and Form Submission", 2, "6. Manage Executive Reviews & Address Inaccuracies", "Portal Administrator & Legal"},
		{"Master Portal Upload, Publication & Recognition", 0, "7. Finalize Publication Strategy & Recognize Contributors", "Portal Administrator"},
	}

	var milestones []Milestone
	for _, m := range baseMilestones {
		targetDate := targetDeadline.AddDate(0, 0, -m.Offset)
		shifted := false
		shiftReason := ""

		for _, exc := range exclusions {
			if !targetDate.Before(exc.StartDate) && !targetDate.After(exc.EndDate) {
				daysToShift := int(targetDate.Sub(exc.StartDate).Hours()/24) + 1
				targetDate = exc.StartDate.AddDate(0, 0, -1)
				shifted = true
				shiftReason = fmt.Sprintf("Shifted %d day(s) earlier to avoid %s", daysToShift, exc.Name)
				break
			}
		}

		milestones = append(milestones, Milestone{
			Name:             m.Name,
			OffsetDays:       m.Offset,
			TargetDate:       targetDate,
			OperationalPhase: m.Phase,
			Shifted:          shifted,
			ShiftReason:      shiftReason,
			LeadRole:         m.LeadRole,
		})
	}

	return &WorkbackTimeline{
		TargetDeadline:   targetDeadline,
		Milestones:       milestones,
		ExclusionWindows: exclusions,
	}
}
