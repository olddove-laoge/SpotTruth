package middleware

import (
	"log"
	"net/http"
	"time"

	"spottruth/go_backend/internal/observability"
)

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func RequestLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		observability.OnRequestStart()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		next.ServeHTTP(rec, r)
		observability.OnRequestDone(rec.status, time.Since(start))
		requestID := GetRequestID(r)

		log.Printf("request_id=%s method=%s path=%s status=%d duration_ms=%d remote=%s", requestID, r.Method, r.URL.Path, rec.status, time.Since(start).Milliseconds(), r.RemoteAddr)
	})
}
