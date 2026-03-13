package gateway

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthz(t *testing.T) {
	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatalf("healthz 不应走代理")
	})

	h := NewHandler(proxy, 10)
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("healthz 状态码错误: %d", rr.Code)
	}

	var body map[string]string
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("healthz 返回 JSON 非法: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("healthz 返回内容错误: %v", body)
	}
}

func TestProxyRoute(t *testing.T) {
	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/demo" {
			t.Fatalf("代理路径错误: %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusCreated)
	})

	h := NewHandler(proxy, 10)
	req := httptest.NewRequest(http.MethodGet, "/demo", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("代理路由未转发: %d", rr.Code)
	}
}
