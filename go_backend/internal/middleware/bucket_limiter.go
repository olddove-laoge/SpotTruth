package middleware

import (
	"encoding/json"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"spottruth/go_backend/internal/observability"
)

type BucketLimiterOptions struct {
	Enabled           bool
	RequestsPerWindow int
	Window            time.Duration
	RetryAfterSeconds int
	PreferAPIKey      bool
}

type bucketCounter struct {
	count   int
	resetAt time.Time
}

func BucketLimiter(next http.Handler, opts BucketLimiterOptions) http.Handler {
	if !opts.Enabled {
		return next
	}
	if opts.RequestsPerWindow <= 0 {
		opts.RequestsPerWindow = 60
	}
	if opts.Window <= 0 {
		opts.Window = time.Minute
	}
	if opts.RetryAfterSeconds <= 0 {
		opts.RetryAfterSeconds = int(opts.Window.Seconds())
		if opts.RetryAfterSeconds <= 0 {
			opts.RetryAfterSeconds = 60
		}
	}

	var (
		mu      sync.Mutex
		buckets = map[string]bucketCounter{}
	)

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := EnsureRequestID(w, r)
		key := bucketKey(r, opts.PreferAPIKey)
		now := time.Now()

		mu.Lock()
		entry := buckets[key]
		if entry.resetAt.IsZero() || now.After(entry.resetAt) {
			entry = bucketCounter{count: 0, resetAt: now.Add(opts.Window)}
		}

		if entry.count >= opts.RequestsPerWindow {
			retryAfter := int(time.Until(entry.resetAt).Seconds())
			if retryAfter <= 0 {
				retryAfter = opts.RetryAfterSeconds
			}
			mu.Unlock()

			observability.OnLimiterRejected()
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("Retry-After", strconv.Itoa(retryAfter))
			w.WriteHeader(http.StatusTooManyRequests)
			_ = json.NewEncoder(w).Encode(map[string]any{
				"code":         "GATEWAY_RATE_LIMITED",
				"message":      "请求频率过高，请稍后重试",
				"request_id":   requestID,
				"bucket_key":   key,
				"retry_after":  retryAfter,
				"limit_window": opts.Window.String(),
			})
			return
		}

		entry.count++
		buckets[key] = entry
		mu.Unlock()

		next.ServeHTTP(w, r)
	})
}

func bucketKey(r *http.Request, preferAPIKey bool) string {
	if preferAPIKey {
		if apiKey := strings.TrimSpace(r.Header.Get("X-API-Key")); apiKey != "" {
			return "api_key:" + apiKey
		}
	}

	if xff := strings.TrimSpace(r.Header.Get("X-Forwarded-For")); xff != "" {
		parts := strings.Split(xff, ",")
		if len(parts) > 0 {
			ip := strings.TrimSpace(parts[0])
			if ip != "" {
				return "ip:" + ip
			}
		}
	}

	host, _, err := net.SplitHostPort(strings.TrimSpace(r.RemoteAddr))
	if err == nil && host != "" {
		return "ip:" + host
	}
	if strings.TrimSpace(r.RemoteAddr) != "" {
		return "ip:" + strings.TrimSpace(r.RemoteAddr)
	}
	return "ip:unknown"
}
