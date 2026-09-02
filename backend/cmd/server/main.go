package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/google/rficonductorv2/backend/internal/api"
	"github.com/google/rficonductorv2/backend/internal/config"
	"github.com/google/rficonductorv2/backend/internal/db"
	"github.com/google/rficonductorv2/backend/internal/observability"
)

// Service version and verification marker definitions
const (
	ServiceVersion     = "3.3.2"
	VerificationMarker = "v3.3.2-verified"
)

func main() {
	observability.InitLogger()
	cfg := config.LoadConfig()

	slog.Info("Starting Analyst Response Agent (ARA) Go backend",
		"environment", cfg.Environment,
		"port", cfg.Port,
		"runtime", cfg.AgentRuntime,
		"version", cfg.Version,
		"verification_marker", cfg.VerificationMarker,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	database, err := db.NewDatabase(ctx, cfg.DatabaseURL, cfg.PoolMaxConns)
	if err != nil {
		slog.Error("Database initialization error", "error", err)
	}
	defer database.Close()

	repository := db.NewRepository(database)

	router := api.SetupRouter(&api.RouterDependencies{
		Config:     cfg,
		Database:   database,
		Repository: repository,
	})

	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		slog.Info(fmt.Sprintf("Server listening on port %s", cfg.Port))
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("HTTP server failed to listen", "error", err)
			os.Exit(1)
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	slog.Info("Shutting down server gracefully...")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		slog.Error("Server forced to shutdown", "error", err)
	}
	slog.Info("Server exited cleanly")
}
