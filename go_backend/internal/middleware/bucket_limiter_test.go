package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestBucketLimiterByAPIKey(t *testing.T) {
	h := BucketLimiter(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}), BucketLimiterOptions{
		Enabled:           true,
		RequestsPerWindow: 1,
		Window:            2 * time.Second,
		RetryAfterSeconds: 2,
		PreferAPIKey:      true,
	})

	req1 := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	req1.Header.Set("X-API-Key", "key-a")
	req1.RemoteAddr = "10.0.0.1:1234"
	rr1 := httptest.NewRecorder()
	h.ServeHTTP(rr1, req1)
	if rr1.Code != http.StatusOK {
		t.Fatalf("首次请求应通过: got=%d want=%d", rr1.Code, http.StatusOK)
	}

	req2 := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	req2.Header.Set("X-API-Key", "key-a")
	req2.RemoteAddr = "10.0.0.1:1234"
	rr2 := httptest.NewRecorder()
	h.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusTooManyRequests {
		t.Fatalf("同一API Key应被限流: got=%d want=%d", rr2.Code, http.StatusTooManyRequests)
	}

	var body map[string]any
	if err := json.Unmarshal(rr2.Body.Bytes(), &body); err != nil {
		t.Fatalf("限流返回JSON非法: %v", err)
	}
	if body["code"] != "GATEWAY_RATE_LIMITED" {
		t.Fatalf("错误码不正确: %v", body["code"])
	}
	if body["request_id"] == "" {
		t.Fatal("缺少 request_id")
	}
}

func TestBucketLimiterFallbackToIP(t *testing.T) {
	h := BucketLimiter(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}), BucketLimiterOptions{
		Enabled:           true,
		RequestsPerWindow: 1,
		Window:            2 * time.Second,
		RetryAfterSeconds: 2,
		PreferAPIKey:      true,
	})

	req1 := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	req1.RemoteAddr = "10.0.0.3:2233"
	rr1 := httptest.NewRecorder()
	h.ServeHTTP(rr1, req1)
	if rr1.Code != http.StatusOK {
		t.Fatalf("首次请求应通过: got=%d want=%d", rr1.Code, http.StatusOK)
	}

	req2 := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	req2.RemoteAddr = "10.0.0.3:2233"
	rr2 := httptest.NewRecorder()
	h.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusTooManyRequests {
		t.Fatalf("同一IP应被限流: got=%d want=%d", rr2.Code, http.StatusTooManyRequests)
	}
}
