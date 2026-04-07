package gateway

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type ReadinessChecker func(ctx context.Context) error

func NewHTTPReadinessChecker(baseURL, healthPath string, timeout time.Duration) ReadinessChecker {
	trimmedBase := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	path := healthPath
	if path == "" {
		path = "/healthz"
	}
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	if timeout <= 0 {
		timeout = 2 * time.Second
	}

	client := &http.Client{Timeout: timeout}
	url := trimmedBase + path

	return func(ctx context.Context) error {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			return fmt.Errorf("创建 readiness 请求失败: %w", err)
		}

		resp, err := client.Do(req)
		if err != nil {
			return fmt.Errorf("上游不可用: %w", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			return fmt.Errorf("上游探测失败: status=%d", resp.StatusCode)
		}
		return nil
	}
}
