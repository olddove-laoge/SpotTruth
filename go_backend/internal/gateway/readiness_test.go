package gateway

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestHTTPReadinessCheckerSuccess(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/healthz" {
			t.Fatalf("探测路径错误: %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer upstream.Close()

	checker := NewHTTPReadinessChecker(upstream.URL, "/healthz", 500*time.Millisecond)
	if err := checker(context.Background()); err != nil {
		t.Fatalf("ready 检查应通过: %v", err)
	}
}

func TestHTTPReadinessCheckerFailureStatus(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer upstream.Close()

	checker := NewHTTPReadinessChecker(upstream.URL, "/healthz", 500*time.Millisecond)
	if err := checker(context.Background()); err == nil {
		t.Fatal("ready 检查应失败")
	}
}
