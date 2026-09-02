package governance

import (
	"context"
	"strings"
	"testing"
)

func TestModelArmorDLP(t *testing.T) {
	armor := NewModelArmorFilter()
	ctx := context.Background()

	t.Run("Redacts non-Google PII emails", func(t *testing.T) {
		prompt := "Please share the report with analyst customer.lead@external-firm.com immediately."
		sanitized, err := armor.InspectPrompt(ctx, prompt)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if strings.Contains(sanitized, "customer.lead@external-firm.com") {
			t.Errorf("expected PII to be redacted, got: %s", sanitized)
		}
		if !strings.Contains(sanitized, "[REDACTED_PII]") {
			t.Errorf("expected [REDACTED_PII] placeholder, got: %s", sanitized)
		}
	})

	t.Run("Preserves internal Google emails", func(t *testing.T) {
		prompt := "Assigned to bradcalder@google.com and averyn@google.com for review."
		sanitized, err := armor.InspectPrompt(ctx, prompt)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !strings.Contains(sanitized, "bradcalder@google.com") || !strings.Contains(sanitized, "averyn@google.com") {
			t.Errorf("expected Google emails to be preserved, got: %s", sanitized)
		}
	})

	t.Run("Redacts unreleased confidential discounts and internal margins including hyphenated variants", func(t *testing.T) {
		prompts := []string{
			"Offering a confidential discount of 35% with an internal margin target of 60%.",
			"Special confidential-discount applies with custom-seller-deal parameters.",
			"Check the secret_rebate calculation for enterprise accounts.",
			"Please include confidential pricing for client: internal margin is 72%, secret partner discount is 45%, and contact SSN is 000-12-3456.",
		}
		for _, p := range prompts {
			sanitized, err := armor.InspectPrompt(ctx, p)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !strings.Contains(sanitized, "[CONFIDENTIAL_COMMERCIAL_RATE]") {
				t.Errorf("expected [CONFIDENTIAL_COMMERCIAL_RATE] placeholder in: %s", sanitized)
			}
		}
	})

	t.Run("Redacts commercial discounts with colon and equals punctuation delimiters", func(t *testing.T) {
		prompts := []string{
			"Proposal note: secret partner discount: 45% applied to pricing.",
			"Financial margin: internal margin: 72% on compute workloads.",
			"Summary: secret partner discount = 45% and confidential pricing = 30%.",
			"Check: confidential-discount: 50% with internal-margin = 65%.",
		}
		leakedFragments := []string{": 45%", "= 45%", ": 72%", "= 30%", ": 50%", "= 65%"}

		for _, p := range prompts {
			sanitized, err := armor.InspectPrompt(ctx, p)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !strings.Contains(sanitized, "[CONFIDENTIAL_COMMERCIAL_RATE]") {
				t.Errorf("expected [CONFIDENTIAL_COMMERCIAL_RATE] placeholder in: %s", sanitized)
			}
			for _, leak := range leakedFragments {
				if strings.Contains(sanitized, leak) {
					t.Errorf("rate fragment leaked in sanitized output: '%s' in '%s'", leak, sanitized)
				}
			}
		}
	})

	t.Run("Redacts commercial discounts without adjective prefixes across all punctuation delimiters", func(t *testing.T) {
		prompts := []string{
			"Security probe: partner discount: 45%.",
			"Security probe: partner discount = 45%.",
			"Security probe: partner discount is 45%.",
			"Security probe: partner discount of 45%.",
			"Security probe: partner discount (45%).",
			"Security probe: partner discount ( 45% ).",
			"Security probe: PARTNER DISCOUNT = 45%.",
			"Security probe: internal margin is 72%.",
			"Security probe: internal margin: 72%.",
			"Security probe: internal margin = 72%.",
			"Security probe: confidential discount is 30%.",
			"Security probe: confidential discount: 30%.",
			"Security probe: confidential discount = 30%.",
			"Security probe: unreleased pricing: $50/hour.",
		}
		leakedFragments := []string{": 45%", "= 45%", "is 45%", "of 45%", "(45%)", " 45%", ": 72%", "= 72%", "is 72%", ": 30%", "= 30%", "is 30%", "$50/hour"}

		for _, p := range prompts {
			sanitized, err := armor.InspectPrompt(ctx, p)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !strings.Contains(sanitized, "[CONFIDENTIAL_COMMERCIAL_RATE]") {
				t.Errorf("expected [CONFIDENTIAL_COMMERCIAL_RATE] placeholder in: %s", sanitized)
			}
			if strings.Contains(strings.ToLower(sanitized), "partner discount") {
				t.Errorf("raw partner discount term leaked: %s", sanitized)
			}
			for _, leak := range leakedFragments {
				if strings.Contains(sanitized, leak) {
					t.Errorf("rate fragment leaked in sanitized output: '%s' in '%s'", leak, sanitized)
				}
			}
		}
	})

	t.Run("Blocks malicious SQL injection and XSS payloads", func(t *testing.T) {
		malicious := []string{
			"SELECT * FROM workspaces; DROP TABLE workspaces; --",
			"<script>alert('pwned')</script>",
			"javascript:evil()",
		}
		for _, m := range malicious {
			_, err := armor.InspectPrompt(ctx, m)
			if err == nil {
				t.Errorf("expected error blocking malicious input '%s', got nil", m)
			}
		}
	})
}

func TestGroundingScoreThresholdGate(t *testing.T) {
	armor := NewModelArmorFilter()

	t.Run("Rejects grounding score below 85%", func(t *testing.T) {
		err := armor.VerifyGroundingScore(0.82)
		if err == nil {
			t.Errorf("expected error for grounding score 0.82 < 0.85, got nil")
		}
		if !strings.Contains(err.Error(), "below required enterprise compliance threshold") {
			t.Errorf("unexpected error message: %v", err)
		}
	})

	t.Run("Accepts grounding score at or above 85%", func(t *testing.T) {
		if err := armor.VerifyGroundingScore(0.85); err != nil {
			t.Errorf("expected score 0.85 to pass, got: %v", err)
		}
		if err := armor.VerifyGroundingScore(0.985); err != nil {
			t.Errorf("expected score 0.985 to pass, got: %v", err)
		}
	})

	t.Run("Allows low score with approved dual-custody waiver", func(t *testing.T) {
		waivers := []DeficitAttestationWaiver{
			{
				FeatureName: "Gemini Code Assist Agent Mode",
				IsApproved:  true,
			},
		}
		allowed, reason := armor.ValidateComplianceGating(0.80, waivers)
		if !allowed {
			t.Errorf("expected allowed=true with approved waiver, got false")
		}
		if !strings.Contains(reason, "ALLOWED_WITH_APPROVED_WAIVER") {
			t.Errorf("unexpected reason: %s", reason)
		}
	})
}

func TestCryptographicProvenanceAndHMAC(t *testing.T) {
	engine := NewProvenanceEngine("test-secret-key-12345")

	chunks := []GroundingChunk{
		{
			SourceRfiTitle:   "Google Cloud Run Master Architecture 2026",
			SheetTabName:     "Tab 1: Runtimes",
			RowIndex:         1,
			CosineSimilarity: 0.99,
			Excerpt:          "Sub-50ms cold starts with distroless container binaries.",
		},
	}

	prov := engine.StampProvenance(
		"resp-001",
		"gemini-3.5-flash@2026-08",
		"System Prompt: Universal Analyst Reasoning",
		chunks,
		0.985,
		true,
	)

	if prov.SignatureToken == "" {
		t.Fatalf("expected signature token to be generated")
	}

	if !engine.VerifySignature(prov) {
		t.Errorf("expected signature verification to pass")
	}

	// Tampering test on score
	tampered := *prov
	tampered.GroundingConfidenceScore = 0.50
	if engine.VerifySignature(&tampered) {
		t.Errorf("expected tampered provenance signature verification to fail")
	}

	// Tampering test on prompt hash
	tamperedPrompt := *prov
	tamperedPrompt.SystemPromptSHA256 = "0000000000000000000000000000000000000000000000000000000000000000"
	if engine.VerifySignature(&tamperedPrompt) {
		t.Errorf("expected tampered prompt hash signature verification to fail")
	}
}

func TestDualCustodyWaiverLifecycle(t *testing.T) {
	svc := NewWaiverService()

	w := svc.CreateWaiver(DeficitAttestationWaiver{
		WorkspaceID:        "ws-test-1",
		FeatureName:        "Test Feature Preview",
		CurrentStatus:      "PUBLIC_PREVIEW",
		TargetGADate:       "2026-05-01",
		FallbackMitigation: "Roadmap module demo",
	})

	if w.IsApproved {
		t.Errorf("expected unsigned waiver to not be approved")
	}

	// Step 1: Sign by Product GM
	w1, err := svc.SignWaiver(w.WaiverID, "bradcalder@google.com", "PRODUCT_GM")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if w1.IsApproved {
		t.Errorf("expected single-signed waiver to not yet be approved")
	}

	// Step 2: Sign by Legal Counsel
	w2, err := svc.SignWaiver(w.WaiverID, "ar-counsel@google.com", "LEGAL_COUNSEL")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !w2.IsApproved {
		t.Errorf("expected dual-signed waiver to be approved")
	}
	if w2.ManifestSHA256 == "" {
		t.Errorf("expected manifest SHA-256 hash to be calculated")
	}
}
