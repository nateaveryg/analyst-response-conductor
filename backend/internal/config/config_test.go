package config

import (
	"os"
	"testing"
)

func TestLoadConfig_Defaults(t *testing.T) {
	// Clean environment
	origVersion := os.Getenv("SERVICE_VERSION")
	origMarker := os.Getenv("VERIFICATION_MARKER")
	origPort := os.Getenv("PORT")
	origEnv := os.Getenv("ENVIRONMENT")
	defer func() {
		os.Setenv("SERVICE_VERSION", origVersion)
		os.Setenv("VERIFICATION_MARKER", origMarker)
		os.Setenv("PORT", origPort)
		os.Setenv("ENVIRONMENT", origEnv)
	}()

	os.Unsetenv("SERVICE_VERSION")
	os.Unsetenv("VERIFICATION_MARKER")
	os.Unsetenv("PORT")
	os.Unsetenv("ENVIRONMENT")

	cfg := LoadConfig()
	if cfg.Version != "3.3.2" {
		t.Errorf("expected default Version '3.3.2', got %q", cfg.Version)
	}
	if cfg.VerificationMarker != "v3.3.2-verified" {
		t.Errorf("expected default VerificationMarker 'v3.3.2-verified', got %q", cfg.VerificationMarker)
	}
	if cfg.Port != "8080" {
		t.Errorf("expected default Port '8080', got %q", cfg.Port)
	}
	if cfg.Environment != "production" {
		t.Errorf("expected default Environment 'production', got %q", cfg.Environment)
	}
	if cfg.AgentRuntime != "cloud-run" {
		t.Errorf("expected default AgentRuntime 'cloud-run', got %q", cfg.AgentRuntime)
	}
}

func TestLoadConfig_EnvironmentOverrides(t *testing.T) {
	origVersion := os.Getenv("SERVICE_VERSION")
	origMarker := os.Getenv("VERIFICATION_MARKER")
	origPort := os.Getenv("PORT")
	origEnv := os.Getenv("ENVIRONMENT")
	origRuntime := os.Getenv("AGENT_RUNTIME")
	origMaxConns := os.Getenv("POOL_MAX_CONNS")
	defer func() {
		os.Setenv("SERVICE_VERSION", origVersion)
		os.Setenv("VERIFICATION_MARKER", origMarker)
		os.Setenv("PORT", origPort)
		os.Setenv("ENVIRONMENT", origEnv)
		os.Setenv("AGENT_RUNTIME", origRuntime)
		os.Setenv("POOL_MAX_CONNS", origMaxConns)
	}()

	os.Setenv("SERVICE_VERSION", "3.3.1-custom-rc1")
	os.Setenv("VERIFICATION_MARKER", "custom-verification-marker-42")
	os.Setenv("PORT", "9090")
	os.Setenv("ENVIRONMENT", "staging")
	os.Setenv("AGENT_RUNTIME", "go-cloud-run")
	os.Setenv("POOL_MAX_CONNS", "25")

	cfg := LoadConfig()
	if cfg.Version != "3.3.1-custom-rc1" {
		t.Errorf("expected overridden Version '3.3.1-custom-rc1', got %q", cfg.Version)
	}
	if cfg.VerificationMarker != "custom-verification-marker-42" {
		t.Errorf("expected overridden VerificationMarker 'custom-verification-marker-42', got %q", cfg.VerificationMarker)
	}
	if cfg.Port != "9090" {
		t.Errorf("expected overridden Port '9090', got %q", cfg.Port)
	}
	if cfg.Environment != "staging" {
		t.Errorf("expected overridden Environment 'staging', got %q", cfg.Environment)
	}
	if cfg.AgentRuntime != "go-cloud-run" {
		t.Errorf("expected overridden AgentRuntime 'go-cloud-run', got %q", cfg.AgentRuntime)
	}
	if cfg.PoolMaxConns != 25 {
		t.Errorf("expected overridden PoolMaxConns 25, got %d", cfg.PoolMaxConns)
	}
}

func TestLoadConfig_EmptyEnvFallback(t *testing.T) {
	origVersion := os.Getenv("SERVICE_VERSION")
	origMarker := os.Getenv("VERIFICATION_MARKER")
	defer func() {
		os.Setenv("SERVICE_VERSION", origVersion)
		os.Setenv("VERIFICATION_MARKER", origMarker)
	}()

	os.Setenv("SERVICE_VERSION", "")
	os.Setenv("VERIFICATION_MARKER", "")

	cfg := LoadConfig()
	if cfg.Version != "3.3.2" {
		t.Errorf("expected empty string fallback to '3.3.2', got %q", cfg.Version)
	}
	if cfg.VerificationMarker != "v3.3.2-verified" {
		t.Errorf("expected empty string fallback to 'v3.3.2-verified', got %q", cfg.VerificationMarker)
	}
}
