package gateway

import (
	"encoding/json"
	"net/http"
	"strings"

	"spottruth/go_backend/internal/auth"
	"spottruth/go_backend/internal/middleware"
)

func NewHandler(proxy http.Handler, maxInFlight int) http.Handler {
	return newHandler(proxy, maxInFlight, nil)
}

func NewHandlerWithAuth(proxy http.Handler, maxInFlight int, tokenManager *auth.TokenManager) http.Handler {
	return newHandler(proxy, maxInFlight, tokenManager)
}

func newHandler(proxy http.Handler, maxInFlight int, tokenManager *auth.TokenManager) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{
			"status":  "ok",
			"service": "spottruth-api-gateway",
		})
	})

	proxyWithLimit := middleware.ConcurrencyLimiter(maxInFlight, proxy)

	if tokenManager == nil {
		mux.Handle("/", proxyWithLimit)
		return middleware.RequestLogger(mux)
	}

	publicPaths := map[string]struct{}{
		"/healthz":             {},
		"/api/v1/auth/login":   {},
		"/api/v1/auth/refresh": {},
	}

	adminHandler := auth.RequireRole(auth.RoleAdmin, auth.RoleSystem)(proxyWithLimit)
	internalHandler := auth.RequireRole(auth.RoleSystem)(proxyWithLimit)
	defaultAuthed := auth.AuthMiddleware(tokenManager, proxyWithLimit)
	adminAuthed := auth.AuthMiddleware(tokenManager, adminHandler)
	internalAuthed := auth.AuthMiddleware(tokenManager, internalHandler)

	securedProxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if _, ok := publicPaths[r.URL.Path]; ok {
			proxyWithLimit.ServeHTTP(w, r)
			return
		}

		switch {
		case strings.HasPrefix(r.URL.Path, "/api/v1/admin/"):
			adminAuthed.ServeHTTP(w, r)
		case strings.HasPrefix(r.URL.Path, "/api/v1/internal/"):
			internalAuthed.ServeHTTP(w, r)
		default:
			defaultAuthed.ServeHTTP(w, r)
		}
	})

	mux.Handle("/", securedProxy)

	return middleware.RequestLogger(mux)
}
