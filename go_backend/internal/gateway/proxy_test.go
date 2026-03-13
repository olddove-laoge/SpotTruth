package gateway

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestNewReverseProxyForward(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/tasks" {
			t.Fatalf("上游收到路径错误: %s", r.URL.Path)
		}
		if r.URL.RawQuery != "q=1" {
			t.Fatalf("上游收到查询参数错误: %s", r.URL.RawQuery)
		}
		if r.Header.Get("X-Forwarded-Host") == "" {
			t.Fatal("缺少 X-Forwarded-Host")
		}
		_, _ = io.WriteString(w, "ok")
	}))
	defer upstream.Close()

	proxy, err := NewReverseProxy(upstream.URL, ProxyOptions{
		MaxIdleConns:          100,
		MaxIdleConnsPerHost:   50,
		IdleConnTimeout:       30 * time.Second,
		ResponseHeaderTimeout: 2 * time.Second,
	})
	if err != nil {
		t.Fatalf("创建代理失败: %v", err)
	}

	req := httptest.NewRequest(http.MethodGet, "/api/v1/tasks?q=1", nil)
	rr := httptest.NewRecorder()
	proxy.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("代理返回状态码错误: %d", rr.Code)
	}
	if rr.Body.String() != "ok" {
		t.Fatalf("代理返回内容错误: %s", rr.Body.String())
	}
}

func TestNewReverseProxyInvalidTarget(t *testing.T) {
	_, err := NewReverseProxy("://bad_url", ProxyOptions{})
	if err == nil {
		t.Fatal("非法 target 应返回错误")
	}
}
