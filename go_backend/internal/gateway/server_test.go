package gateway

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"spottruth/go_backend/internal/auth"
	"spottruth/go_backend/internal/observability"
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
	loginAuthenticator := auth.NewStaticLoginAuthenticator([]auth.StaticCredential{
		{
			Account:  "spottruth_user",
			Password: "spottruth_user_123",
			UserID:   "u-1",
			Username: "spottruth_user",
			Role:     auth.RoleUser,
		},
	})

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatalf("登录接口不应透传到上游: %s", r.URL.Path)
	})

	h := NewHandlerWithOptions(proxy, 10, HandlerOptions{
		TokenManager:       tm,
		LoginAuthenticator: loginAuthenticator,
	})
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", strings.NewReader(`{"account":"spottruth_user","password":"spottruth_user_123","login_type":"password"}`))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("登录签发状态码错误: got=%d want=%d", rr.Code, http.StatusOK)
	}

	var body struct {
		Code string `json:"code"`
		Data struct {
			AccessToken string `json:"access_token"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("登录返回 JSON 非法: %v", err)
	}
	if body.Code != "OK" {
		t.Fatalf("登录返回码错误: %s", body.Code)
	}
	if body.Data.AccessToken == "" {
		t.Fatal("登录返回 access_token 为空")
	}
}

func TestLoginTokenCanAccessProtectedRoute(t *testing.T) {
	tm, err := auth.NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}
	loginAuthenticator := auth.NewStaticLoginAuthenticator([]auth.StaticCredential{
		{
			Account:  "spottruth_user",
			Password: "spottruth_user_123",
			UserID:   "u-1",
			Username: "spottruth_user",
			Role:     auth.RoleUser,
		},
	})

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/search" {
			t.Fatalf("代理路径错误: %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusCreated)
	})

	h := NewHandlerWithOptions(proxy, 10, HandlerOptions{
		TokenManager:       tm,
		LoginAuthenticator: loginAuthenticator,
	})

	loginReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", strings.NewReader(`{"account":"spottruth_user","password":"spottruth_user_123"}`))
	loginReq.Header.Set("Content-Type", "application/json")
	loginResp := httptest.NewRecorder()
	h.ServeHTTP(loginResp, loginReq)
	if loginResp.Code != http.StatusOK {
		t.Fatalf("登录请求失败: %d", loginResp.Code)
	}

	var loginBody struct {
		Data struct {
			AccessToken string `json:"access_token"`
		} `json:"data"`
	}
	if err := json.Unmarshal(loginResp.Body.Bytes(), &loginBody); err != nil {
		t.Fatalf("登录返回 JSON 非法: %v", err)
	}
	if loginBody.Data.AccessToken == "" {
		t.Fatal("登录返回 token 为空")
	}

	protectedReq := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	protectedReq.Header.Set("Authorization", "Bearer "+loginBody.Data.AccessToken)
	protectedResp := httptest.NewRecorder()
	h.ServeHTTP(protectedResp, protectedReq)

	if protectedResp.Code != http.StatusCreated {
		t.Fatalf("登录 token 访问受保护接口失败: got=%d want=%d", protectedResp.Code, http.StatusCreated)
	}
}

func TestLoginInvalidCredentialReturnsUnauthorized(t *testing.T) {
	tm, err := auth.NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}
	loginAuthenticator := auth.NewStaticLoginAuthenticator([]auth.StaticCredential{
		{
			Account:  "spottruth_user",
			Password: "spottruth_user_123",
			UserID:   "u-1",
			Username: "spottruth_user",
			Role:     auth.RoleUser,
		},
	})

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatalf("登录失败不应透传到上游: %s", r.URL.Path)
	})

	h := NewHandlerWithOptions(proxy, 10, HandlerOptions{
		TokenManager:       tm,
		LoginAuthenticator: loginAuthenticator,
	})

	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", strings.NewReader(`{"account":"spottruth_user","password":"wrong"}`))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("登录失败状态码错误: got=%d want=%d", rr.Code, http.StatusUnauthorized)
	}
	var body struct {
		Code string `json:"code"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("登录失败返回 JSON 非法: %v", err)
	}
	if body.Code != "AUTH_LOGIN_FAILED" {
		t.Fatalf("登录失败错误码错误: %s", body.Code)
	}
}

func TestReadyzActiveSuccess(t *testing.T) {
	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	h := NewHandlerWithOptions(proxy, 10, HandlerOptions{
		ReadinessChecker: func(ctx context.Context) error { return nil },
	})

	req := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("readyz 成功状态码错误: got=%d want=%d", rr.Code, http.StatusOK)
	}
}

func TestReadyzActiveFailure(t *testing.T) {
	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	h := NewHandlerWithOptions(proxy, 10, HandlerOptions{
		ReadinessChecker: func(ctx context.Context) error { return context.DeadlineExceeded },
	})

	req := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusServiceUnavailable {
		t.Fatalf("readyz 失败状态码错误: got=%d want=%d", rr.Code, http.StatusServiceUnavailable)
	}
}

func TestMetricsEndpoint(t *testing.T) {
	observability.ResetForTest()

	proxy := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	h := NewHandler(proxy, 10)

	req1 := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rr1 := httptest.NewRecorder()
	h.ServeHTTP(rr1, req1)

	req2 := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	rr2 := httptest.NewRecorder()
	h.ServeHTTP(rr2, req2)

	if rr2.Code != http.StatusOK {
		t.Fatalf("metrics 状态码错误: got=%d want=%d", rr2.Code, http.StatusOK)
	}
	if !strings.Contains(rr2.Body.String(), "spottruth_requests_total") {
		t.Fatal("metrics Prometheus 输出缺少 spottruth_requests_total")
	}

	req3 := httptest.NewRequest(http.MethodGet, "/metrics/json", nil)
	rr3 := httptest.NewRecorder()
	h.ServeHTTP(rr3, req3)

	if rr3.Code != http.StatusOK {
		t.Fatalf("metrics/json 状态码错误: got=%d want=%d", rr3.Code, http.StatusOK)
	}

	var body map[string]any
	if err := json.Unmarshal(rr3.Body.Bytes(), &body); err != nil {
		t.Fatalf("metrics/json 返回 JSON 非法: %v", err)
	}

	if _, ok := body["requests_total"]; !ok {
		t.Fatal("metrics 缺少 requests_total")
	}
	if _, ok := body["in_flight_requests"]; !ok {
		t.Fatal("metrics 缺少 in_flight_requests")
	}
	if _, ok := body["limiter_rejected_total"]; !ok {
		t.Fatal("metrics 缺少 limiter_rejected_total")
	}
	if _, ok := body["circuit_state"]; !ok {
		t.Fatal("metrics 缺少 circuit_state")
	}
	if _, ok := body["circuit_degraded_total"]; !ok {
		t.Fatal("metrics 缺少 circuit_degraded_total")
	}
}
