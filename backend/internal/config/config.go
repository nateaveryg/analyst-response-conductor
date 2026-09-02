package config

import (
	"os"
	"strconv"
)

type Config struct {
	Port                   string
	DatabaseURL            string
	VertexAIProject        string
	VertexAILocation       string
	VertexAIModel          string
	SecuritySecretKey      string
	DefaultEnterpriseEmail string
	Environment            string
	PoolMaxConns           int32
	AgentRuntime           string
	AgentName              string
	AgentDisplayName       string
	AgentDescription       string
	AgentFunctionalType    string
	AgentIdentityType      string
	Version                string
	VerificationMarker     string
}

func LoadConfig() *Config {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	dbURL := os.Getenv("DATABASE_URL")
	proj := os.Getenv("VERTEX_AI_PROJECT")
	loc := os.Getenv("VERTEX_AI_LOCATION")
	if loc == "" {
		loc = "us-central1"
	}
	model := os.Getenv("VERTEX_AI_MODEL")
	if model == "" {
		model = "gemini-3.5-flash"
	}
	secKey := os.Getenv("SECURITY_SECRET_KEY")
	if secKey == "" {
		secKey = "dev-secret-key-conductor-ara-2026"
	}
	defaultEmail := os.Getenv("DEFAULT_ENTERPRISE_USER_EMAIL")
	if defaultEmail == "" {
		defaultEmail = "enterprise-analyst@google.com"
	}
	env := os.Getenv("ENVIRONMENT")
	if env == "" {
		env = "production"
	}
	maxConnsStr := os.Getenv("POOL_MAX_CONNS")
	maxConns := int32(10)
	if mc, err := strconv.Atoi(maxConnsStr); err == nil && mc > 0 {
		maxConns = int32(mc)
	}
	runtime := os.Getenv("AGENT_RUNTIME")
	if runtime == "" {
		runtime = "cloud-run"
	}
	version := os.Getenv("SERVICE_VERSION")
	if version == "" {
		version = "3.3.2"
	}
	verificationMarker := os.Getenv("VERIFICATION_MARKER")
	if verificationMarker == "" {
		verificationMarker = "v3.3.2-verified"
	}

	return &Config{
		Port:                   port,
		DatabaseURL:            dbURL,
		VertexAIProject:        proj,
		VertexAILocation:       loc,
		VertexAIModel:          model,
		SecuritySecretKey:      secKey,
		DefaultEnterpriseEmail: defaultEmail,
		Environment:            env,
		PoolMaxConns:           maxConns,
		AgentRuntime:           runtime,
		AgentName:              "analyst_response_agent",
		AgentDisplayName:       "Analyst Response Agent (ARA)",
		AgentDescription:       "Universal AI orchestration platform for industry analyst evaluations (Gartner MQ/CC, Forrester Wave, IDC MarketScape).",
		AgentFunctionalType:    "ANALYST_RELATIONS_ORCHESTRATOR",
		AgentIdentityType:      "SERVICE_AGENT",
		Version:                version,
		VerificationMarker:     verificationMarker,
	}
}
