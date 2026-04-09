package config

import (
	"testing"
	"time"
)

func TestLoadDefaultValues(t *testing.T) {
	t.Setenv("GATEWAY_ADDR", "")
	t.Setenv("UPSTREAM_BASE_URL", "")
	t.Setenv("READ_HEADER_TIMEOUT", "")
	t.Setenv("READ_TIMEOUT", "")
	t.Setenv("WRITE_TIMEOUT", "")
	t.Setenv("SERVER_IDLE_TIMEOUT", "")
	t.Setenv("AUTH_ENABLED", "")
	t.Setenv("AUTH_SIGNING_KEY", "")
	t.Setenv("AUTH_ISSUER", "")
	t.Setenv("AUTH_ACCESS_TTL", "")
	t.Setenv("UPSTREAM_HEALTH_PATH", "")
	t.Setenv("READINESS_TIMEOUT", "")
	t.Setenv("LIMITER_RETRY_AFTER_SECONDS", "")
	t.Setenv("BUCKET_LIMIT_ENABLED", "")
	t.Setenv("BUCKET_LIMIT_REQUESTS", "")
	t.Setenv("BUCKET_LIMIT_WINDOW", "")
	t.Setenv("BUCKET_LIMIT_RETRY_AFTER_SECONDS", "")
	t.Setenv("BUCKET_LIMIT_PREFER_API_KEY", "")
	t.Setenv("CB_ENABLED", "")
	t.Setenv("CB_MAX_REQUESTS", "")
	t.Setenv("CB_INTERVAL", "")
	t.Setenv("CB_TIMEOUT", "")
	t.Setenv("CB_MIN_REQUESTS", "")
	t.Setenv("CB_ERROR_RATE_THRESHOLD", "")
	t.Setenv("CB_RETRY_AFTER_SECONDS", "")
	t.Setenv("SHUTDOWN_TIMEOUT", "")
	t.Setenv("MAX_IN_FLIGHT", "")
	t.Setenv("MAX_IDLE_CONNS", "")
	t.Setenv("MAX_IDLE_CONNS_PER_HOST", "")
	t.Setenv("IDLE_CONN_TIMEOUT", "")
	t.Setenv("DIAL_TIMEOUT", "")
	t.Setenv("TLS_HANDSHAKE_TIMEOUT", "")
	t.Setenv("EXPECT_CONTINUE_TIMEOUT", "")
	t.Setenv("RESPONSE_HEADER_TIMEOUT", "")

	cfg := Load()
	if cfg.GatewayAddr != ":8080" {
		t.Fatalf("GatewayAddr 默认值错误: %s", cfg.GatewayAddr)
	}
	if cfg.UpstreamBaseURL != "http://127.0.0.1:5000" {
		t.Fatalf("UpstreamBaseURL 默认值错误: %s", cfg.UpstreamBaseURL)
	}
	if cfg.ReadHeaderTimeout != 5*time.Second {
		t.Fatalf("ReadHeaderTimeout 默认值错误: %v", cfg.ReadHeaderTimeout)
	}
	if cfg.ReadTimeout != 30*time.Second {
		t.Fatalf("ReadTimeout 默认值错误: %v", cfg.ReadTimeout)
	}
	if cfg.WriteTimeout != 30*time.Second {
		t.Fatalf("WriteTimeout 默认值错误: %v", cfg.WriteTimeout)
	}
	if cfg.IdleTimeout != 60*time.Second {
		t.Fatalf("IdleTimeout 默认值错误: %v", cfg.IdleTimeout)
	}
	if cfg.DialTimeout != 3*time.Second {
		t.Fatalf("DialTimeout 默认值错误: %v", cfg.DialTimeout)
	}
	if cfg.TLSHandshakeTimeout != 5*time.Second {
		t.Fatalf("TLSHandshakeTimeout 默认值错误: %v", cfg.TLSHandshakeTimeout)
	}
	if cfg.ExpectContinueTimeout != 1*time.Second {
		t.Fatalf("ExpectContinueTimeout 默认值错误: %v", cfg.ExpectContinueTimeout)
	}
	if !cfg.AuthEnabled {
		t.Fatal("AuthEnabled 默认值错误: 应为 true")
	}
	if cfg.AuthSigningKey != "spottruth-dev-signing-key" {
		t.Fatalf("AuthSigningKey 默认值错误: %s", cfg.AuthSigningKey)
	}
	if cfg.AuthIssuer != "spottruth-api-gateway" {
		t.Fatalf("AuthIssuer 默认值错误: %s", cfg.AuthIssuer)
	}
	if cfg.AuthAccessTTL != 30*time.Minute {
		t.Fatalf("AuthAccessTTL 默认值错误: %v", cfg.AuthAccessTTL)
	}
	if cfg.UpstreamHealthPath != "/healthz" {
		t.Fatalf("UpstreamHealthPath 默认值错误: %s", cfg.UpstreamHealthPath)
	}
	if cfg.ReadinessTimeout != 2*time.Second {
		t.Fatalf("ReadinessTimeout 默认值错误: %v", cfg.ReadinessTimeout)
	}
	if cfg.LimiterRetryAfterSec != 1 {
		t.Fatalf("LimiterRetryAfterSec 默认值错误: %d", cfg.LimiterRetryAfterSec)
	}
	if !cfg.BucketEnabled {
		t.Fatal("BucketEnabled 默认值错误: 应为 true")
	}
	if cfg.BucketRequests != 120 {
		t.Fatalf("BucketRequests 默认值错误: %d", cfg.BucketRequests)
	}
	if cfg.BucketWindow != time.Minute {
		t.Fatalf("BucketWindow 默认值错误: %v", cfg.BucketWindow)
	}
	if cfg.BucketRetryAfterSec != 5 {
		t.Fatalf("BucketRetryAfterSec 默认值错误: %d", cfg.BucketRetryAfterSec)
	}
	if !cfg.BucketPreferAPIKey {
		t.Fatal("BucketPreferAPIKey 默认值错误: 应为 true")
	}
	if !cfg.CBEnabled {
		t.Fatal("CBEnabled 默认值错误: 应为 true")
	}
	if cfg.CBMaxRequests != 3 {
		t.Fatalf("CBMaxRequests 默认值错误: %d", cfg.CBMaxRequests)
	}
	if cfg.CBInterval != 10*time.Second {
		t.Fatalf("CBInterval 默认值错误: %v", cfg.CBInterval)
	}
	if cfg.CBTimeout != 15*time.Second {
		t.Fatalf("CBTimeout 默认值错误: %v", cfg.CBTimeout)
	}
	if cfg.CBMinRequests != 5 {
		t.Fatalf("CBMinRequests 默认值错误: %d", cfg.CBMinRequests)
	}
	if cfg.CBErrorRateThreshold != 50 {
		t.Fatalf("CBErrorRateThreshold 默认值错误: %d", cfg.CBErrorRateThreshold)
	}
	if cfg.CBRetryAfterSec != 3 {
		t.Fatalf("CBRetryAfterSec 默认值错误: %d", cfg.CBRetryAfterSec)
	}
	if cfg.MaxInFlight != 2048 {
		t.Fatalf("MaxInFlight 默认值错误: %d", cfg.MaxInFlight)
	}
}

func TestLoadEnvValuesAndFallback(t *testing.T) {
	t.Setenv("GATEWAY_ADDR", ":18080")
	t.Setenv("UPSTREAM_BASE_URL", "http://127.0.0.1:9000")
	t.Setenv("MAX_IN_FLIGHT", "4096")
	t.Setenv("MAX_IDLE_CONNS", "300")
	t.Setenv("READ_HEADER_TIMEOUT", "7s")
	t.Setenv("READ_TIMEOUT", "20s")
	t.Setenv("WRITE_TIMEOUT", "25s")
	t.Setenv("SERVER_IDLE_TIMEOUT", "70s")
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("AUTH_SIGNING_KEY", "my-sign-key")
	t.Setenv("AUTH_ISSUER", "spottruth-test")
	t.Setenv("AUTH_ACCESS_TTL", "45m")
	t.Setenv("UPSTREAM_HEALTH_PATH", "/actuator/health")
	t.Setenv("READINESS_TIMEOUT", "1500ms")
	t.Setenv("LIMITER_RETRY_AFTER_SECONDS", "3")
	t.Setenv("BUCKET_LIMIT_ENABLED", "false")
	t.Setenv("BUCKET_LIMIT_REQUESTS", "300")
	t.Setenv("BUCKET_LIMIT_WINDOW", "2m")
	t.Setenv("BUCKET_LIMIT_RETRY_AFTER_SECONDS", "7")
	t.Setenv("BUCKET_LIMIT_PREFER_API_KEY", "false")
	t.Setenv("CB_ENABLED", "true")
	t.Setenv("CB_MAX_REQUESTS", "8")
	t.Setenv("CB_INTERVAL", "20s")
	t.Setenv("CB_TIMEOUT", "30s")
	t.Setenv("CB_MIN_REQUESTS", "12")
	t.Setenv("CB_ERROR_RATE_THRESHOLD", "70")
	t.Setenv("CB_RETRY_AFTER_SECONDS", "9")
	t.Setenv("DIAL_TIMEOUT", "4s")
	t.Setenv("EXPECT_CONTINUE_TIMEOUT", "2s")
	t.Setenv("TLS_HANDSHAKE_TIMEOUT", "bad")
	t.Setenv("RESPONSE_HEADER_TIMEOUT", "bad")

	cfg := Load()
	if cfg.GatewayAddr != ":18080" {
		t.Fatalf("GatewayAddr 读取环境变量失败: %s", cfg.GatewayAddr)
	}
	if cfg.UpstreamBaseURL != "http://127.0.0.1:9000" {
		t.Fatalf("UpstreamBaseURL 读取环境变量失败: %s", cfg.UpstreamBaseURL)
	}
	if cfg.MaxInFlight != 4096 {
		t.Fatalf("MaxInFlight 读取环境变量失败: %d", cfg.MaxInFlight)
	}
	if cfg.MaxIdleConns != 300 {
		t.Fatalf("MaxIdleConns 读取环境变量失败: %d", cfg.MaxIdleConns)
	}
	if cfg.ReadHeaderTimeout != 7*time.Second {
		t.Fatalf("ReadHeaderTimeout 读取环境变量失败: %v", cfg.ReadHeaderTimeout)
	}
	if cfg.ReadTimeout != 20*time.Second {
		t.Fatalf("ReadTimeout 读取环境变量失败: %v", cfg.ReadTimeout)
	}
	if cfg.WriteTimeout != 25*time.Second {
		t.Fatalf("WriteTimeout 读取环境变量失败: %v", cfg.WriteTimeout)
	}
	if cfg.IdleTimeout != 70*time.Second {
		t.Fatalf("IdleTimeout 读取环境变量失败: %v", cfg.IdleTimeout)
	}
	if cfg.DialTimeout != 4*time.Second {
		t.Fatalf("DialTimeout 读取环境变量失败: %v", cfg.DialTimeout)
	}
	if cfg.ExpectContinueTimeout != 2*time.Second {
		t.Fatalf("ExpectContinueTimeout 读取环境变量失败: %v", cfg.ExpectContinueTimeout)
	}
	if cfg.AuthEnabled {
		t.Fatal("AuthEnabled 读取环境变量失败: 应为 false")
	}
	if cfg.AuthSigningKey != "my-sign-key" {
		t.Fatalf("AuthSigningKey 读取环境变量失败: %s", cfg.AuthSigningKey)
	}
	if cfg.AuthIssuer != "spottruth-test" {
		t.Fatalf("AuthIssuer 读取环境变量失败: %s", cfg.AuthIssuer)
	}
	if cfg.AuthAccessTTL != 45*time.Minute {
		t.Fatalf("AuthAccessTTL 读取环境变量失败: %v", cfg.AuthAccessTTL)
	}
	if cfg.UpstreamHealthPath != "/actuator/health" {
		t.Fatalf("UpstreamHealthPath 读取环境变量失败: %s", cfg.UpstreamHealthPath)
	}
	if cfg.ReadinessTimeout != 1500*time.Millisecond {
		t.Fatalf("ReadinessTimeout 读取环境变量失败: %v", cfg.ReadinessTimeout)
	}
	if cfg.LimiterRetryAfterSec != 3 {
		t.Fatalf("LimiterRetryAfterSec 读取环境变量失败: %d", cfg.LimiterRetryAfterSec)
	}
	if cfg.BucketEnabled {
		t.Fatal("BucketEnabled 读取环境变量失败: 应为 false")
	}
	if cfg.BucketRequests != 300 {
		t.Fatalf("BucketRequests 读取环境变量失败: %d", cfg.BucketRequests)
	}
	if cfg.BucketWindow != 2*time.Minute {
		t.Fatalf("BucketWindow 读取环境变量失败: %v", cfg.BucketWindow)
	}
	if cfg.BucketRetryAfterSec != 7 {
		t.Fatalf("BucketRetryAfterSec 读取环境变量失败: %d", cfg.BucketRetryAfterSec)
	}
	if cfg.BucketPreferAPIKey {
		t.Fatal("BucketPreferAPIKey 读取环境变量失败: 应为 false")
	}
	if !cfg.CBEnabled {
		t.Fatal("CBEnabled 读取环境变量失败: 应为 true")
	}
	if cfg.CBMaxRequests != 8 {
		t.Fatalf("CBMaxRequests 读取环境变量失败: %d", cfg.CBMaxRequests)
	}
	if cfg.CBInterval != 20*time.Second {
		t.Fatalf("CBInterval 读取环境变量失败: %v", cfg.CBInterval)
	}
	if cfg.CBTimeout != 30*time.Second {
		t.Fatalf("CBTimeout 读取环境变量失败: %v", cfg.CBTimeout)
	}
	if cfg.CBMinRequests != 12 {
		t.Fatalf("CBMinRequests 读取环境变量失败: %d", cfg.CBMinRequests)
	}
	if cfg.CBErrorRateThreshold != 70 {
		t.Fatalf("CBErrorRateThreshold 读取环境变量失败: %d", cfg.CBErrorRateThreshold)
	}
	if cfg.CBRetryAfterSec != 9 {
		t.Fatalf("CBRetryAfterSec 读取环境变量失败: %d", cfg.CBRetryAfterSec)
	}
	if cfg.TLSHandshakeTimeout != 5*time.Second {
		t.Fatalf("TLSHandshakeTimeout 非法值应回退默认: %v", cfg.TLSHandshakeTimeout)
	}
	if cfg.ResponseHeaderTimeout != 15*time.Second {
		t.Fatalf("ResponseHeaderTimeout 非法值应回退默认: %v", cfg.ResponseHeaderTimeout)
	}
}

func TestLoadBoolEnvFallback(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "not_bool")
	t.Setenv("LIMITER_RETRY_AFTER_SECONDS", "bad")
	t.Setenv("READINESS_TIMEOUT", "bad")
	t.Setenv("BUCKET_LIMIT_REQUESTS", "bad")
	t.Setenv("BUCKET_LIMIT_WINDOW", "bad")
	t.Setenv("BUCKET_LIMIT_RETRY_AFTER_SECONDS", "bad")
	t.Setenv("CB_MAX_REQUESTS", "bad")
	t.Setenv("CB_INTERVAL", "bad")
	t.Setenv("CB_TIMEOUT", "bad")
	t.Setenv("CB_MIN_REQUESTS", "bad")
	t.Setenv("CB_ERROR_RATE_THRESHOLD", "1000")
	t.Setenv("CB_RETRY_AFTER_SECONDS", "bad")

	cfg := Load()
	if !cfg.AuthEnabled {
		t.Fatal("AUTH_ENABLED 非法值应回退默认 true")
	}
	if cfg.LimiterRetryAfterSec != 1 {
		t.Fatalf("LIMITER_RETRY_AFTER_SECONDS 非法值应回退默认 1: %d", cfg.LimiterRetryAfterSec)
	}
	if cfg.ReadinessTimeout != 2*time.Second {
		t.Fatalf("READINESS_TIMEOUT 非法值应回退默认 2s: %v", cfg.ReadinessTimeout)
	}
	if cfg.BucketRequests != 120 {
		t.Fatalf("BUCKET_LIMIT_REQUESTS 非法值应回退默认 120: %d", cfg.BucketRequests)
	}
	if cfg.BucketWindow != time.Minute {
		t.Fatalf("BUCKET_LIMIT_WINDOW 非法值应回退默认 1m: %v", cfg.BucketWindow)
	}
	if cfg.BucketRetryAfterSec != 5 {
		t.Fatalf("BUCKET_LIMIT_RETRY_AFTER_SECONDS 非法值应回退默认 5: %d", cfg.BucketRetryAfterSec)
	}
	if cfg.CBMaxRequests != 3 {
		t.Fatalf("CB_MAX_REQUESTS 非法值应回退默认 3: %d", cfg.CBMaxRequests)
	}
	if cfg.CBInterval != 10*time.Second {
		t.Fatalf("CB_INTERVAL 非法值应回退默认 10s: %v", cfg.CBInterval)
	}
	if cfg.CBTimeout != 15*time.Second {
		t.Fatalf("CB_TIMEOUT 非法值应回退默认 15s: %v", cfg.CBTimeout)
	}
	if cfg.CBMinRequests != 5 {
		t.Fatalf("CB_MIN_REQUESTS 非法值应回退默认 5: %d", cfg.CBMinRequests)
	}
	if cfg.CBErrorRateThreshold != 50 {
		t.Fatalf("CB_ERROR_RATE_THRESHOLD 非法值应回退默认 50: %d", cfg.CBErrorRateThreshold)
	}
	if cfg.CBRetryAfterSec != 3 {
		t.Fatalf("CB_RETRY_AFTER_SECONDS 非法值应回退默认 3: %d", cfg.CBRetryAfterSec)
	}
}
