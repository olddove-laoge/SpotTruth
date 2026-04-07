package observability

import (
	"runtime"
	"sync/atomic"
	"time"
)

var (
	requestsTotal        uint64
	inFlightRequests     int64
	status2xxTotal       uint64
	status4xxTotal       uint64
	status5xxTotal       uint64
	limiterRejectedTotal uint64
	durationNanosTotal   uint64
)

func OnRequestStart() {
	atomic.AddUint64(&requestsTotal, 1)
	atomic.AddInt64(&inFlightRequests, 1)
}

func OnRequestDone(status int, duration time.Duration) {
	atomic.AddInt64(&inFlightRequests, -1)
	atomic.AddUint64(&durationNanosTotal, uint64(duration.Nanoseconds()))

	switch {
	case status >= 200 && status < 300:
		atomic.AddUint64(&status2xxTotal, 1)
	case status >= 400 && status < 500:
		atomic.AddUint64(&status4xxTotal, 1)
	case status >= 500:
		atomic.AddUint64(&status5xxTotal, 1)
	}
}

func OnLimiterRejected() {
	atomic.AddUint64(&limiterRejectedTotal, 1)
}

func Snapshot() map[string]any {
	total := atomic.LoadUint64(&requestsTotal)
	durationTotal := atomic.LoadUint64(&durationNanosTotal)
	avgMs := 0.0
	if total > 0 {
		avgMs = float64(durationTotal) / float64(total) / 1e6
	}

	return map[string]any{
		"requests_total":         total,
		"in_flight_requests":     atomic.LoadInt64(&inFlightRequests),
		"status_2xx_total":       atomic.LoadUint64(&status2xxTotal),
		"status_4xx_total":       atomic.LoadUint64(&status4xxTotal),
		"status_5xx_total":       atomic.LoadUint64(&status5xxTotal),
		"limiter_rejected_total": atomic.LoadUint64(&limiterRejectedTotal),
		"avg_duration_ms":        avgMs,
		"goroutines":             runtime.NumGoroutine(),
	}
}

func ResetForTest() {
	atomic.StoreUint64(&requestsTotal, 0)
	atomic.StoreInt64(&inFlightRequests, 0)
	atomic.StoreUint64(&status2xxTotal, 0)
	atomic.StoreUint64(&status4xxTotal, 0)
	atomic.StoreUint64(&status5xxTotal, 0)
	atomic.StoreUint64(&limiterRejectedTotal, 0)
	atomic.StoreUint64(&durationNanosTotal, 0)
}
