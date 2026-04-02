package gateway

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"spottruth/go_backend/internal/auth"
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

func TestProxyRouteWithAuthMissingToken(t *testing.T) {
	tm, err := auth.NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	h := NewHandlerWithAuth(proxy, 10, tm)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("鉴权失败状态码错误: got=%d want=%d", rr.Code, http.StatusUnauthorized)
	}

	var body struct {
		Code string `json:"code"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("鉴权失败返回 JSON 非法: %v", err)
	}
	if body.Code != "AUTH_TOKEN_MISSING" {
		t.Fatalf("鉴权失败错误码错误: %s", body.Code)
	}
}

func TestProxyRouteWithAuthPass(t *testing.T) {
	tm, err := auth.NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}
	token, err := tm.GenerateAccessToken("u1", "alice", auth.RoleUser)
	if err != nil {
		t.Fatalf("generate token failed: %v", err)
	}

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/search" {
			t.Fatalf("代理路径错误: %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusCreated)
	})

	h := NewHandlerWithAuth(proxy, 10, tm)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("鉴权通过后转发失败: got=%d want=%d", rr.Code, http.StatusCreated)
	}
}

func TestProxyRouteWithAuthForbidden(t *testing.T) {
	tm, err := auth.NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}
	token, err := tm.GenerateAccessToken("u1", "alice", auth.RoleUser)
	if err != nil {
		t.Fatalf("generate token failed: %v", err)
	}

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	h := NewHandlerWithAuth(proxy, 10, tm)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/admin/jobs/rebuild", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusForbidden {
		t.Fatalf("越权访问状态码错误: got=%d want=%d", rr.Code, http.StatusForbidden)
	}

	var body struct {
		Code string `json:"code"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("越权返回 JSON 非法: %v", err)
	}
	if body.Code != "AUTH_PERMISSION_DENIED" {
		t.Fatalf("越权错误码错误: %s", body.Code)
	}
}

func TestPublicRouteBypassesAuth(t *testing.T) {
	tm, err := auth.NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/auth/login" {
			t.Fatalf("白名单路径错误: %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusAccepted)
	})

	h := NewHandlerWithAuth(proxy, 10, tm)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusAccepted {
		t.Fatalf("白名单路由应绕过鉴权: got=%d want=%d", rr.Code, http.StatusAccepted)
	}
}
