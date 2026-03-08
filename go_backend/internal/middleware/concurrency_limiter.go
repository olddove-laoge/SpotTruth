package middleware

import "net/http"

func ConcurrencyLimiter(maxInFlight int, next http.Handler) http.Handler {
	if maxInFlight <= 0 {
		return next
	}

	sem := make(chan struct{}, maxInFlight)

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case sem <- struct{}{}:
			defer func() { <-sem }()
			next.ServeHTTP(w, r)
		default:
			http.Error(w, "service busy", http.StatusServiceUnavailable)
		}
	})
}
