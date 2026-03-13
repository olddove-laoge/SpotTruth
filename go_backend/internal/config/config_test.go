package config

import (
	"testing"
	"time"
)

func TestLoadDefaultValues(t *testing.T) {
	t.Setenv("GATEWAY_ADDR", "")
	t.Setenv("UPSTREAM_BASE_URL", "")
	t.Setenv("READ_HEADER_TIMEOUT", "")
	t.Setenv("SHUTDOWN_TIMEOUT", "")
	t.Setenv("MAX_IN_FLIGHT", "")
	t.Setenv("MAX_IDLE_CONNS", "")
	t.Setenv("MAX_IDLE_CONNS_PER_HOST", "")
	t.Setenv("IDLE_CONN_TIMEOUT", "")
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
	if cfg.ResponseHeaderTimeout != 15*time.Second {
		t.Fatalf("ResponseHeaderTimeout 非法值应回退默认: %v", cfg.ResponseHeaderTimeout)
	}
}
