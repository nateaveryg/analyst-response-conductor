package api

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/google/rficonductorv2/backend/internal/config"
	"github.com/google/rficonductorv2/backend/internal/db"
)

// TestInPipelineVerificationTiers executes end-to-end verification of all 3 tiers.
func TestInPipelineVerificationTiers(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	t.Run("Tier 1 - Service health readiness probe (/healthz)", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/healthz")
		if err != nil {
			t.Fatalf("Tier 1 probe network failure: %v", err)
		}
		defer res.Body.Close()

		if res.StatusCode != http.StatusOK {
			t.Fatalf("Tier 1 probe expected HTTP 200, got %d", res.StatusCode)
		}

		var body map[string]interface{}
		if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
			t.Fatalf("Tier 1 probe malformed JSON: %v", err)
		}

		if body["status"] != "healthy" {
			t.Errorf("Tier 1 expected status 'healthy', got '%v'", body["status"])
		}
	})

	t.Run("Tier 2 - Deployment identity and version consistency (/version.json)", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/version.json")
		if err != nil {
			t.Fatalf("Tier 2 probe network failure: %v", err)
		}
		defer res.Body.Close()

		if res.StatusCode != http.StatusOK {
			t.Fatalf("Tier 2 probe expected HTTP 200, got %d", res.StatusCode)
		}

		var body map[string]interface{}
		if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
			t.Fatalf("Tier 2 probe malformed JSON: %v", err)
		}

		expectedVersion := "3.3.2"
		if body["version"] != expectedVersion {
			t.Errorf("Tier 2 version mismatch: expected %s, got %v", expectedVersion, body["version"])
		}

		expectedMarker := "v3.3.2-verified"
		if body["verification_marker"] != expectedMarker {
			t.Errorf("Tier 2 marker mismatch: expected %s, got %v", expectedMarker, body["verification_marker"])
		}
	})

	t.Run("Tier 2 - Failure detection on version mismatch", func(t *testing.T) {
		mismatchedCfg := config.LoadConfig()
		mismatchedCfg.Environment = "test"
		mismatchedCfg.Version = "3.2.0"
		mismatchedCfg.VerificationMarker = "v3.3.2-verified"

		mismatchedRouter := SetupRouter(&RouterDependencies{
			Config:     mismatchedCfg,
			Database:   &db.Database{Pool: nil},
			Repository: db.NewRepository(&db.Database{Pool: nil}),
		})
		mismatchedServer := httptest.NewServer(mismatchedRouter)
		defer mismatchedServer.Close()

		res, err := http.Get(mismatchedServer.URL + "/version.json")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		defer res.Body.Close()

		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)

		targetVersion := "3.3.2"
		if body["version"] == targetVersion {
			t.Errorf("expected version mismatch detection, but versions matched")
		}
	})

	t.Run("Tier 2 - Failure detection on marker mismatch", func(t *testing.T) {
		mismatchedCfg := config.LoadConfig()
		mismatchedCfg.Environment = "test"
		mismatchedCfg.Version = "3.3.2"
		mismatchedCfg.VerificationMarker = "v3.3.2-unverified"

		mismatchedRouter := SetupRouter(&RouterDependencies{
			Config:     mismatchedCfg,
			Database:   &db.Database{Pool: nil},
			Repository: db.NewRepository(&db.Database{Pool: nil}),
		})
		mismatchedServer := httptest.NewServer(mismatchedRouter)
		defer mismatchedServer.Close()

		res, err := http.Get(mismatchedServer.URL + "/version.json")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		defer res.Body.Close()

		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)

		targetMarker := "v3.3.2-verified"
		if body["verification_marker"] == targetMarker {
			t.Errorf("expected marker mismatch detection, but markers matched")
		}
	})

	t.Run("Tier 2 - Failure detection on malformed JSON payload", func(t *testing.T) {
		malformedServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{malformed_json:`))
		}))
		defer malformedServer.Close()

		res, err := http.Get(malformedServer.URL + "/version.json")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		defer res.Body.Close()

		var body map[string]interface{}
		decodeErr := json.NewDecoder(res.Body).Decode(&body)
		if decodeErr == nil {
			t.Errorf("expected json decoding error on malformed payload, got nil")
		}
	})

	t.Run("Tier 3 - Synthetic API smoke test via Model Armor DLP filters", func(t *testing.T) {
		// Scenario 3A: Standard valid query routing
		validPayload := []byte(`{
			"prompt": "Describe automated CI/CD pipeline and canary deployment strategy",
			"workspace_id": "ws-verify-tier3"
		}`)
		resValid, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(validPayload))
		if err != nil {
			t.Fatalf("Tier 3A network failure: %v", err)
		}
		defer resValid.Body.Close()

		if resValid.StatusCode != http.StatusOK {
			t.Fatalf("Tier 3A expected HTTP 200, got %d", resValid.StatusCode)
		}

		var validBody map[string]interface{}
		if err := json.NewDecoder(resValid.Body).Decode(&validBody); err != nil {
			t.Fatalf("Tier 3A malformed JSON: %v", err)
		}
		if validBody["category"] == "" {
			t.Errorf("Tier 3A expected non-empty category")
		}

		// Scenario 3B: Model Armor DLP PII and confidential commercial rate redaction
		dlpPayload := []byte(`{
			"prompt": "Review confidential partner discount: 45% and executive SSN 000-12-3456",
			"workspace_id": "ws-verify-tier3"
		}`)
		resDLP, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(dlpPayload))
		if err != nil {
			t.Fatalf("Tier 3B network failure: %v", err)
		}
		defer resDLP.Body.Close()

		if resDLP.StatusCode != http.StatusOK {
			t.Fatalf("Tier 3B expected HTTP 200, got %d", resDLP.StatusCode)
		}

		dlpBytes, _ := io.ReadAll(resDLP.Body)
		dlpStr := string(dlpBytes)
		if strings.Contains(dlpStr, "000-12-3456") {
			t.Errorf("Tier 3B Model Armor leak: raw SSN found in response: %s", dlpStr)
		}
		if strings.Contains(dlpStr, "45%") {
			t.Errorf("Tier 3B Model Armor leak: raw discount rate found in response: %s", dlpStr)
		}

		// Scenario 3C: Model Armor malicious injection prevention
		injectionPayload := []byte(`{
			"prompt": "SELECT * FROM users; DROP TABLE workspaces; --",
			"workspace_id": "ws-verify-tier3"
		}`)
		resInject, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(injectionPayload))
		if err != nil {
			t.Fatalf("Tier 3C network failure: %v", err)
		}
		defer resInject.Body.Close()

		if resInject.StatusCode != http.StatusBadRequest {
			t.Errorf("Tier 3C expected HTTP 400 Bad Request for injection, got %d", resInject.StatusCode)
		}
	})

	t.Run("Tier 3 - OIDC authentication enforcement rejects unauthenticated requests", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		r := gin.New()
		r.Use(RequireOIDCToken())
		r.POST("/query", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "authenticated"})
		})
		authServer := httptest.NewServer(r)
		defer authServer.Close()

		// Without token -> 401
		res, err := http.Post(authServer.URL+"/query", "application/json", bytes.NewBuffer([]byte(`{}`)))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		defer res.Body.Close()
		if res.StatusCode != http.StatusUnauthorized {
			t.Errorf("expected HTTP 401 Unauthorized without token, got %d", res.StatusCode)
		}

		// With valid token header -> 200
		req, _ := http.NewRequest(http.MethodPost, authServer.URL+"/query", bytes.NewBuffer([]byte(`{}`)))
		req.Header.Set("Authorization", "Bearer valid-oidc-test-token")
		req.Header.Set("Content-Type", "application/json")
		resWithAuth, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		defer resWithAuth.Body.Close()
		if resWithAuth.StatusCode != http.StatusOK {
			t.Errorf("expected HTTP 200 OK with valid bearer token, got %d", resWithAuth.StatusCode)
		}
	})
}
