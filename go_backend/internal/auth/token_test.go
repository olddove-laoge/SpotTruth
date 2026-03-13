package auth

import (
	"errors"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func TestTokenManagerGenerateAndParse(t *testing.T) {
	tm, err := NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	token, err := tm.GenerateAccessToken("u1", "alice", RoleUser)
	if err != nil {
		t.Fatalf("generate token failed: %v", err)
	}

	claims, err := tm.ParseAccessToken(token)
	if err != nil {
		t.Fatalf("parse token failed: %v", err)
	}

	if claims.Subject != "u1" {
		t.Fatalf("unexpected subject: %s", claims.Subject)
	}
	if claims.Username != "alice" {
		t.Fatalf("unexpected username: %s", claims.Username)
	}
	if claims.Role != RoleUser {
		t.Fatalf("unexpected role: %s", claims.Role)
	}
	if claims.ID == "" {
		t.Fatal("expected jti to be set")
	}
}

func TestTokenManagerParseExpiredToken(t *testing.T) {
	tm, err := NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	tm.now = func() time.Time {
		return time.Unix(1000, 0)
	}
	token, err := tm.GenerateAccessToken("u1", "alice", RoleUser)
	if err != nil {
		t.Fatalf("generate token failed: %v", err)
	}

	tm.now = func() time.Time {
		return time.Unix(1000, 0).Add(2 * time.Hour)
	}

	_, err = tm.ParseAccessToken(token)
	if !errors.Is(err, ErrTokenExpired) {
		t.Fatalf("expected ErrTokenExpired, got: %v", err)
	}
}

func TestTokenManagerGenerateInvalidRole(t *testing.T) {
	tm, err := NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	_, err = tm.GenerateAccessToken("u1", "alice", Role("guest"))
	if !errors.Is(err, ErrInvalidRole) {
		t.Fatalf("expected ErrInvalidRole, got: %v", err)
	}
}

func TestTokenManagerParseRejectsMissingJTI(t *testing.T) {
	tm, err := NewTokenManager("test-signing-key", "spottruth-gateway", 30*time.Minute)
	if err != nil {
		t.Fatalf("new token manager failed: %v", err)
	}

	now := time.Now()
	claims := Claims{
		Role:     RoleUser,
		Username: "alice",
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   "u1",
			Issuer:    "spottruth-gateway",
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(30 * time.Minute)),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	raw, err := token.SignedString([]byte("test-signing-key"))
	if err != nil {
		t.Fatalf("sign token failed: %v", err)
	}

	_, err = tm.ParseAccessToken(raw)
	if !errors.Is(err, ErrTokenInvalid) {
		t.Fatalf("expected ErrTokenInvalid, got: %v", err)
	}
}
