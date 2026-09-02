package governance

import (
	"context"
	"fmt"
	"regexp"
	"strings"
)

const DefaultGroundingThreshold = 0.85

type ModelArmorFilter struct {
	emailPattern         *regexp.Regexp
	unreleasedSkuPattern *regexp.Regexp
	ssnPattern           *regexp.Regexp
	groundingThreshold   float64
}

func NewModelArmorFilter() *ModelArmorFilter {
	return &ModelArmorFilter{
		emailPattern:         regexp.MustCompile(`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`),
		unreleasedSkuPattern: regexp.MustCompile(`(?i)(?:(?:(?:unreleased|internal|confidential|secret)[:=\-\s_]+)?(?:partner[:=\-\s_]+)?(?:discounts?|pricings?|margins?|rebates?)(?:[:=\-\s_]*(?:(?:is|are|of)[:=\-\s_]+)?(?:\(\s*\d+(?:\.\d+)?\s*%\s*\)|\d+(?:\.\d+)?\s*%|\$\s*\d+(?:\.\d+)?(?:\/\w+)?))?|(?:(?:unreleased|internal|confidential|secret)[:=\-\s_]+)?custom[:=\-\s_]+seller[:=\-\s_]+deal|\b\d+(?:\.\d+)?\s*%\s*(?:internal|confidential)?\s*margins?|\b\d+(?:\.\d+)?\s*%\s+on\s+compute\s+margins?|\bmargins?\s*(?:(?:is|are|of)[:=\-\s_]+)?(?:\(\s*\d+(?:\.\d+)?\s*%\s*\)|\d+(?:\.\d+)?\s*%))`),
		ssnPattern:           regexp.MustCompile(`\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b`),
		groundingThreshold:   DefaultGroundingThreshold,
	}
}

func (m *ModelArmorFilter) InspectPrompt(ctx context.Context, text string) (string, error) {
	if text == "" {
		return "", nil
	}

	if m.ContainsBlockedPatterns(text) {
		return "", fmt.Errorf("BLOCKED: Prompt contains forbidden injection patterns or malicious script payload")
	}

	// Redact non-Google PII emails
	sanitized := m.emailPattern.ReplaceAllStringFunc(text, func(match string) string {
		if strings.HasSuffix(strings.ToLower(match), "@google.com") {
			return match
		}
		return "[REDACTED_PII]"
	})

	sanitized = m.ssnPattern.ReplaceAllString(sanitized, "[REDACTED_SSN]")
	sanitized = m.unreleasedSkuPattern.ReplaceAllString(sanitized, "[CONFIDENTIAL_COMMERCIAL_RATE]")

	return sanitized, nil
}

func (m *ModelArmorFilter) InspectOutput(ctx context.Context, text string) (string, error) {
	if text == "" {
		return "", nil
	}
	// Redact PII or leaked confidential rate tokens from generated model outputs
	sanitized := m.emailPattern.ReplaceAllStringFunc(text, func(match string) string {
		if strings.HasSuffix(strings.ToLower(match), "@google.com") {
			return match
		}
		return "[REDACTED_PII]"
	})
	sanitized = m.ssnPattern.ReplaceAllString(sanitized, "[REDACTED_SSN]")
	sanitized = m.unreleasedSkuPattern.ReplaceAllString(sanitized, "[CONFIDENTIAL_COMMERCIAL_RATE]")
	return sanitized, nil
}

func (m *ModelArmorFilter) VerifyGroundingScore(score float64) error {
	if score < m.groundingThreshold {
		return fmt.Errorf("grounding score %.2f (%.1f%%) is below required enterprise compliance threshold %.2f (%.1f%%)",
			score, score*100, m.groundingThreshold, m.groundingThreshold*100)
	}
	return nil
}

func (m *ModelArmorFilter) ValidateComplianceGating(score float64, activeWaivers []DeficitAttestationWaiver) (bool, string) {
	if err := m.VerifyGroundingScore(score); err != nil {
		hasApprovedWaiver := false
		for _, w := range activeWaivers {
			if w.IsApproved {
				hasApprovedWaiver = true
				break
			}
		}
		if !hasApprovedWaiver {
			return false, fmt.Sprintf("BLOCKED: %s. An approved Deficit Attestation Waiver is required.", err.Error())
		}
		return true, "ALLOWED_WITH_APPROVED_WAIVER: Grounding score below threshold but dual-custody waiver is active."
	}
	return true, "COMPLIANT: Output meets all grounding fidelity and DLP safety standards."
}

func (m *ModelArmorFilter) ContainsBlockedPatterns(text string) bool {
	lower := strings.ToLower(text)
	return strings.Contains(lower, "drop table ") ||
		strings.Contains(lower, "<script>") ||
		strings.Contains(lower, "javascript:") ||
		strings.Contains(lower, "union select ") ||
		strings.Contains(lower, "exec xp_")
}
