package gateway

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
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

func TestNewReverseProxyTransportTimeoutOptions(t *testing.T) {
	opts := ProxyOptions{
		MaxIdleConns:          120,
		MaxIdleConnsPerHost:   60,
		IdleConnTimeout:       40 * time.Second,
		DialTimeout:           2 * time.Second,
		TLSHandshakeTimeout:   6 * time.Second,
		ExpectContinueTimeout: 1500 * time.Millisecond,
		ResponseHeaderTimeout: 3 * time.Second,
	}

	h, err := NewReverseProxy("http://127.0.0.1:5000", opts)
	if err != nil {
		t.Fatalf("创建代理失败: %v", err)
	}

	rp, ok := h.(*httputil.ReverseProxy)
	if !ok {
		t.Fatalf("返回类型错误: %T", h)
	}

	tr, ok := rp.Transport.(*http.Transport)
	if !ok {
		t.Fatalf("transport 类型错误: %T", rp.Transport)
	}

	if tr.MaxIdleConns != opts.MaxIdleConns {
		t.Fatalf("MaxIdleConns 错误: got=%d want=%d", tr.MaxIdleConns, opts.MaxIdleConns)
	}
	if tr.MaxIdleConnsPerHost != opts.MaxIdleConnsPerHost {
		t.Fatalf("MaxIdleConnsPerHost 错误: got=%d want=%d", tr.MaxIdleConnsPerHost, opts.MaxIdleConnsPerHost)
	}
	if tr.IdleConnTimeout != opts.IdleConnTimeout {
		t.Fatalf("IdleConnTimeout 错误: got=%v want=%v", tr.IdleConnTimeout, opts.IdleConnTimeout)
	}
	if tr.TLSHandshakeTimeout != opts.TLSHandshakeTimeout {
		t.Fatalf("TLSHandshakeTimeout 错误: got=%v want=%v", tr.TLSHandshakeTimeout, opts.TLSHandshakeTimeout)
	}
	if tr.ExpectContinueTimeout != opts.ExpectContinueTimeout {
		t.Fatalf("ExpectContinueTimeout 错误: got=%v want=%v", tr.ExpectContinueTimeout, opts.ExpectContinueTimeout)
	}
	if tr.ResponseHeaderTimeout != opts.ResponseHeaderTimeout {
		t.Fatalf("ResponseHeaderTimeout 错误: got=%v want=%v", tr.ResponseHeaderTimeout, opts.ResponseHeaderTimeout)
	}
	if tr.DialContext == nil {
		t.Fatal("DialContext 不应为空")
	}
}
