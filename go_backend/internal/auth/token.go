package auth

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

var (
	ErrInvalidSigningConfig = errors.New("invalid signing config")
	ErrInvalidRole          = errors.New("invalid role")
	ErrTokenExpired         = errors.New("token expired")
	ErrTokenInvalid         = errors.New("token invalid")
)

type Role string

const (
	RoleUser   Role = "user"
	RoleAdmin  Role = "admin"
	RoleSystem Role = "system"
)

type Claims struct {
	Role     Role   `json:"role"`
	Username string `json:"username,omitempty"`
	jwt.RegisteredClaims
}

type TokenManager struct {
	signingKey []byte
	issuer     string
	accessTTL  time.Duration
	now        func() time.Time
}

func (m *TokenManager) AccessTTLSeconds() int64 {
	if m == nil {
		return 0
	}
	return int64(m.accessTTL / time.Second)
}

func NewTokenManager(signingKey, issuer string, accessTTL time.Duration) (*TokenManager, error) {
	if signingKey == "" || issuer == "" || accessTTL <= 0 {
		return nil, ErrInvalidSigningConfig
	}

	return &TokenManager{
		signingKey: []byte(signingKey),
		issuer:     issuer,
		accessTTL:  accessTTL,
		now:        time.Now,
	}, nil
}

func (m *TokenManager) GenerateAccessToken(userID, username string, role Role) (string, error) {
	if m == nil {
		return "", ErrInvalidSigningConfig
	}
	if !isValidRole(role) {
		return "", fmt.Errorf("generate token: %w", ErrInvalidRole)
	}
	if userID == "" {
		return "", errors.New("generate token: sub is empty")
	}
	tokenID, err := newTokenID()
	if err != nil {
		return "", fmt.Errorf("generate token: %w", err)
	}

	now := m.now()
	claims := Claims{
		Role:     role,
		Username: username,
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   userID,
			Issuer:    m.issuer,
			ID:        tokenID,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(m.accessTTL)),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString(m.signingKey)
	if err != nil {
		return "", fmt.Errorf("generate token: %w", err)
	}
	return signed, nil
}

func (m *TokenManager) ParseAccessToken(raw string) (*Claims, error) {
	if m == nil {
		return nil, ErrInvalidSigningConfig
	}
	if raw == "" {
		return nil, ErrTokenInvalid
	}

	parsed, err := jwt.ParseWithClaims(raw, &Claims{}, func(token *jwt.Token) (any, error) {
		method, ok := token.Method.(*jwt.SigningMethodHMAC)
		if !ok || method.Alg() != jwt.SigningMethodHS256.Alg() {
			return nil, fmt.Errorf("unexpected signing method: %s", token.Method.Alg())
		}
		return m.signingKey, nil
	}, jwt.WithIssuer(m.issuer), jwt.WithTimeFunc(m.now))
	if err != nil {
		if errors.Is(err, jwt.ErrTokenExpired) {
			return nil, ErrTokenExpired
		}
		return nil, ErrTokenInvalid
	}

	claims, ok := parsed.Claims.(*Claims)
	if !ok || !parsed.Valid {
		return nil, ErrTokenInvalid
	}
	if !isValidRole(claims.Role) || claims.Subject == "" || claims.ID == "" {
		return nil, ErrTokenInvalid
	}

	return claims, nil
}

func newTokenID() (string, error) {
	randomBytes := make([]byte, 16)
	if _, err := rand.Read(randomBytes); err != nil {
		return "", err
	}
	return hex.EncodeToString(randomBytes), nil
}

func isValidRole(role Role) bool {
	switch role {
	case RoleUser, RoleAdmin, RoleSystem:
		return true
	default:
		return false
	}
}
