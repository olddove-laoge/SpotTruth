package auth

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestAuthMiddlewareMissingToken(t *testing.T) {
	tm, err := NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	h := AuthMiddleware(tm, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	w := httptest.NewRecorder()

	h.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", w.Code)
	}
}

func TestAuthMiddlewarePassAndRequireRole(t *testing.T) {
	tm, err := NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	token, err := tm.GenerateAccessToken("u1", "alice", RoleUser)
	if err != nil {
		t.Fatalf("generate token failed: %v", err)
	}

	base := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		claims, ok := ClaimsFromContext(r.Context())
		if !ok || claims.Subject != "u1" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		w.WriteHeader(http.StatusOK)
	})

	h := AuthMiddleware(tm, RequireRole(RoleUser)(base))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()

	h.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
}

func TestRequireRoleForbidden(t *testing.T) {
	tm, err := NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	token, err := tm.GenerateAccessToken("u1", "alice", RoleUser)
	if err != nil {
		t.Fatalf("generate token failed: %v", err)
	}

	h := AuthMiddleware(tm, RequireRole(RoleAdmin)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/admin/jobs/rebuild", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()

	h.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Fatalf("expected 403, got %d", w.Code)
	}
}

func TestAuthMiddlewareNilTokenManager(t *testing.T) {
	h := AuthMiddleware(nil, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/search", nil)
	w := httptest.NewRecorder()

	h.ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500, got %d", w.Code)
	}

	var body struct {
		Code  string `json:"code"`
		Error struct {
			Type string `json:"type"`
		} `json:"error"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("unmarshal body failed: %v", err)
	}
	if body.Code != "INTERNAL_ERROR" {
		t.Fatalf("unexpected code: %s", body.Code)
	}
	if body.Error.Type != "internal" {
		t.Fatalf("unexpected error type: %s", body.Error.Type)
	}
}
