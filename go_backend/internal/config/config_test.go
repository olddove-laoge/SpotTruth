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
	if cfg.TLSHandshakeTimeout != 5*time.Second {
		t.Fatalf("TLSHandshakeTimeout 非法值应回退默认: %v", cfg.TLSHandshakeTimeout)
	}
	if cfg.ResponseHeaderTimeout != 15*time.Second {
		t.Fatalf("ResponseHeaderTimeout 非法值应回退默认: %v", cfg.ResponseHeaderTimeout)
	}
}
