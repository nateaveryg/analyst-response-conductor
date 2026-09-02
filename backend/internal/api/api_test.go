package api

import (
	"bytes"
	"encoding/json"
	"io"
	"mime"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/google/uuid"
	"github.com/google/rficonductorv2/backend/internal/config"
	"github.com/google/rficonductorv2/backend/internal/db"
	"github.com/google/rficonductorv2/backend/internal/observability"
)

func setupTestRouter() *httptest.Server {
	observability.InitLogger()
	cfg := config.LoadConfig()
	cfg.Environment = "test"
	database := &db.Database{Pool: nil}
	repo := db.NewRepository(database)

	router := SetupRouter(&RouterDependencies{
		Config:     cfg,
		Database:   database,
		Repository: repo,
	})

	return httptest.NewServer(router)
}

func TestHealthAndReadinessEndpoints(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	t.Run("GET /health returns 200 healthy", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/health")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["status"] != "healthy" {
			t.Errorf("expected status 'healthy', got %v", body["status"])
		}
		if body["version"] != "3.3.2" {
			t.Errorf("expected version '3.3.2', got %v", body["version"])
		}
		if body["verification_marker"] != "v3.3.2-verified" {
			t.Errorf("expected verification_marker 'v3.3.2-verified', got %v", body["verification_marker"])
		}
	})

	t.Run("GET /ready returns 200 ready", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/ready")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
	})

	t.Run("GET /api/v1/agent-card returns metadata", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/api/v1/agent-card")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["displayName"] != "Analyst Response Agent (ARA)" {
			t.Errorf("unexpected displayName: %v", body["displayName"])
		}
		if body["version"] != "3.3.2" {
			t.Errorf("expected version '3.3.2', got %v", body["version"])
		}
		if body["verification_marker"] != "v3.3.2-verified" {
			t.Errorf("expected verification_marker 'v3.3.2-verified', got %v", body["verification_marker"])
		}
	})

	t.Run("GET /.well-known/agent.json returns standardized metadata with version", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/.well-known/agent.json")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["version"] != "3.3.2" {
			t.Errorf("expected version '3.3.2', got %v", body["version"])
		}
		if body["verification_marker"] != "v3.3.2-verified" {
			t.Errorf("expected verification_marker 'v3.3.2-verified', got %v", body["verification_marker"])
		}
	})

	t.Run("GET /healthz returns 200 healthy with version", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/healthz")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["status"] != "healthy" || body["version"] != "3.3.2" || body["verification_marker"] != "v3.3.2-verified" {
			t.Errorf("unexpected body on /healthz: %v", body)
		}
	})

	t.Run("GET /version.json returns version 3.3.2 and verification marker", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/version.json")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["version"] != "3.3.2" {
			t.Errorf("expected version 3.3.2, got %v", body["version"])
		}
		if body["verification_marker"] != "v3.3.2-verified" {
			t.Errorf("expected verification_marker v3.3.2-verified, got %v", body["verification_marker"])
		}
	})

	t.Run("HEAD requests to metadata endpoints return HTTP 200 without error", func(t *testing.T) {
		headPaths := []string{
			"/",
			"/health",
			"/healthz",
			"/ready",
			"/version.json",
			"/api/v1/agent-card",
			"/.well-known/agent.json",
			"/getAgentCard",
			"/api/v1/agent-engine/card",
			"/api/v1/agent-engine/getAgentCard",
			"/api/v1/workspaces",
			"/api/v1/artifacts",
			"/api/v1/governance/scorecard",
			"/api/v1/export/deep-dive-report",
			"/api/v1/stream/telemetry",
		}
		for _, p := range headPaths {
			req, err := http.NewRequest(http.MethodHead, ts.URL+p, nil)
			if err != nil {
				t.Fatalf("failed to create HEAD request for %s: %v", p, err)
			}
			res, err := http.DefaultClient.Do(req)
			if err != nil {
				t.Fatalf("unexpected error on HEAD %s: %v", p, err)
			}
			if res.StatusCode != http.StatusOK {
				t.Errorf("expected 200 on HEAD %s, got %d", p, res.StatusCode)
			}
		}
	})

	t.Run("Dynamic config overrides propagate to /health, /version.json, and agent card", func(t *testing.T) {
		customCfg := config.LoadConfig()
		customCfg.Environment = "test"
		customCfg.Version = "3.3.2-custom-override"
		customCfg.VerificationMarker = "marker-override-xyz"

		database := &db.Database{Pool: nil}
		repo := db.NewRepository(database)
		customRouter := SetupRouter(&RouterDependencies{
			Config:     customCfg,
			Database:   database,
			Repository: repo,
		})
		customServer := httptest.NewServer(customRouter)
		defer customServer.Close()

		// Test /health
		hRes, err := http.Get(customServer.URL + "/health")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		var hBody map[string]interface{}
		_ = json.NewDecoder(hRes.Body).Decode(&hBody)
		if hBody["version"] != "3.3.2-custom-override" {
			t.Errorf("expected overridden version, got %v", hBody["version"])
		}
		if hBody["verification_marker"] != "marker-override-xyz" {
			t.Errorf("expected overridden verification_marker, got %v", hBody["verification_marker"])
		}

		// Test /version.json
		vRes, err := http.Get(customServer.URL + "/version.json")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		var vBody map[string]interface{}
		_ = json.NewDecoder(vRes.Body).Decode(&vBody)
		if vBody["version"] != "3.3.2-custom-override" {
			t.Errorf("expected overridden version in /version.json, got %v", vBody["version"])
		}
		if vBody["verification_marker"] != "marker-override-xyz" {
			t.Errorf("expected overridden verification_marker in /version.json, got %v", vBody["verification_marker"])
		}

		// Test /api/v1/agent-card
		cRes, err := http.Get(customServer.URL + "/api/v1/agent-card")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		var cBody map[string]interface{}
		_ = json.NewDecoder(cRes.Body).Decode(&cBody)
		if cBody["version"] != "3.3.2-custom-override" {
			t.Errorf("expected overridden version, got %v", cBody["version"])
		}
		if cBody["verification_marker"] != "marker-override-xyz" {
			t.Errorf("expected overridden verification_marker, got %v", cBody["verification_marker"])
		}
	})
}

func TestA2UIChatEndpoints(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	t.Run("Missing message field returns HTTP 422", func(t *testing.T) {
		payload := []byte(`{"action_id": "open_intake"}`)
		res, err := http.Post(ts.URL+"/api/v1/a2ui/chat", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusUnprocessableEntity {
			t.Errorf("expected status 422, got %d", res.StatusCode)
		}
	})

	t.Run("Action open_intake returns Phase 1 surface", func(t *testing.T) {
		payload := []byte(`{"message": "open intake", "action_id": "open_intake", "context_data": {"report_name": "DevSecOps Platforms, 2026"}}`)
		res, err := http.Post(ts.URL+"/api/v1/a2ui/chat", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body A2UIChatResponse
		_ = json.NewDecoder(res.Body).Decode(&body)
		if len(body.A2UIPayloads) == 0 || !strings.Contains(body.A2UIPayloads[0], "Phase 1:") {
			t.Errorf("expected Phase 1 surface in A2UIPayloads, got: %v", body.A2UIPayloads)
		}
	})

	t.Run("Action submit_criteria_analysis returns Scorecard", func(t *testing.T) {
		payload := []byte(`{"message": "run evaluation", "action_id": "submit_criteria_analysis"}`)
		res, err := http.Post(ts.URL+"/api/v1/a2ui/chat", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body A2UIChatResponse
		_ = json.NewDecoder(res.Body).Decode(&body)
		if !strings.Contains(body.A2UIPayloads[0], "Portfolio Eligibility Scorecard") {
			t.Errorf("expected scorecard in payload, got: %v", body.A2UIPayloads)
		}
	})

	t.Run("Ad-hoc conversational question returns reasoning without onboarding form", func(t *testing.T) {
		payload := []byte(`{"message": "What is the GAAP revenue floor threshold and how do we calculate standalone CAGR?"}`)
		res, err := http.Post(ts.URL+"/api/v1/a2ui/chat", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", res.StatusCode)
		}
		var body A2UIChatResponse
		_ = json.NewDecoder(res.Body).Decode(&body)
		if len(body.A2UIPayloads) != 0 {
			t.Errorf("expected 0 A2UIPayloads for ad-hoc query, got %d", len(body.A2UIPayloads))
		}
		if !strings.Contains(body.ResponseText, "$25M") {
			t.Errorf("expected response to contain $25M, got: %s", body.ResponseText)
		}
	})
}

func TestArtifactsCRUDAndValidation(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	t.Run("Create artifact with missing fields returns 422", func(t *testing.T) {
		payload := []byte(`{"title": "Incomplete"}`)
		res, err := http.Post(ts.URL+"/api/v1/artifacts/", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusUnprocessableEntity {
			t.Errorf("expected status 422, got %d", res.StatusCode)
		}
	})

	t.Run("Create, Get, List, Delete valid artifact", func(t *testing.T) {
		createPayload := []byte(`{
			"title": "E2E Test Artifact",
			"artifact_type": "scorecard",
			"summary": "Automated verification summary",
			"content": "### Verification Content\nAll tests passed."
		}`)
		res, err := http.Post(ts.URL+"/api/v1/artifacts/", "application/json", bytes.NewBuffer(createPayload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusCreated {
			t.Fatalf("expected status 201, got %d", res.StatusCode)
		}

		var created db.SavedArtifact
		_ = json.NewDecoder(res.Body).Decode(&created)
		if created.ID == uuid.Nil {
			t.Fatalf("expected valid UUID, got nil")
		}

		// GET by UUID
		getRes, err := http.Get(ts.URL + "/api/v1/artifacts/" + created.ID.String())
		if err != nil || getRes.StatusCode != http.StatusOK {
			t.Errorf("expected GET status 200, got %d", getRes.StatusCode)
		}

		// DELETE by UUID
		req, _ := http.NewRequest(http.MethodDelete, ts.URL+"/api/v1/artifacts/"+created.ID.String(), nil)
		delRes, err := http.DefaultClient.Do(req)
		if err != nil || delRes.StatusCode != http.StatusNoContent {
			t.Errorf("expected DELETE status 204, got %d", delRes.StatusCode)
		}

		// GET after DELETE returns 404
		get404, _ := http.Get(ts.URL + "/api/v1/artifacts/" + created.ID.String())
		if get404.StatusCode != http.StatusNotFound {
			t.Errorf("expected 404 after delete, got %d", get404.StatusCode)
		}
	})

	t.Run("Non-UUID string returns 422", func(t *testing.T) {
		res, _ := http.Get(ts.URL + "/api/v1/artifacts/not-a-valid-uuid")
		if res.StatusCode != http.StatusUnprocessableEntity {
			t.Errorf("expected 422 for invalid UUID, got %d", res.StatusCode)
		}
	})

	t.Run("Non-existent UUID returns 404", func(t *testing.T) {
		fakeUUID := "00000000-0000-0000-0000-000000000000"
		res, _ := http.Get(ts.URL + "/api/v1/artifacts/" + fakeUUID)
		if res.StatusCode != http.StatusNotFound {
			t.Errorf("expected 404 for non-existent UUID, got %d", res.StatusCode)
		}
	})
}

func TestExportEndpoints(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	routes := []struct {
		Path              string
		ExpectedSubstring string
	}{
		{"/api/v1/export/deep-dive-report", "Universal Analyst Evaluation"},
		{"/api/v1/export/workback-schedule?format=md", "Workback Schedule"},
		{"/api/v1/export/workback-schedule?format=csv", "7-Phase Operational Process"},
		{"/api/v1/export/kickoff-deck", "Executive Stakeholder Kickoff"},
		{"/api/v1/export/rfi-responses?format=md", "Completed RFI Technical Responses"},
		{"/api/v1/export/rfi-responses?format=csv", "Worksheet Tab Domain"},
		{"/api/v1/export/demo-playbook?report=devsecops", "60 Minutes Overall Cap"},
		{"/api/v1/export/demo-playbook?report=cnap", "45 Minutes Overall Cap"},
		{"/api/v1/export/executive-review-memo", "APPROVED BY EXECUTIVE REVIEW PANEL"},
		{"/api/v1/export/final-publication-bundle", "Phase 7: Master Portal Publication"},
	}

	for _, r := range routes {
		t.Run("GET "+r.Path, func(t *testing.T) {
			res, err := http.Get(ts.URL + r.Path)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if res.StatusCode != http.StatusOK {
				t.Errorf("expected 200 for %s, got %d", r.Path, res.StatusCode)
			}
		})
	}

	t.Run("POST to GET export endpoint returns 405 Method Not Allowed", func(t *testing.T) {
		res, err := http.Post(ts.URL+"/api/v1/export/demo-playbook?report=cnap", "application/json", strings.NewReader("{}"))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusMethodNotAllowed {
			t.Errorf("expected 405 Method Not Allowed, got %d", res.StatusCode)
		}
	})

	t.Run("Invalid export route returns 404 Not Found", func(t *testing.T) {
		res, _ := http.Get(ts.URL + "/api/v1/export/non-existent-route")
		if res.StatusCode != http.StatusNotFound {
			t.Errorf("expected 404 Not Found, got %d", res.StatusCode)
		}
	})
}

func TestAgentEngineEndpoints(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	t.Run("POST /api/v1/agent-engine/query returns grounded synthesis", func(t *testing.T) {
		payload := []byte(`{"prompt": "Explain container vulnerability scanning and agentless workload security.", "workspace_id": "ws-cnap-001"}`)
		res, err := http.Post(ts.URL+"/api/v1/agent-engine/query", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["category"] != "CNAPP" {
			t.Errorf("expected CNAPP category, got %v", body["category"])
		}
	})

	t.Run("GET /api/v1/agent-engine/card returns metadata card", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/api/v1/agent-engine/card")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected 200, got %d", res.StatusCode)
		}
	})

	t.Run("POST /api/v1/agent-engine/evaluate scores grounded answer", func(t *testing.T) {
		payload := []byte(`{
			"question": "How do you ensure container security?",
			"generated_answer": "Google Cloud Artifact Registry provides automated vulnerability scanning and SLSA Level 3 provenance attestations with SOC2 Type II compliance."
		}`)
		res, err := http.Post(ts.URL+"/api/v1/agent-engine/evaluate", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["passed_evaluation"] != true {
			t.Errorf("expected passed_evaluation=true, got %v", body["passed_evaluation"])
		}
	})
}

func TestSPARouteFallbackAndMIMERegistration(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	t.Run("Verify MIME extension registrations", func(t *testing.T) {
		wasmType := mime.TypeByExtension(".wasm")
		if !strings.Contains(wasmType, "application/wasm") {
			t.Errorf("expected application/wasm for .wasm, got %s", wasmType)
		}
		jsType := mime.TypeByExtension(".js")
		if !strings.Contains(jsType, "application/javascript") {
			t.Errorf("expected application/javascript for .js, got %s", jsType)
		}
		jsonType := mime.TypeByExtension(".json")
		if !strings.Contains(jsonType, "application/json") {
			t.Errorf("expected application/json for .json, got %s", jsonType)
		}
	})

	t.Run("GET / serves root portal", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Errorf("expected 200, got %d", res.StatusCode)
		}
		body, _ := io.ReadAll(res.Body)
		if !strings.Contains(string(body), "Analyst Response Agent (ARA) - A2UI Executive Portal") {
			t.Errorf("expected portal title in root response, got: %s", string(body))
		}
	})

	t.Run("GET allowed SPA routes fall back to SPA index.html", func(t *testing.T) {
		spaRoutes := []string{
			"/",
			"/index.html",
			"/workspaces",
			"/workspaces/123/dashboard",
			"/workspace",
			"/workspace/rfi-analysis/deep-link",
			"/governance",
			"/review",
			"/publish",
			"/onboarding",
			"/intake",
		}
		for _, path := range spaRoutes {
			res, err := http.Get(ts.URL + path)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if res.StatusCode != http.StatusOK {
				t.Errorf("expected 200 for SPA route %s, got %d", path, res.StatusCode)
			}
			body, _ := io.ReadAll(res.Body)
			if !strings.Contains(string(body), "Analyst Response Agent (ARA) - A2UI Executive Portal") {
				t.Errorf("expected portal HTML in SPA fallback for %s, got: %s", path, string(body))
			}

			// HEAD request must also succeed with 200 and Content-Type text/html
			headReq, err := http.NewRequest(http.MethodHead, ts.URL+path, nil)
			if err != nil {
				t.Fatalf("failed to create HEAD request for %s: %v", path, err)
			}
			headRes, err := http.DefaultClient.Do(headReq)
			if err != nil {
				t.Fatalf("unexpected error on HEAD %s: %v", path, err)
			}
			if headRes.StatusCode != http.StatusOK {
				t.Errorf("expected 200 on HEAD SPA route %s, got %d", path, headRes.StatusCode)
			}
			if ct := headRes.Header.Get("Content-Type"); !strings.Contains(ct, "text/html") {
				t.Errorf("expected Content-Type text/html on HEAD %s, got %s", path, ct)
			}
		}
	})

	t.Run("GET non-existent /api/ route returns strict 404 JSON", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/api/v1/non-existent-endpoint")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusNotFound {
			t.Errorf("expected 404, got %d", res.StatusCode)
		}
		var data map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&data)
		if data["detail"] != "Not Found" {
			t.Errorf("expected detail 'Not Found', got %v", data["detail"])
		}
	})

	t.Run("POST non-existent route returns strict 404 JSON", func(t *testing.T) {
		res, err := http.Post(ts.URL+"/non-existent-endpoint", "application/json", strings.NewReader("{}"))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusNotFound {
			t.Errorf("expected 404, got %d", res.StatusCode)
		}
		var data map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&data)
		if data["detail"] != "Not Found" {
			t.Errorf("expected detail 'Not Found', got %v", data["detail"])
		}
	})

	t.Run("GET sensitive system path probes, unmapped paths, and directory traversal return strict 404 JSON", func(t *testing.T) {
		traversalAndUnmappedPaths := []string{
			"/etc/passwd",
			"/proc/cpuinfo",
			"/sys/kernel",
			"/dev/null",
			"/root/.bashrc",
			"/.env",
			"/test.php",
			"/favicon.ico",
			"/var/log",
			"/var/log/syslog",
			"/opt",
			"/tmp",
			"/bin/sh",
			"/usr/local/bin",
			"/random-unmapped-route",
			"/workspaces_invalid",
			"/api/v1/artifacts/../../../../etc/passwd",
			"/workspaces/../../etc/passwd",
		}
		for _, path := range traversalAndUnmappedPaths {
			res, err := http.Get(ts.URL + path)
			if err != nil {
				t.Fatalf("unexpected error requesting %s: %v", path, err)
			}
			if res.StatusCode != http.StatusNotFound {
				t.Errorf("expected 404 for path %s, got %d", path, res.StatusCode)
			}
			var data map[string]interface{}
			_ = json.NewDecoder(res.Body).Decode(&data)
			if data["detail"] != "Not Found" {
				t.Errorf("expected detail 'Not Found' for path %s, got %v", path, data["detail"])
			}
		}
	})

	t.Run("POST /api/v1/artifacts/restore contract parity includes message and response_text", func(t *testing.T) {
		payload := bytes.NewBufferString(`{}`)
		res, err := http.Post(ts.URL+"/api/v1/artifacts/restore", "application/json", payload)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
			t.Fatalf("failed to decode json: %v", err)
		}
		msg, hasMsg := body["message"]
		respText, hasRespText := body["response_text"]
		if !hasMsg || !hasRespText {
			t.Errorf("expected both 'message' and 'response_text' in response, got keys: %v", body)
		}
		if msg != respText {
			t.Errorf("expected 'message' (%v) to match 'response_text' (%v)", msg, respText)
		}
	})
}

func TestAgentEngineTopLevelRoutes(t *testing.T) {
	ts := setupTestRouter()
	defer ts.Close()

	t.Run("POST /query with flat payload returns HTTP 200 and grounded response", func(t *testing.T) {
		payload := []byte(`{"prompt": "Explain container vulnerability scanning and workload security.", "workspace_id": "ws-test-top"}`)
		res, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected HTTP 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
			t.Fatalf("failed to decode response: %v", err)
		}
		if body["category"] != "CNAPP" {
			t.Errorf("expected category 'CNAPP', got %v", body["category"])
		}
		if body["response"] == "" {
			t.Errorf("expected non-empty response field")
		}
	})

	t.Run("POST /query with nested Reasoning Engine envelope unmarshals correctly", func(t *testing.T) {
		payload := []byte(`{"input": {"prompt": "Describe automated CI/CD pipeline and canary deployment strategy", "workspace_id": "ws-nested"}}`)
		res, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected HTTP 200, got %d", res.StatusCode)
		}
		var body map[string]interface{}
		_ = json.NewDecoder(res.Body).Decode(&body)
		if body["category"] != "DEVSECOPS" {
			t.Errorf("expected category 'DEVSECOPS', got %v", body["category"])
		}
	})

	t.Run("POST /query with Model Armor DLP prompt redacts commercial rate and SSN", func(t *testing.T) {
		payload := []byte(`{"prompt": "Review secret partner discount: 45% and executive SSN 000-12-3456"}`)
		res, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected HTTP 200, got %d", res.StatusCode)
		}
		bodyBytes, _ := io.ReadAll(res.Body)
		bodyStr := string(bodyBytes)
		if strings.Contains(bodyStr, "45%") || strings.Contains(bodyStr, "000-12-3456") {
			t.Errorf("sensitive rate or SSN leaked in response: %s", bodyStr)
		}
	})

	t.Run("POST /query with SQL injection attempt returns HTTP 400", func(t *testing.T) {
		payload := []byte(`{"prompt": "SELECT * FROM users; DROP TABLE workspaces; --"}`)
		res, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusBadRequest {
			t.Errorf("expected HTTP 400 for SQL injection, got %d", res.StatusCode)
		}
	})

	t.Run("POST /query with empty prompt returns HTTP 422", func(t *testing.T) {
		payload := []byte(`{"prompt": "   "}`)
		res, err := http.Post(ts.URL+"/query", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusUnprocessableEntity {
			t.Errorf("expected HTTP 422 for empty prompt, got %d", res.StatusCode)
		}
	})

	t.Run("POST /streamQuery returns text/event-stream chunks", func(t *testing.T) {
		payload := []byte(`{"prompt": "Stream Cloud Security Posture Management compliance"}`)
		res, err := http.Post(ts.URL+"/streamQuery", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected HTTP 200, got %d", res.StatusCode)
		}
		contentType := res.Header.Get("Content-Type")
		if !strings.Contains(contentType, "text/event-stream") {
			t.Errorf("expected Content-Type text/event-stream, got %s", contentType)
		}
		bodyBytes, _ := io.ReadAll(res.Body)
		bodyStr := string(bodyBytes)
		if !strings.Contains(bodyStr, "data:") {
			t.Errorf("expected SSE data: markers in stream, got: %s", bodyStr)
		}
	})

	t.Run("POST /query:stream alias returns text/event-stream", func(t *testing.T) {
		payload := []byte(`{"prompt": "Evaluate stream"}`)
		res, err := http.Post(ts.URL+"/query:stream", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected HTTP 200, got %d", res.StatusCode)
		}
	})

	t.Run("GET /getAgentCard and POST /getAgentCard return agent metadata", func(t *testing.T) {
		for _, method := range []string{http.MethodGet, http.MethodPost} {
			req, _ := http.NewRequest(method, ts.URL+"/getAgentCard", nil)
			res, err := http.DefaultClient.Do(req)
			if err != nil {
				t.Fatalf("unexpected error on %s: %v", method, err)
			}
			if res.StatusCode != http.StatusOK {
				t.Errorf("expected HTTP 200 on %s /getAgentCard, got %d", method, res.StatusCode)
			}
			var card map[string]interface{}
			_ = json.NewDecoder(res.Body).Decode(&card)
			if card["name"] == "" {
				t.Errorf("expected non-empty agent name in card")
			}
		}
	})
}
