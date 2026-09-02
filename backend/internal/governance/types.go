package governance

import "time"

type DeficitAttestationWaiver struct {
	WaiverID              string    `json:"waiver_id"`
	WorkspaceID           string    `json:"workspace_id"`
	FeatureName           string    `json:"feature_name"`
	CurrentStatus         string    `json:"current_status"` // "PUBLIC_PREVIEW", "EARLY_GA", "ROADMAP"
	TargetGADate          string    `json:"target_ga_date"`
	FallbackMitigation    string    `json:"fallback_mitigation"`
	ProductGMApprover     string    `json:"product_gm_approver"`
	LegalCounselApprover  string    `json:"legal_counsel_approver"`
	ApprovedAtTimestamp   time.Time `json:"approved_at_timestamp"`
	IsApproved            bool      `json:"is_approved"`
	ManifestSHA256        string    `json:"manifest_sha256"`
}

type GroundingChunk struct {
	SourceRfiTitle   string  `json:"source_rfi_title"`
	SheetTabName     string  `json:"sheet_tab_name"`
	RowIndex         int     `json:"row_index"`
	CosineSimilarity float64 `json:"cosine_similarity"`
	Excerpt          string  `json:"excerpt"`
}

type CryptographicProvenance struct {
	ProvenanceID             string           `json:"provenance_id"`
	ResponseID               string           `json:"response_id"`
	ModelVersion             string           `json:"model_version"` // e.g. "gemini-3.5-flash@2026-08"
	SystemPromptSHA256       string           `json:"system_prompt_sha256"`
	SourceChunks             []GroundingChunk `json:"source_chunks"`
	GroundingConfidenceScore float64          `json:"grounding_confidence_score"`
	ModelArmorPassed         bool             `json:"model_armor_passed"`
	GeneratedAt              time.Time        `json:"generated_at"`
	SignatureToken           string           `json:"signature_token"`
}

type GovernanceRadarReport struct {
	WorkspaceID                 string                     `json:"workspace_id"`
	OverallComplianceScore      float64                    `json:"overall_compliance_score"`
	RagGroundingFidelity        float64                    `json:"rag_grounding_fidelity"`
	ActiveWaiversCount          int                        `json:"active_waivers_count"`
	WaiversApproved             bool                       `json:"waivers_approved"`
	SovereignResidencyCompliant bool                       `json:"sovereign_residency_compliant"`
	SovereignRegion             string                     `json:"sovereign_region"`
	OSSLicensesCleared          bool                       `json:"oss_licenses_cleared"`
	CommercialRatesVerified     bool                       `json:"commercial_rates_verified"`
	Waivers                     []DeficitAttestationWaiver `json:"waivers"`
	AuditBundleGeneratedAt      time.Time                  `json:"audit_bundle_generated_at"`
}
