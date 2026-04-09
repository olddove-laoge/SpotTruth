package observability

import (
	"fmt"
	"runtime"
	"strings"
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
	circuitOpenTotal     uint64
	circuitHalfOpenTotal uint64
	circuitClosedTotal   uint64
	circuitDegradedTotal uint64
	circuitState         int64
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

func OnCircuitStateChange(state string) {
	switch state {
	case "open":
		atomic.StoreInt64(&circuitState, 2)
		atomic.AddUint64(&circuitOpenTotal, 1)
	case "half-open":
		atomic.StoreInt64(&circuitState, 1)
		atomic.AddUint64(&circuitHalfOpenTotal, 1)
	case "closed":
		atomic.StoreInt64(&circuitState, 0)
		atomic.AddUint64(&circuitClosedTotal, 1)
	}
}

func OnCircuitDegraded() {
	atomic.AddUint64(&circuitDegradedTotal, 1)
}

func circuitStateName(v int64) string {
	switch v {
	case 2:
		return "open"
	case 1:
		return "half-open"
	default:
		return "closed"
	}
}

func Snapshot() map[string]any {
	total := atomic.LoadUint64(&requestsTotal)
	durationTotal := atomic.LoadUint64(&durationNanosTotal)
	avgMs := 0.0
	if total > 0 {
		avgMs = float64(durationTotal) / float64(total) / 1e6
	}

	return map[string]any{
		"requests_total":          total,
		"in_flight_requests":      atomic.LoadInt64(&inFlightRequests),
		"status_2xx_total":        atomic.LoadUint64(&status2xxTotal),
		"status_4xx_total":        atomic.LoadUint64(&status4xxTotal),
		"status_5xx_total":        atomic.LoadUint64(&status5xxTotal),
		"limiter_rejected_total":  atomic.LoadUint64(&limiterRejectedTotal),
		"circuit_state":           circuitStateName(atomic.LoadInt64(&circuitState)),
		"circuit_open_total":      atomic.LoadUint64(&circuitOpenTotal),
		"circuit_half_open_total": atomic.LoadUint64(&circuitHalfOpenTotal),
		"circuit_closed_total":    atomic.LoadUint64(&circuitClosedTotal),
		"circuit_degraded_total":  atomic.LoadUint64(&circuitDegradedTotal),
		"avg_duration_ms":         avgMs,
		"goroutines":              runtime.NumGoroutine(),
	}
}

func Prometheus() string {
	snapshot := Snapshot()
	b := &strings.Builder{}

	b.WriteString("# HELP spottruth_requests_total Total requests seen by gateway\n")
	b.WriteString("# TYPE spottruth_requests_total counter\n")
	fmt.Fprintf(b, "spottruth_requests_total %d\n", snapshot["requests_total"])

	b.WriteString("# HELP spottruth_in_flight_requests Number of in-flight requests\n")
	b.WriteString("# TYPE spottruth_in_flight_requests gauge\n")
	fmt.Fprintf(b, "spottruth_in_flight_requests %d\n", snapshot["in_flight_requests"])

	b.WriteString("# HELP spottruth_http_status_total Count of responses by status class\n")
	b.WriteString("# TYPE spottruth_http_status_total counter\n")
	fmt.Fprintf(b, "spottruth_http_status_total{code_class=\"2xx\"} %d\n", snapshot["status_2xx_total"])
	fmt.Fprintf(b, "spottruth_http_status_total{code_class=\"4xx\"} %d\n", snapshot["status_4xx_total"])
	fmt.Fprintf(b, "spottruth_http_status_total{code_class=\"5xx\"} %d\n", snapshot["status_5xx_total"])

	b.WriteString("# HELP spottruth_limiter_rejected_total Rejected requests by limiter\n")
	b.WriteString("# TYPE spottruth_limiter_rejected_total counter\n")
	fmt.Fprintf(b, "spottruth_limiter_rejected_total %d\n", snapshot["limiter_rejected_total"])

	b.WriteString("# HELP spottruth_circuit_open_total Circuit open transitions\n")
	b.WriteString("# TYPE spottruth_circuit_open_total counter\n")
	fmt.Fprintf(b, "spottruth_circuit_open_total %d\n", snapshot["circuit_open_total"])

	b.WriteString("# HELP spottruth_circuit_half_open_total Circuit half-open transitions\n")
	b.WriteString("# TYPE spottruth_circuit_half_open_total counter\n")
	fmt.Fprintf(b, "spottruth_circuit_half_open_total %d\n", snapshot["circuit_half_open_total"])

	b.WriteString("# HELP spottruth_circuit_closed_total Circuit closed transitions\n")
	b.WriteString("# TYPE spottruth_circuit_closed_total counter\n")
	fmt.Fprintf(b, "spottruth_circuit_closed_total %d\n", snapshot["circuit_closed_total"])

	b.WriteString("# HELP spottruth_circuit_degraded_total Circuit degraded responses\n")
	b.WriteString("# TYPE spottruth_circuit_degraded_total counter\n")
	fmt.Fprintf(b, "spottruth_circuit_degraded_total %d\n", snapshot["circuit_degraded_total"])

	b.WriteString("# HELP spottruth_circuit_state_value Circuit state as numeric gauge (closed=0, half-open=1, open=2)\n")
	b.WriteString("# TYPE spottruth_circuit_state_value gauge\n")
	fmt.Fprintf(b, "spottruth_circuit_state_value %.0f\n", circuitStateValue(snapshot["circuit_state"].(string)))

	b.WriteString("# HELP spottruth_request_duration_avg_ms Average request duration in ms\n")
	b.WriteString("# TYPE spottruth_request_duration_avg_ms gauge\n")
	fmt.Fprintf(b, "spottruth_request_duration_avg_ms %.6f\n", snapshot["avg_duration_ms"])

	b.WriteString("# HELP spottruth_goroutines Number of goroutines\n")
	b.WriteString("# TYPE spottruth_goroutines gauge\n")
	fmt.Fprintf(b, "spottruth_goroutines %d\n", snapshot["goroutines"])

	return b.String()
}

func circuitStateValue(state string) float64 {
	switch state {
	case "open":
		return 2
	case "half-open":
		return 1
	default:
		return 0
	}
}

func ResetForTest() {
	atomic.StoreUint64(&requestsTotal, 0)
	atomic.StoreInt64(&inFlightRequests, 0)
	atomic.StoreUint64(&status2xxTotal, 0)
	atomic.StoreUint64(&status4xxTotal, 0)
	atomic.StoreUint64(&status5xxTotal, 0)
	atomic.StoreUint64(&limiterRejectedTotal, 0)
	atomic.StoreUint64(&circuitOpenTotal, 0)
	atomic.StoreUint64(&circuitHalfOpenTotal, 0)
	atomic.StoreUint64(&circuitClosedTotal, 0)
	atomic.StoreUint64(&circuitDegradedTotal, 0)
	atomic.StoreInt64(&circuitState, 0)
	atomic.StoreUint64(&durationNanosTotal, 0)
}
