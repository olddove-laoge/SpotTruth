package auth

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"
)

type contextKey string

const claimsContextKey contextKey = "auth.claims"

func AuthMiddleware(tokenManager *TokenManager, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if tokenManager == nil {
			writeAuthError(w, r, http.StatusInternalServerError, "INTERNAL_ERROR", "鉴权服务未配置")
			return
		}

		token, ok := extractBearerToken(r.Header.Get("Authorization"))
		if !ok {
			writeAuthError(w, r, http.StatusUnauthorized, "AUTH_TOKEN_MISSING", "未携带 Bearer Token")
			return
		}

		claims, err := tokenManager.ParseAccessToken(token)
		if err != nil {
			switch {
			case errors.Is(err, ErrTokenExpired):
				writeAuthError(w, r, http.StatusUnauthorized, "AUTH_TOKEN_INVALID", "token 已过期")
			default:
				writeAuthError(w, r, http.StatusUnauthorized, "AUTH_TOKEN_INVALID", "token 非法")
			}
			return
		}

		ctx := context.WithValue(r.Context(), claimsContextKey, claims)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func RequireRole(roles ...Role) func(next http.Handler) http.Handler {
	allowed := make(map[Role]struct{}, len(roles))
	for _, role := range roles {
		if isValidRole(role) {
			allowed[role] = struct{}{}
		}
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, ok := ClaimsFromContext(r.Context())
			if !ok {
				writeAuthError(w, r, http.StatusUnauthorized, "AUTH_TOKEN_INVALID", "未找到鉴权上下文")
				return
			}

			if _, ok := allowed[claims.Role]; !ok {
				writeAuthError(w, r, http.StatusForbidden, "AUTH_PERMISSION_DENIED", "角色权限不足")
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func ClaimsFromContext(ctx context.Context) (*Claims, bool) {
	claims, ok := ctx.Value(claimsContextKey).(*Claims)
	if !ok || claims == nil {
		return nil, false
	}
	return claims, true
}

func extractBearerToken(authorizationHeader string) (string, bool) {
	if authorizationHeader == "" {
		return "", false
	}

	parts := strings.SplitN(authorizationHeader, " ", 2)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") || strings.TrimSpace(parts[1]) == "" {
		return "", false
	}

	return strings.TrimSpace(parts[1]), true
}

func writeAuthError(w http.ResponseWriter, r *http.Request, status int, code, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)

	_ = json.NewEncoder(w).Encode(map[string]any{
		"code":    code,
		"message": message,
		"error": map[string]string{
			"type":    authErrorType(status),
			"details": message,
		},
		"request_id": r.Header.Get("X-Request-ID"),
		"timestamp":  time.Now().Format(time.RFC3339),
	})
}

func authErrorType(status int) string {
	switch status {
	case http.StatusUnauthorized:
		return "unauthorized"
	case http.StatusForbidden:
		return "forbidden"
	default:
		return "internal"
	}
}
