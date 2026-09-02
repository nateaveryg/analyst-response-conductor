package observability

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

var Logger *slog.Logger

func InitLogger() {
	opts := &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}
	handler := slog.NewJSONHandler(os.Stdout, opts)
	Logger = slog.New(handler)
	slog.SetDefault(Logger)
}

func getLogger() *slog.Logger {
	if Logger != nil {
		return Logger
	}
	return slog.Default()
}

func ExtractTraceID(r *http.Request) string {
	traceHeader := r.Header.Get("X-Cloud-Trace-Context")
	if traceHeader == "" {
		return ""
	}
	parts := strings.Split(traceHeader, "/")
	if len(parts) > 0 {
		return parts[0]
	}
	return ""
}

func LoggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		traceID := ExtractTraceID(c.Request)

		c.Next()

		duration := time.Since(start)
		status := c.Writer.Status()

		attrs := []slog.Attr{
			slog.String("method", c.Request.Method),
			slog.String("path", c.Request.URL.Path),
			slog.Int("status", status),
			slog.Duration("latency", duration),
			slog.String("client_ip", c.ClientIP()),
		}
		if traceID != "" {
			attrs = append(attrs, slog.String("logging.googleapis.com/trace", traceID))
		}

		l := getLogger()
		if status >= 500 {
			l.LogAttrs(context.Background(), slog.LevelError, "HTTP request failed", attrs...)
		} else if status >= 400 {
			l.LogAttrs(context.Background(), slog.LevelWarn, "HTTP client warning", attrs...)
		} else {
			l.LogAttrs(context.Background(), slog.LevelInfo, "HTTP request completed", attrs...)
		}
	}
}
