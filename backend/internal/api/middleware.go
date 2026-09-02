package api

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/rficonductorv2/backend/internal/config"
)

const (
	CtxUserEmailKey = "user_email"
)

func AuthMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		userEmail := extractUserEmail(c.Request, cfg.DefaultEnterpriseEmail)
		c.Set(CtxUserEmailKey, userEmail)
		c.Next()
	}
}

func extractUserEmail(r *http.Request, defaultEmail string) string {
	// 1. Cloud IAP header
	if iapEmail := r.Header.Get("X-Goog-Authenticated-User-Email"); iapEmail != "" {
		cleaned := strings.TrimPrefix(iapEmail, "accounts.google.com:")
		cleaned = strings.TrimSpace(cleaned)
		if cleaned != "" {
			return cleaned
		}
	}

	// 2. IAP JWT assertion
	if jwt := r.Header.Get("x-goog-iap-jwt-assertion"); jwt != "" {
		parts := strings.Split(jwt, ".")
		if len(parts) >= 2 {
			payloadSegment := parts[1]
			if l := len(payloadSegment) % 4; l > 0 {
				payloadSegment += strings.Repeat("=", 4-l)
			}
			if decoded, err := base64.URLEncoding.DecodeString(payloadSegment); err == nil {
				var claims struct {
					Email string `json:"email"`
				}
				if err := json.Unmarshal(decoded, &claims); err == nil && claims.Email != "" {
					return strings.TrimSpace(claims.Email)
				}
			}
		}
	}

	// 3. Local test header
	if testEmail := r.Header.Get("X-User-Email"); testEmail != "" {
		return strings.TrimSpace(testEmail)
	}

	// 4. Default fallback
	if defaultEmail == "" {
		defaultEmail = "enterprise-analyst@google.com"
	}
	return defaultEmail
}

func RequireOIDCToken() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
			c.Header("WWW-Authenticate", "Bearer")
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"detail": "Missing or invalid Authorization Bearer OIDC token header",
			})
			return
		}

		token := strings.TrimSpace(strings.TrimPrefix(authHeader, "Bearer "))
		if token == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"detail": "Empty OIDC token",
			})
			return
		}

		c.Next()
	}
}

func SecurityHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("X-Content-Type-Options", "nosniff")
		c.Header("X-Frame-Options", "DENY")
		c.Header("X-XSS-Protection", "1; mode=block")
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-Email, X-Goog-Authenticated-User-Email, x-goog-iap-jwt-assertion")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
