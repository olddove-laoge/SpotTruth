package middleware

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"strings"
	"time"
)

type requestIDContextKey struct{}

func RequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := EnsureRequestID(w, r)
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), requestIDContextKey{}, requestID)))
	})
}

func EnsureRequestID(w http.ResponseWriter, r *http.Request) string {
	requestID := strings.TrimSpace(r.Header.Get("X-Request-ID"))
	if requestID == "" {
		requestID = strings.TrimSpace(r.Header.Get("X-Request-Id"))
	}
	if requestID == "" {
		requestID = newRequestID()
		r.Header.Set("X-Request-ID", requestID)
	}
	if w != nil {
		w.Header().Set("X-Request-ID", requestID)
	}
	return requestID
}

func GetRequestID(r *http.Request) string {
	if r == nil {
		return ""
	}
	if v := r.Context().Value(requestIDContextKey{}); v != nil {
		if s, ok := v.(string); ok && s != "" {
			return s
		}
	}
	return strings.TrimSpace(r.Header.Get("X-Request-ID"))
}

func newRequestID() string {
	b := make([]byte, 12)
	if _, err := rand.Read(b); err != nil {
		return time.Now().Format("20060102150405.000000000")
	}
	return hex.EncodeToString(b)
}
