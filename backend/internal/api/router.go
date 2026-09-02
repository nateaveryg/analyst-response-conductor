package api

import (
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/rficonductorv2/backend/internal/agentengine"
	"github.com/google/rficonductorv2/backend/internal/config"
	"github.com/google/rficonductorv2/backend/internal/db"
	"github.com/google/rficonductorv2/backend/internal/governance"
	"github.com/google/rficonductorv2/backend/internal/observability"
	"github.com/google/rficonductorv2/backend/internal/rag"
	"github.com/google/rficonductorv2/backend/internal/services"
)

func init() {
	_ = mime.AddExtensionType(".wasm", "application/wasm")
	_ = mime.AddExtensionType(".js", "application/javascript")
	_ = mime.AddExtensionType(".mjs", "application/javascript")
	_ = mime.AddExtensionType(".json", "application/json")
	_ = mime.AddExtensionType(".css", "text/css; charset=utf-8")
	_ = mime.AddExtensionType(".html", "text/html; charset=utf-8")
	_ = mime.AddExtensionType(".png", "image/png")
	_ = mime.AddExtensionType(".svg", "image/svg+xml")
}

// Allowed SPA routes and route prefixes for the client application
var allowedSPAPrefixes = []string{
	"/workspaces",
	"/workspace",
	"/governance",
	"/review",
	"/publish",
	"/onboarding",
	"/intake",
}

// isAllowedSPARoute checks whether a request path matches an allowed client SPA route
func isAllowedSPARoute(path string) bool {
	cleanPath := filepath.Clean(path)
	if cleanPath == "/" || cleanPath == "/index.html" {
		return true
	}
	for _, prefix := range allowedSPAPrefixes {
		if cleanPath == prefix || strings.HasPrefix(cleanPath, prefix+"/") {
			return true
		}
	}
	return false
}

// resolveWebFile checks if the requested path corresponds to an existing regular file inside webDir,
// strictly enforcing directory boundary limits to prevent any path traversal.
func resolveWebFile(webDir, reqPath string) (string, bool) {
	if webDir == "" {
		return "", false
	}
	cleanRel := filepath.Clean("/" + strings.TrimPrefix(reqPath, "/"))
	cleanRel = strings.TrimPrefix(cleanRel, "/")
	if cleanRel == "" || cleanRel == "." {
		return "", false
	}
	absWebDir, err := filepath.Abs(webDir)
	if err != nil {
		return "", false
	}
	targetPath := filepath.Join(absWebDir, filepath.FromSlash(cleanRel))
	rel, relErr := filepath.Rel(absWebDir, targetPath)
	if relErr != nil || strings.HasPrefix(rel, "..") || rel == "." {
		return "", false
	}
	fi, statErr := os.Stat(targetPath)
	if statErr != nil || fi.IsDir() {
		return "", false
	}
	return targetPath, true
}

// fallbackIndexHTML provides an authentic fallback HTML shell when webDir is not present on disk
var fallbackIndexHTML = []byte(`<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>The Conductor v3 - Analyst Response Agent (ARA) - A2UI Executive Portal</title>
  <style>
    body { background-color: #0F172A; margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #94A3B8; }
    .loading-container { text-align: center; }
    .spinner { border: 3px solid rgba(138, 180, 248, 0.2); border-top: 3px solid #8AB4F8; border-radius: 50%; width: 36px; height: 36px; animation: spin 1s linear infinite; margin: 0 auto 16px auto; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    #error-boundary { display: none; width: 100%; max-width: 640px; padding: 20px; box-sizing: border-box; }
    .diagnostics-log { margin-top: 12px; display: flex; flex-direction: column; gap: 6px; }
    .diagnostics-entry { background-color: #1E293B; color: #F8FAFC; padding: 8px 12px; border-radius: 8px; font-size: 11px; border: 1px solid #334155; font-family: monospace; }
  </style>
</head>
<body>
  <div id="loading" class="loading-container">
    <div class="spinner"></div>
    <div style="font-size: 14px; font-weight: 600; color: #FFFFFF;">Initializing Conductor v3 WebAssembly Engine...</div>
    <div style="font-size: 11px; margin-top: 4px;">Loading Google Cloud Agent Architecture</div>
  </div>
  <div id="error-boundary"></div>
  <script>
    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
    function appendMessage(role, text) {
      console.log('[' + role + '] ' + text);
      const boundary = document.getElementById('error-boundary');
      if (!boundary) return;
      let logContainer = document.getElementById('diagnostics-log');
      if (!logContainer) {
        logContainer = document.createElement('div');
        logContainer.id = 'diagnostics-log';
        logContainer.className = 'diagnostics-log';
        boundary.appendChild(logContainer);
      }
      const entry = document.createElement('div');
      entry.className = 'diagnostics-entry';
      entry.textContent = '[' + role + '] ' + text;
      logContainer.appendChild(entry);
      boundary.style.display = 'block';
    }
    function renderClientError(err, contextMsg) {
      const loadingEl = document.getElementById('loading');
      if (loadingEl) loadingEl.style.display = 'none';
      const boundary = document.getElementById('error-boundary');
      if (!boundary) return;
      const header = contextMsg || 'Failed to render A2UI surface:';
      const detail = err ? (err.message || String(err)) : 'Unknown initialization failure';
      const card = document.createElement('div');
      card.className = 'bg-red-50 text-red-700 p-3 rounded-xl text-xs border border-red-200';
      card.style.cssText = 'background-color: #FEF2F2; color: #B91C1C; padding: 16px; border-radius: 12px; border: 1px solid #FECACA; font-size: 12px; line-height: 1.5; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);';
      card.innerHTML = '<div style="font-weight: 700; font-size: 13px; margin-bottom: 6px;">' + escapeHtml(header) + '</div><div style="font-family: monospace; word-break: break-word;">' + escapeHtml(detail) + '</div>';
      boundary.prepend(card);
      boundary.style.display = 'block';
    }
    function handleEngineConnectionError(err) {
      const errDetail = err && err.message ? err.message : String(err);
      const connErrMsg = '⚠️ Error connecting to Cloud Run A2UI engine: ' + errDetail;
      console.error(connErrMsg);
      appendMessage('agent', connErrMsg);
      renderClientError(err, 'Failed to render A2UI surface:');
    }
    window.addEventListener('error', function(event) {
      const target = event.target;
      if (target && (target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
        handleEngineConnectionError(new Error('Failed to load asset: ' + (target.src || target.href || 'unknown source')));
      } else if (event.message) {
        renderClientError(new Error(event.message));
      }
    }, true);
    window.addEventListener('unhandledrejection', function(event) {
      const reason = event.reason;
      handleEngineConnectionError(reason instanceof Error ? reason : new Error(String(reason)));
    });
  </script>
</body>
</html>`)

type RouterDependencies struct {
	Config     *config.Config
	Database   *db.Database
	Repository *db.Repository
}

func SetupRouter(deps *RouterDependencies) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(observability.LoggingMiddleware())
	r.Use(SecurityHeadersMiddleware())
	r.Use(AuthMiddleware(deps.Config))

	// Enable HandleMethodNotAllowed for standard HTTP 405 responses
	r.HandleMethodNotAllowed = true

	// Web root resolution for Flutter Web distribution assets
	candidateWebDirs := []string{}
	if envDir := os.Getenv("WEB_DIR"); envDir != "" {
		candidateWebDirs = append(candidateWebDirs, envDir)
	}
	candidateWebDirs = append(candidateWebDirs,
		"/app/web",
		"frontend/build/web",
		filepath.Join("..", "frontend", "build", "web"),
		filepath.Join("..", "..", "frontend", "build", "web"),
		filepath.Join("frontend", "web"),
		filepath.Join("..", "frontend", "web"),
		filepath.Join("..", "..", "frontend", "web"),
		filepath.Join("..", "app", "static"),
		filepath.Join("..", "..", "app", "static"),
		"/app/static",
		filepath.Join("app", "static"),
		"static",
	)

	var webDir string
	for _, dir := range candidateWebDirs {
		if fi, err := os.Stat(dir); err == nil && fi.IsDir() {
			webDir = dir
			break
		}
	}

	// Custom discriminating SPA fallback and 404/405 handlers matching FastAPI JSON format
	r.NoRoute(func(c *gin.Context) {
		if c.Request.Method != http.MethodGet && c.Request.Method != http.MethodHead {
			c.JSON(http.StatusNotFound, gin.H{"detail": "Not Found"})
			return
		}

		path := c.Request.URL.Path
		rawURI := c.Request.RequestURI

		// Reject directory traversal indicators immediately
		if strings.Contains(path, "..") || strings.Contains(rawURI, "..") {
			c.JSON(http.StatusNotFound, gin.H{"detail": "Not Found"})
			return
		}

		// Exclude reserved backend paths from SPA routing fallback
		if path == "/api" || strings.HasPrefix(path, "/api/") ||
			path == "/health" || strings.HasPrefix(path, "/health/") ||
			path == "/healthz" || strings.HasPrefix(path, "/healthz/") ||
			path == "/ready" || strings.HasPrefix(path, "/ready/") ||
			path == "/query" || strings.HasPrefix(path, "/query") ||
			path == "/streamQuery" || strings.HasPrefix(path, "/streamQuery") ||
			path == "/getAgentCard" || strings.HasPrefix(path, "/getAgentCard") {
			c.JSON(http.StatusNotFound, gin.H{"detail": "Not Found"})
			return
		}

		// 1. Resolve and serve physical static files located within webDir
		if targetFile, ok := resolveWebFile(webDir, path); ok {
			c.File(targetFile)
			return
		}

		// 2. Only serve SPA index.html for paths explicitly matching the client SPA route allowlist
		if isAllowedSPARoute(path) {
			if webDir != "" {
				indexPath := filepath.Join(webDir, "index.html")
				if fi, err := os.Stat(indexPath); err == nil && !fi.IsDir() {
					c.File(indexPath)
					return
				}
			}
			c.Data(http.StatusOK, "text/html; charset=utf-8", fallbackIndexHTML)
			return
		}

		// 3. Strict default: any route not in the allowlist and not matching an existing physical static file returns 404 JSON
		c.JSON(http.StatusNotFound, gin.H{"detail": "Not Found"})
	})

	r.NoMethod(func(c *gin.Context) {
		c.JSON(http.StatusMethodNotAllowed, gin.H{"detail": "Method Not Allowed"})
	})

	// Instantiate Core Services & Engine Client
	modelArmor := governance.NewModelArmorFilter()
	provenanceEng := governance.NewProvenanceEngine(deps.Config.SecuritySecretKey)
	waiverSvc := governance.NewWaiverService()
	ragSvc := rag.NewRAGService()

	agentEngineClient := agentengine.NewClient(agentengine.ClientConfig{
		ProjectID: deps.Config.VertexAIProject,
		Location:  deps.Config.VertexAILocation,
		ModelName: deps.Config.VertexAIModel,
	})

	a2uiGen := services.NewA2UIGenerator()
	inclusionSvc := services.NewInclusionAnalyzer(deps.Repository)
	timelineSvc := services.NewTimelineEngine()
	routingSvc := services.NewRoutingEngine(deps.Repository)
	rfiArchitect := services.NewRfiArchitectAgent(ragSvc, deps.Repository)
	demoAgent := services.NewDemoScriptAgent()
	execAgent := services.NewExecutiveReviewAgent()
	workspaceSvc := services.NewWorkspaceService(deps.Repository)
	artifactSvc := services.NewArtifactService(deps.Repository, a2uiGen)

	// Handlers
	a2uiHandler := NewA2UIHandler(
		a2uiGen, inclusionSvc, timelineSvc, routingSvc,
		rfiArchitect, demoAgent, execAgent, workspaceSvc,
		modelArmor, provenanceEng, waiverSvc,
	)
	workspacesHandler := NewWorkspacesHandler(workspaceSvc)
	artifactsHandler := NewArtifactsHandler(artifactSvc, workspaceSvc)
	exportHandler := NewExportHandler(rfiArchitect, demoAgent, execAgent, timelineSvc)
	inclusionHandler := NewInclusionHandler(inclusionSvc)
	streamHandler := NewStreamHandler()
	orchestrationHandler := NewOrchestrationHandler(timelineSvc, routingSvc)
	governanceHandler := NewGovernanceHandler(waiverSvc, provenanceEng, modelArmor)
	agentEngineHandler := NewAgentEngineHandler(agentEngineClient, modelArmor)

	// Static & Root Portal
	if webDir != "" {
		r.Static("/static", webDir)
		assetsDir := filepath.Join(webDir, "assets")
		if fi, err := os.Stat(assetsDir); err == nil && fi.IsDir() {
			r.Static("/assets", assetsDir)
		}
	}

	rootHandler := func(c *gin.Context) {
		if webDir != "" {
			indexPath := filepath.Join(webDir, "index.html")
			if fi, err := os.Stat(indexPath); err == nil && !fi.IsDir() {
				c.File(indexPath)
				return
			}
		}
		c.Data(http.StatusOK, "text/html; charset=utf-8", fallbackIndexHTML)
	}
	r.GET("/", rootHandler)
	r.HEAD("/", rootHandler)

	// Health & Diagnostics
	healthHandler := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":              "healthy",
			"service":             "Analyst Response Agent (ARA)",
			"environment":         deps.Config.Environment,
			"version":             deps.Config.Version,
			"verification_marker": deps.Config.VerificationMarker,
		})
	}
	r.GET("/health", healthHandler)
	r.HEAD("/health", healthHandler)
	r.GET("/healthz", healthHandler)
	r.HEAD("/healthz", healthHandler)

	readyHandler := func(c *gin.Context) {
		if err := deps.Database.Ping(c.Request.Context()); err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"status":   "unready",
				"database": err.Error(),
			})
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"status":   "ready",
			"database": "connected",
		})
	}
	r.GET("/ready", readyHandler)
	r.HEAD("/ready", readyHandler)

	// Version metadata endpoint matching frontend/build/web/version.json contract
	versionHandler := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"app_name":            "rficonductorv3_client",
			"version":             deps.Config.Version,
			"build_number":        "2",
			"package_name":        "rficonductorv3_client",
			"verification_marker": deps.Config.VerificationMarker,
		})
	}
	r.GET("/version.json", versionHandler)
	r.HEAD("/version.json", versionHandler)

	// Agent Registry Card
	agentCardHandler := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"name":                deps.Config.AgentName,
			"displayName":         deps.Config.AgentDisplayName,
			"description":         deps.Config.AgentDescription,
			"functionalType":      deps.Config.AgentFunctionalType,
			"identityType":        deps.Config.AgentIdentityType,
			"version":             deps.Config.Version,
			"verification_marker": deps.Config.VerificationMarker,
			"runtime":             deps.Config.AgentRuntime,
			"supportedProtocols": []string{
				"A2A", "REST", "A2UI", "VERTEX_REASONING_ENGINE",
			},
			"capabilities": []string{
				"criteria_parsing_and_intake",
				"scoring_matrix_gap_analysis",
				"workback_schedule_generation",
				"multi_tab_rfi_spreadsheet_ingestion",
				"pgvector_grounded_synthesis",
				"demo_script_and_storyboard_synthesis",
				"executive_governance_and_deficit_waiver",
			},
			"provider": gin.H{
				"name":    "Google Cloud",
				"project": deps.Config.VertexAIProject,
				"region":  deps.Config.VertexAILocation,
			},
		})
	}
	r.GET("/api/v1/agent-card", agentCardHandler)
	r.HEAD("/api/v1/agent-card", agentCardHandler)
	r.GET("/.well-known/agent.json", agentCardHandler)
	r.HEAD("/.well-known/agent.json", agentCardHandler)

	// Top-level Vertex AI Reasoning Engine / Agent Engine & Gateway Routes
	r.POST("/query", agentEngineHandler.Query)
	r.POST("/streamQuery", agentEngineHandler.Stream)
	r.POST("/query:stream", agentEngineHandler.Stream)
	r.GET("/getAgentCard", agentEngineHandler.GetAgentCard)
	r.HEAD("/getAgentCard", agentEngineHandler.GetAgentCard)
	r.POST("/getAgentCard", agentEngineHandler.GetAgentCard)

	// API v1 Routes
	v1 := r.Group("/api/v1")
	{
		// A2UI Chat
		v1.POST("/a2ui/chat", a2uiHandler.HandleChat)

		// Workspaces
		v1.GET("/workspaces", workspacesHandler.ListWorkspaces)
		v1.HEAD("/workspaces", workspacesHandler.ListWorkspaces)
		v1.GET("/workspaces/", workspacesHandler.ListWorkspaces)
		v1.HEAD("/workspaces/", workspacesHandler.ListWorkspaces)
		v1.POST("/workspaces", workspacesHandler.CreateWorkspace)
		v1.POST("/workspaces/", workspacesHandler.CreateWorkspace)
		v1.GET("/workspaces/:workspace_id", workspacesHandler.GetWorkspace)
		v1.HEAD("/workspaces/:workspace_id", workspacesHandler.GetWorkspace)
		v1.PUT("/workspaces/:workspace_id", workspacesHandler.UpdateWorkspace)

		// Saved Artifacts
		v1.GET("/artifacts", artifactsHandler.ListArtifacts)
		v1.HEAD("/artifacts", artifactsHandler.ListArtifacts)
		v1.GET("/artifacts/", artifactsHandler.ListArtifacts)
		v1.HEAD("/artifacts/", artifactsHandler.ListArtifacts)
		v1.POST("/artifacts", artifactsHandler.CreateArtifact)
		v1.POST("/artifacts/", artifactsHandler.CreateArtifact)
		v1.GET("/artifacts/:artifact_id", artifactsHandler.GetArtifact)
		v1.HEAD("/artifacts/:artifact_id", artifactsHandler.GetArtifact)
		v1.PUT("/artifacts/:artifact_id", artifactsHandler.UpdateArtifact)
		v1.DELETE("/artifacts/:artifact_id", artifactsHandler.DeleteArtifact)
		v1.POST("/artifacts/restore", artifactsHandler.RestoreSessionContext)

		// Export
		export := v1.Group("/export")
		{
			export.GET("/deep-dive-report", exportHandler.ExportDeepDiveReport)
			export.HEAD("/deep-dive-report", exportHandler.ExportDeepDiveReport)
			export.GET("/workback-schedule", exportHandler.ExportWorkbackSchedule)
			export.HEAD("/workback-schedule", exportHandler.ExportWorkbackSchedule)
			export.GET("/kickoff-deck", exportHandler.ExportKickoffDeck)
			export.HEAD("/kickoff-deck", exportHandler.ExportKickoffDeck)
			export.GET("/rfi-responses", exportHandler.ExportRfiResponses)
			export.HEAD("/rfi-responses", exportHandler.ExportRfiResponses)
			export.GET("/demo-playbook", exportHandler.ExportDemoPlaybook)
			export.HEAD("/demo-playbook", exportHandler.ExportDemoPlaybook)
			export.GET("/executive-review-memo", exportHandler.ExportExecutiveReviewMemo)
			export.HEAD("/executive-review-memo", exportHandler.ExportExecutiveReviewMemo)
			export.GET("/final-publication-bundle", exportHandler.ExportFinalPublicationBundle)
			export.HEAD("/final-publication-bundle", exportHandler.ExportFinalPublicationBundle)
		}

		// Inclusion
		v1.POST("/inclusion/analyze", inclusionHandler.AnalyzeInclusion)

		// Stream Telemetry
		v1.GET("/stream/telemetry", streamHandler.StreamTelemetry)
		v1.HEAD("/stream/telemetry", streamHandler.StreamTelemetry)

		// Orchestration
		v1.POST("/orchestration/timeline", orchestrationHandler.CreateWorkbackTimeline)
		v1.POST("/orchestration/route", RequireOIDCToken(), orchestrationHandler.RouteRfiQuestions)

		// Governance
		gov := v1.Group("/governance")
		{
			gov.GET("/scorecard", governanceHandler.GetScorecard)
			gov.HEAD("/scorecard", governanceHandler.GetScorecard)
			gov.GET("/waivers", governanceHandler.ListWaivers)
			gov.HEAD("/waivers", governanceHandler.ListWaivers)
			gov.POST("/waivers", governanceHandler.CreateWaiver)
			gov.POST("/waivers/:id/sign", governanceHandler.SignWaiver)
			gov.GET("/provenance/:id", governanceHandler.GetProvenance)
			gov.HEAD("/provenance/:id", governanceHandler.GetProvenance)
			gov.GET("/audit-bundle", governanceHandler.ExportAuditBundle)
			gov.HEAD("/audit-bundle", governanceHandler.ExportAuditBundle)
		}

		// Vertex AI Agent Engine
		engine := v1.Group("/agent-engine")
		{
			engine.POST("/query", agentEngineHandler.Query)
			engine.POST("/stream", agentEngineHandler.Stream)
			engine.POST("/streamQuery", agentEngineHandler.Stream)
			engine.POST("/query:stream", agentEngineHandler.Stream)
			engine.GET("/card", agentEngineHandler.GetAgentCard)
			engine.HEAD("/card", agentEngineHandler.GetAgentCard)
			engine.POST("/card", agentEngineHandler.GetAgentCard)
			engine.GET("/getAgentCard", agentEngineHandler.GetAgentCard)
			engine.HEAD("/getAgentCard", agentEngineHandler.GetAgentCard)
			engine.POST("/getAgentCard", agentEngineHandler.GetAgentCard)
			engine.POST("/evaluate", agentEngineHandler.Evaluate)
		}
	}

	return r
}
