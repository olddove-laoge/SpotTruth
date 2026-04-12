package gateway

import (
	"encoding/json"
	"net/http"
	"strings"

	"spottruth/go_backend/internal/auth"
	"spottruth/go_backend/internal/middleware"
	"spottruth/go_backend/internal/observability"
)

type HandlerOptions struct {
	TokenManager            *auth.TokenManager
	LoginAuthenticator      auth.LoginAuthenticator
	ReadinessChecker        ReadinessChecker
	LimiterRetryAfterSecond int
	CircuitBreaker          middleware.CircuitBreakerOptions
	BucketLimiter           middleware.BucketLimiterOptions
}

func NewHandler(proxy http.Handler, maxInFlight int) http.Handler {
	return NewHandlerWithOptions(proxy, maxInFlight, HandlerOptions{})
}

func NewHandlerWithAuth(proxy http.Handler, maxInFlight int, tokenManager *auth.TokenManager) http.Handler {
	return NewHandlerWithOptions(proxy, maxInFlight, HandlerOptions{TokenManager: tokenManager})
}

func NewHandlerWithOptions(proxy http.Handler, maxInFlight int, opts HandlerOptions) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{
			"status":  "ok",
			"service": "spottruth-api-gateway",
		})
	})

	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		if opts.ReadinessChecker == nil {
			_ = json.NewEncoder(w).Encode(map[string]string{
				"status":  "ready",
				"service": "spottruth-api-gateway",
				"mode":    "passive",
			})
			return
		}

		if err := opts.ReadinessChecker(r.Context()); err != nil {
			w.WriteHeader(http.StatusServiceUnavailable)
			_ = json.NewEncoder(w).Encode(map[string]string{
				"status":  "not_ready",
				"service": "spottruth-api-gateway",
				"reason":  err.Error(),
			})
			return
		}

		_ = json.NewEncoder(w).Encode(map[string]string{
			"status":  "ready",
			"service": "spottruth-api-gateway",
			"mode":    "active",
		})
	})

	mux.HandleFunc("GET /metrics", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
		_, _ = w.Write([]byte(observability.Prometheus()))
	})

	mux.HandleFunc("GET /metrics/json", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		snapshot := observability.Snapshot()
		snapshot["service"] = "spottruth-api-gateway"
		_ = json.NewEncoder(w).Encode(snapshot)
	})

	proxyWithBreaker := middleware.CircuitBreaker(proxy, opts.CircuitBreaker)
	proxyWithBucket := middleware.BucketLimiter(proxyWithBreaker, opts.BucketLimiter)
	proxyWithLimit := middleware.ConcurrencyLimiterWithOptions(maxInFlight, opts.LimiterRetryAfterSecond, proxyWithBucket)

	if opts.TokenManager == nil {
		mux.Handle("/", proxyWithLimit)
		return middleware.RequestID(middleware.RequestLogger(mux))
	}

	mux.HandleFunc("POST /api/v1/auth/login", loginHandler(opts.TokenManager, opts.LoginAuthenticator))

	publicPaths := map[string]struct{}{
		"/healthz":             {},
		"/readyz":              {},
		"/metrics":             {},
		"/metrics/json":        {},
		"/api/v1/auth/login":   {},
		"/api/v1/auth/refresh": {},
	}

	adminHandler := auth.RequireRole(auth.RoleAdmin, auth.RoleSystem)(proxyWithLimit)
	internalHandler := auth.RequireRole(auth.RoleSystem)(proxyWithLimit)
	defaultAuthed := auth.AuthMiddleware(opts.TokenManager, proxyWithLimit)
	adminAuthed := auth.AuthMiddleware(opts.TokenManager, adminHandler)
	internalAuthed := auth.AuthMiddleware(opts.TokenManager, internalHandler)

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

	return middleware.CORS(middleware.RequestID(middleware.RequestLogger(mux)))
}
