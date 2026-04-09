package observability

import (
	"strings"
	"testing"
	"time"
)

func TestPrometheusOutput(t *testing.T) {
	ResetForTest()
	OnRequestStart()
	OnRequestDone(200, 10*time.Millisecond)
	OnLimiterRejected()
	OnCircuitStateChange("open")
	OnCircuitDegraded()

	text := Prometheus()
	if !strings.Contains(text, "# HELP spottruth_requests_total") {
		t.Fatal("Prometheus 输出缺少 HELP")
	}
	if !strings.Contains(text, "spottruth_requests_total") {
		t.Fatal("Prometheus 输出缺少 requests_total")
	}
	if !strings.Contains(text, "spottruth_circuit_state_value") {
		t.Fatal("Prometheus 输出缺少 circuit_state")
	}
	if !strings.Contains(text, "spottruth_limiter_rejected_total") {
		t.Fatal("Prometheus 输出缺少 limiter_rejected_total")
	}
}
