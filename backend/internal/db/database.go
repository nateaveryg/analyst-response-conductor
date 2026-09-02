package db

import (
	"context"
	"log/slog"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	pgxvec "github.com/pgvector/pgvector-go/pgx"
)

type Database struct {
	Pool *pgxpool.Pool
}

func NewDatabase(ctx context.Context, databaseURL string, maxConns int32) (*Database, error) {
	if databaseURL == "" {
		slog.Warn("No DATABASE_URL provided, operating in in-memory repository mode")
		return &Database{Pool: nil}, nil
	}

	// Normalize Python asyncpg / psycopg URLs to standard postgres://
	cleanedURL := strings.Replace(databaseURL, "postgresql+asyncpg://", "postgres://", 1)
	cleanedURL = strings.Replace(cleanedURL, "postgresql+psycopg2://", "postgres://", 1)

	config, err := pgxpool.ParseConfig(cleanedURL)
	if err != nil {
		slog.Warn("Failed to parse DATABASE_URL, falling back to in-memory mode", "error", err)
		return &Database{Pool: nil}, nil
	}

	config.MaxConns = maxConns
	config.MaxConnLifetime = 30 * time.Minute
	config.MaxConnIdleTime = 5 * time.Minute
	config.HealthCheckPeriod = 1 * time.Minute

	config.AfterConnect = func(ctx context.Context, conn *pgx.Conn) error {
		return pgxvec.RegisterTypes(ctx, conn)
	}

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		slog.Warn("Failed to create pgxpool, falling back to in-memory mode", "error", err)
		return &Database{Pool: nil}, nil
	}

	// Ping check
	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := pool.Ping(pingCtx); err != nil {
		slog.Warn("Could not ping database on startup, continuing with pool retry", "error", err)
	} else {
		slog.Info("Successfully connected and pinged Cloud SQL PostgreSQL database")
	}

	return &Database{Pool: pool}, nil
}

func (d *Database) Close() {
	if d.Pool != nil {
		d.Pool.Close()
	}
}

func (d *Database) Ping(ctx context.Context) error {
	if d.Pool == nil {
		return nil
	}
	return d.Pool.Ping(ctx)
}
