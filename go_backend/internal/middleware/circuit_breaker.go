package middleware

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/sony/gobreaker"

	"spottruth/go_backend/internal/observability"
)

type CircuitBreakerOptions struct {
	Enabled            bool
	Name               string
	MaxRequests        uint32
	Interval           time.Duration
	Timeout            time.Duration
	MinRequests        uint32
	ErrorRateThreshold float64
	RetryAfterSeconds  int
}

type downstreamStatusError struct {
	status int
}

func (e downstreamStatusError) Error() string {
	return "downstream status >= 500"
}

type breakerStatusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *breakerStatusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func (r *breakerStatusRecorder) Write(b []byte) (int, error) {
	if r.status == 0 {
		r.status = http.StatusOK
	}
	return r.ResponseWriter.Write(b)
}

func CircuitBreaker(next http.Handler, opts CircuitBreakerOptions) http.Handler {
	if !opts.Enabled {
		return next
	}

	if opts.Name == "" {
		opts.Name = "upstream"
	}
	if opts.MaxRequests == 0 {
		opts.MaxRequests = 3
	}
	if opts.Interval <= 0 {
		opts.Interval = 10 * time.Second
	}
	if opts.Timeout <= 0 {
		opts.Timeout = 15 * time.Second
	}
	if opts.MinRequests == 0 {
		opts.MinRequests = 5
	}
	if opts.ErrorRateThreshold <= 0 || opts.ErrorRateThreshold > 1 {
		opts.ErrorRateThreshold = 0.5
	}
	if opts.RetryAfterSeconds <= 0 {
		opts.RetryAfterSeconds = 3
	}

	breaker := gobreaker.NewCircuitBreaker(gobreaker.Settings{
		Name:        opts.Name,
		MaxRequests: opts.MaxRequests,
		Interval:    opts.Interval,
		Timeout:     opts.Timeout,
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			if counts.Requests < opts.MinRequests {
				return false
			}
			failureRate := float64(counts.TotalFailures) / float64(counts.Requests)
			return failureRate >= opts.ErrorRateThreshold
		},
		OnStateChange: func(name string, from gobreaker.State, to gobreaker.State) {
			toState := breakerStateName(to)
			observability.OnCircuitStateChange(toState)
			log.Printf("circuit_breaker name=%s from=%s to=%s", name, breakerStateName(from), toState)
		},
	})

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := EnsureRequestID(w, r)

		_, err := breaker.Execute(func() (interface{}, error) {
			rec := &breakerStatusRecorder{ResponseWriter: w, status: http.StatusOK}
			next.ServeHTTP(rec, r)
			if rec.status >= http.StatusInternalServerError {
				return nil, downstreamStatusError{status: rec.status}
			}
			return nil, nil
		})
		if err == nil {
			return
		}

		var downstreamErr downstreamStatusError
		if errors.As(err, &downstreamErr) {
			return
		}

		switch {
		case errors.Is(err, gobreaker.ErrOpenState):
			writeDegradedResponse(w, requestID, "open_circuit", opts.RetryAfterSeconds)
			observability.OnCircuitDegraded()
		case errors.Is(err, gobreaker.ErrTooManyRequests):
			writeDegradedResponse(w, requestID, "half_open_rejected", opts.RetryAfterSeconds)
			observability.OnCircuitDegraded()
		default:
			writeDegradedResponse(w, requestID, "circuit_execute_error", opts.RetryAfterSeconds)
			observability.OnCircuitDegraded()
		}
	})
}

func breakerStateName(state gobreaker.State) string {
	switch state {
	case gobreaker.StateOpen:
		return "open"
	case gobreaker.StateHalfOpen:
		return "half-open"
	default:
		return "closed"
	}
}

func writeDegradedResponse(w http.ResponseWriter, requestID, reason string, retryAfter int) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Retry-After", strconv.Itoa(retryAfter))
	w.WriteHeader(http.StatusServiceUnavailable)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"code":           "GATEWAY_DEGRADED",
		"message":        "服务繁忙，已进入降级保护，请稍后重试",
		"request_id":     requestID,
		"degrade_reason": reason,
		"retry_after":    retryAfter,
	})
}
