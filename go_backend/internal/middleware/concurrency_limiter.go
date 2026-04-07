package middleware

import (
	"encoding/json"
	"net/http"
	"strconv"

	"spottruth/go_backend/internal/observability"
)

func ConcurrencyLimiter(maxInFlight int, next http.Handler) http.Handler {
	return ConcurrencyLimiterWithOptions(maxInFlight, 1, next)
}

func ConcurrencyLimiterWithOptions(maxInFlight int, retryAfterSeconds int, next http.Handler) http.Handler {
	if maxInFlight <= 0 {
		return next
	}
	if retryAfterSeconds <= 0 {
		retryAfterSeconds = 1
	}

	sem := make(chan struct{}, maxInFlight)

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case sem <- struct{}{}:
			defer func() { <-sem }()
			next.ServeHTTP(w, r)
		default:
			observability.OnLimiterRejected()
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("Retry-After", strconv.Itoa(retryAfterSeconds))
			w.WriteHeader(http.StatusServiceUnavailable)
			_ = json.NewEncoder(w).Encode(map[string]any{
				"code":    "GATEWAY_CONCURRENCY_LIMITED",
				"message": "并发请求过多，请稍后重试",
			})
		}
	})
}
