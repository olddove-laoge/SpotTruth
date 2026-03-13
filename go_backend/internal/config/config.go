package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	GatewayAddr           string
	UpstreamBaseURL       string
	ReadHeaderTimeout     time.Duration
	ShutdownTimeout       time.Duration
	MaxInFlight           int
	MaxIdleConns          int
	MaxIdleConnsPerHost   int
	IdleConnTimeout       time.Duration
	ResponseHeaderTimeout time.Duration
}

func Load() Config {
	return Config{
		GatewayAddr:           getEnv("GATEWAY_ADDR", ":8080"),
		UpstreamBaseURL:       getEnv("UPSTREAM_BASE_URL", "http://127.0.0.1:5000"),
		ReadHeaderTimeout:     getDurationEnv("READ_HEADER_TIMEOUT", 5*time.Second),
		ShutdownTimeout:       getDurationEnv("SHUTDOWN_TIMEOUT", 10*time.Second),
		MaxInFlight:           getIntEnv("MAX_IN_FLIGHT", 2048),
		MaxIdleConns:          getIntEnv("MAX_IDLE_CONNS", 512),
		MaxIdleConnsPerHost:   getIntEnv("MAX_IDLE_CONNS_PER_HOST", 256),
		IdleConnTimeout:       getDurationEnv("IDLE_CONN_TIMEOUT", 90*time.Second),
		ResponseHeaderTimeout: getDurationEnv("RESPONSE_HEADER_TIMEOUT", 15*time.Second),
	}
}

func getEnv(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

func getIntEnv(key string, defaultVal int) int {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return defaultVal
	}
	return n
}

func getDurationEnv(key string, defaultVal time.Duration) time.Duration {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	d, err := time.ParseDuration(v)
	if err != nil || d <= 0 {
		return defaultVal
	}
	return d
}
