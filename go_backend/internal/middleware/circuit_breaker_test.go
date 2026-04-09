package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"spottruth/go_backend/internal/observability"
)

func TestCircuitBreakerOpensAndDegrades(t *testing.T) {
	observability.ResetForTest()

	var upstreamCalls int32
	failingUpstream := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&upstreamCalls, 1)
		w.WriteHeader(http.StatusBadGateway)
		_, _ = w.Write([]byte("bad gateway"))
	})

	h := CircuitBreaker(failingUpstream, CircuitBreakerOptions{
		Enabled:            true,
		Name:               "test",
		MaxRequests:        1,
		Interval:           time.Minute,
		Timeout:            time.Minute,
		MinRequests:        1,
		ErrorRateThreshold: 0.5,
		RetryAfterSeconds:  2,
	})

	// 第一次失败由下游返回，断路器据此进入 open。
	req1 := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	rr1 := httptest.NewRecorder()
	h.ServeHTTP(rr1, req1)
	if rr1.Code != http.StatusBadGateway {
		t.Fatalf("第一次请求应透传下游错误: got=%d want=%d", rr1.Code, http.StatusBadGateway)
	}

	// 第二次应被熔断拦截并返回降级响应。
	req2 := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	rr2 := httptest.NewRecorder()
	h.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusServiceUnavailable {
		t.Fatalf("熔断降级状态码错误: got=%d want=%d", rr2.Code, http.StatusServiceUnavailable)
	}
	if rr2.Header().Get("Retry-After") != "2" {
		t.Fatalf("Retry-After 错误: %s", rr2.Header().Get("Retry-After"))
	}

	var body map[string]any
	if err := json.Unmarshal(rr2.Body.Bytes(), &body); err != nil {
		t.Fatalf("降级返回 JSON 非法: %v", err)
	}
	if body["code"] != "GATEWAY_DEGRADED" {
		t.Fatalf("降级错误码错误: %v", body["code"])
	}
	if body["degrade_reason"] != "open_circuit" {
		t.Fatalf("降级原因错误: %v", body["degrade_reason"])
	}
	if body["request_id"] == "" {
		t.Fatal("降级返回缺少 request_id")
	}

	if atomic.LoadInt32(&upstreamCalls) != 1 {
		t.Fatalf("熔断后不应再请求上游: got=%d want=%d", upstreamCalls, 1)
	}

	snapshot := observability.Snapshot()
	if snapshot["circuit_state"] != "open" {
		t.Fatalf("熔断状态指标错误: %v", snapshot["circuit_state"])
	}
	if snapshot["circuit_degraded_total"].(uint64) < 1 {
		t.Fatalf("降级命中指标错误: %v", snapshot["circuit_degraded_total"])
	}
}

func TestCircuitBreakerDisabledPassThrough(t *testing.T) {
	upstream := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusCreated)
	})

	h := CircuitBreaker(upstream, CircuitBreakerOptions{Enabled: false})
	req := httptest.NewRequest(http.MethodGet, "/demo", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("禁用熔断时应直通: got=%d want=%d", rr.Code, http.StatusCreated)
	}
}
