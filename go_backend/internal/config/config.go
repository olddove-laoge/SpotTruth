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
	ReadTimeout           time.Duration
	WriteTimeout          time.Duration
	IdleTimeout           time.Duration
	AuthEnabled           bool
	AuthSigningKey        string
	AuthIssuer            string
	AuthAccessTTL         time.Duration
	UpstreamHealthPath    string
	ReadinessTimeout      time.Duration
	LimiterRetryAfterSec  int
	BucketEnabled         bool
	BucketRequests        int
	BucketWindow          time.Duration
	BucketRetryAfterSec   int
	BucketPreferAPIKey    bool
	CBEnabled             bool
	CBMaxRequests         int
	CBInterval            time.Duration
	CBTimeout             time.Duration
	CBMinRequests         int
	CBErrorRateThreshold  int
	CBRetryAfterSec       int
	ShutdownTimeout       time.Duration
	MaxInFlight           int
	MaxIdleConns          int
	MaxIdleConnsPerHost   int
	IdleConnTimeout       time.Duration
	DialTimeout           time.Duration
	TLSHandshakeTimeout   time.Duration
	ExpectContinueTimeout time.Duration
	ResponseHeaderTimeout time.Duration
}

func Load() Config {
	return Config{
		GatewayAddr:           getEnv("GATEWAY_ADDR", ":8080"),
		UpstreamBaseURL:       getEnv("UPSTREAM_BASE_URL", "http://127.0.0.1:5000"),
		ReadHeaderTimeout:     getDurationEnv("READ_HEADER_TIMEOUT", 5*time.Second),
		ReadTimeout:           getDurationEnv("READ_TIMEOUT", 30*time.Second),
		WriteTimeout:          getDurationEnv("WRITE_TIMEOUT", 30*time.Second),
		IdleTimeout:           getDurationEnv("SERVER_IDLE_TIMEOUT", 60*time.Second),
		AuthEnabled:           getBoolEnv("AUTH_ENABLED", true),
		AuthSigningKey:        getEnv("AUTH_SIGNING_KEY", "spottruth-dev-signing-key"),
		AuthIssuer:            getEnv("AUTH_ISSUER", "spottruth-api-gateway"),
		AuthAccessTTL:         getDurationEnv("AUTH_ACCESS_TTL", 30*time.Minute),
		UpstreamHealthPath:    getEnv("UPSTREAM_HEALTH_PATH", "/healthz"),
		ReadinessTimeout:      getDurationEnv("READINESS_TIMEOUT", 2*time.Second),
		LimiterRetryAfterSec:  getIntEnv("LIMITER_RETRY_AFTER_SECONDS", 1),
		BucketEnabled:         getBoolEnv("BUCKET_LIMIT_ENABLED", true),
		BucketRequests:        getIntEnv("BUCKET_LIMIT_REQUESTS", 120),
		BucketWindow:          getDurationEnv("BUCKET_LIMIT_WINDOW", time.Minute),
		BucketRetryAfterSec:   getIntEnv("BUCKET_LIMIT_RETRY_AFTER_SECONDS", 5),
		BucketPreferAPIKey:    getBoolEnv("BUCKET_LIMIT_PREFER_API_KEY", true),
		CBEnabled:             getBoolEnv("CB_ENABLED", true),
		CBMaxRequests:         getIntEnv("CB_MAX_REQUESTS", 3),
		CBInterval:            getDurationEnv("CB_INTERVAL", 10*time.Second),
		CBTimeout:             getDurationEnv("CB_TIMEOUT", 15*time.Second),
		CBMinRequests:         getIntEnv("CB_MIN_REQUESTS", 5),
		CBErrorRateThreshold:  getIntRangeEnv("CB_ERROR_RATE_THRESHOLD", 50, 1, 100),
		CBRetryAfterSec:       getIntEnv("CB_RETRY_AFTER_SECONDS", 3),
		ShutdownTimeout:       getDurationEnv("SHUTDOWN_TIMEOUT", 10*time.Second),
		MaxInFlight:           getIntEnv("MAX_IN_FLIGHT", 2048),
		MaxIdleConns:          getIntEnv("MAX_IDLE_CONNS", 512),
		MaxIdleConnsPerHost:   getIntEnv("MAX_IDLE_CONNS_PER_HOST", 256),
		IdleConnTimeout:       getDurationEnv("IDLE_CONN_TIMEOUT", 90*time.Second),
		DialTimeout:           getDurationEnv("DIAL_TIMEOUT", 3*time.Second),
		TLSHandshakeTimeout:   getDurationEnv("TLS_HANDSHAKE_TIMEOUT", 5*time.Second),
		ExpectContinueTimeout: getDurationEnv("EXPECT_CONTINUE_TIMEOUT", 1*time.Second),
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

func getIntRangeEnv(key string, defaultVal, minVal, maxVal int) int {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(v)
	if err != nil || n < minVal || n > maxVal {
		return defaultVal
	}
	return n
}

func getBoolEnv(key string, defaultVal bool) bool {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	b, err := strconv.ParseBool(v)
	if err != nil {
		return defaultVal
	}
	return b
}
