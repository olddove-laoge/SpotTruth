package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"spottruth/go_backend/internal/auth"
	"spottruth/go_backend/internal/config"
	"spottruth/go_backend/internal/gateway"
)

func main() {
	cfg := config.Load()

	proxy, err := gateway.NewReverseProxy(cfg.UpstreamBaseURL, gateway.ProxyOptions{
		MaxIdleConns:          cfg.MaxIdleConns,
		MaxIdleConnsPerHost:   cfg.MaxIdleConnsPerHost,
		IdleConnTimeout:       cfg.IdleConnTimeout,
		DialTimeout:           cfg.DialTimeout,
		TLSHandshakeTimeout:   cfg.TLSHandshakeTimeout,
		ExpectContinueTimeout: cfg.ExpectContinueTimeout,
		ResponseHeaderTimeout: cfg.ResponseHeaderTimeout,
	})
	if err != nil {
		log.Fatalf("UPSTREAM_BASE_URL 非法: %v", err)
	}

	handlerOptions := gateway.HandlerOptions{
		ReadinessChecker:        gateway.NewHTTPReadinessChecker(cfg.UpstreamBaseURL, cfg.UpstreamHealthPath, cfg.ReadinessTimeout),
		LimiterRetryAfterSecond: cfg.LimiterRetryAfterSec,
	}

	if cfg.AuthEnabled {
		tokenManager, err := auth.NewTokenManager(cfg.AuthSigningKey, cfg.AuthIssuer, cfg.AuthAccessTTL)
		if err != nil {
			log.Fatalf("鉴权配置非法: %v", err)
		}
		handlerOptions.TokenManager = tokenManager
	}

	handler := gateway.NewHandlerWithOptions(proxy, cfg.MaxInFlight, handlerOptions)

	server := &http.Server{
		Addr:              cfg.GatewayAddr,
		Handler:           handler,
		ReadHeaderTimeout: cfg.ReadHeaderTimeout,
		ReadTimeout:       cfg.ReadTimeout,
		WriteTimeout:      cfg.WriteTimeout,
		IdleTimeout:       cfg.IdleTimeout,
	}

	go func() {
		log.Printf("API 网关启动: addr=%s upstream=%s", cfg.GatewayAddr, cfg.UpstreamBaseURL)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("网关启动失败: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	ctx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()

	log.Println("网关正在优雅停机")
	if err := server.Shutdown(ctx); err != nil {
		log.Printf("优雅停机失败: %v", err)
	}
}
