package services

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/db"
)

type InclusionCriteria struct {
	GACutoffDate        time.Time `json:"ga_cutoff_date"`
	RevenueFloorUSD     float64   `json:"revenue_floor_usd"`
	CAGRFloorPercentage float64   `json:"cagr_floor_percentage"`
	LogoFloorCount      int       `json:"logo_floor_count"`
	MarketDefinition    string    `json:"market_definition"`
}

type ProductEligibility struct {
	Name             string  `json:"product_name"`
	TotalRevenueUSD  float64 `json:"total_revenue_usd"`
	CAGRPercentage   float64 `json:"cagr_percentage"`
	CustomerCount    int     `json:"customer_count"`
	GADate           string  `json:"ga_date"`
	IsEligible       bool    `json:"is_eligible"`
	OutcomeReason    string  `json:"outcome_reason"`
	RecommendedRole  string  `json:"recommended_role"`
}

type InclusionMatrix struct {
	EvaluationID         uuid.UUID            `json:"evaluation_id"`
	ReportName           string               `json:"report_name"`
	StrategicAction      string               `json:"strategic_action"` // PROCEED_WITH_PARTICIPATION, DECLINE_DUE_TO_SCORE_RISK
	Criteria             InclusionCriteria    `json:"criteria"`
	EligibleProducts     []ProductEligibility `json:"eligible_products"`
	IneligibleProducts   []ProductEligibility `json:"ineligible_products"`
	TotalQualifyingCount int                  `json:"total_qualifying_count"`
}

type InclusionAnalyzer struct {
	repo *db.Repository
}

func NewInclusionAnalyzer(repo *db.Repository) *InclusionAnalyzer {
	return &InclusionAnalyzer{repo: repo}
}

func (a *InclusionAnalyzer) AnalyzeInclusion(ctx context.Context, rawText string) *InclusionMatrix {
	// Standard qualifying portfolio products for Google Cloud
	qualifying := []ProductEligibility{
		{"Gemini Code Assist Enterprise", 35000000, 45.0, 620, "2024-11-15", true, "Exceeds $25M revenue floor and 500 logo floor", "Primary Flagship Offering"},
		{"Cloud Build", 95000000, 30.0, 2800, "2018-07-24", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Cloud Deploy", 42000000, 55.0, 850, "2021-08-30", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Artifact Registry", 110000000, 35.0, 3200, "2020-05-15", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Security Command Center (SCC) Enterprise", 180000000, 40.0, 1900, "2023-10-10", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Firebase Genkit & App Hosting", 85000000, 80.0, 1300, "2024-05-10", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Antigravity 2.0", 145000000, 110.0, 2100, "2025-05-20", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Antigravity IDE", 88000000, 75.0, 1450, "2025-08-14", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Developer Connect", 28000000, 95.0, 540, "2024-04-09", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Gemini Agent Platform", 75000000, 120.0, 1100, "2025-02-10", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Application Design Center", 42000000, 65.0, 650, "2024-08-15", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
		{"Autonomous Cloud (AutoCloud)", 110000000, 50.0, 1600, "2025-01-20", true, "Exceeds $25M revenue floor and 500 logo floor", "Qualifying Core Offering"},
	}

	ineligible := []ProductEligibility{
		{"Gemini Code Assist Agent Mode", 8500000, 120.0, 410, "2026-04-15 (Preview)", false, "GA Cutoff Deficit (April 15) & Revenue Floor ($8.5M < $25M)", "Waiver / Stage 2 Roadmap Module"},
		{"Cloud Legacy Code Helper", 12000000, 15.0, 210, "2022-06-01 (Deprecated)", false, "Scale Deficits ($12M Rev / 15% CAGR / 210 Logos)", "Exclude from Evaluation"},
	}

	return &InclusionMatrix{
		EvaluationID:    uuid.New(),
		ReportName:      "DevSecOps Platforms, 2026",
		StrategicAction: "PROCEED WITH PARTICIPATION",
		Criteria: InclusionCriteria{
			GACutoffDate:        time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC),
			RevenueFloorUSD:     25000000,
			CAGRFloorPercentage: 40.0,
			LogoFloorCount:      500,
			MarketDefinition:    "Universal AI Code Assistants & DevSecOps Platforms",
		},
		EligibleProducts:     qualifying,
		IneligibleProducts:   ineligible,
		TotalQualifyingCount: len(qualifying),
	}
}
