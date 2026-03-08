package gateway

import (
	"encoding/json"
	"net/http"

	"spottruth/go_backend/internal/middleware"
)

func NewHandler(proxy http.Handler, maxInFlight int) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{
			"status":  "ok",
			"service": "spottruth-api-gateway",
		})
	})

	proxyWithLimit := middleware.ConcurrencyLimiter(maxInFlight, proxy)
	mux.Handle("/", proxyWithLimit)

	return middleware.RequestLogger(mux)
}
