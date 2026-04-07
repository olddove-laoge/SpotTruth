package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

func TestConcurrencyLimiterRejectsWhenBusy(t *testing.T) {
	h := ConcurrencyLimiter(1, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(120 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	}))

	var wg sync.WaitGroup
	wg.Add(2)

	statusCh := make(chan int, 2)
	call := func() {
		defer wg.Done()
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		rr := httptest.NewRecorder()
		h.ServeHTTP(rr, req)
		statusCh <- rr.Code
	}

	go call()
	time.Sleep(20 * time.Millisecond)
	go call()

	wg.Wait()
	close(statusCh)

	got503 := false
	got200 := false
	for s := range statusCh {
		if s == http.StatusServiceUnavailable {
			got503 = true
		}
		if s == http.StatusOK {
			got200 = true
		}
	}

	if !got200 || !got503 {
		t.Fatalf("并发限制结果不符合预期: got200=%v got503=%v", got200, got503)
	}
}

func TestConcurrencyLimiterStructured503(t *testing.T) {
	h := ConcurrencyLimiterWithOptions(1, 2, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(120 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	}))

	firstDone := make(chan struct{})
	go func() {
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		rr := httptest.NewRecorder()
		h.ServeHTTP(rr, req)
		close(firstDone)
	}()

	time.Sleep(20 * time.Millisecond)
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusServiceUnavailable {
		t.Fatalf("状态码错误: got=%d want=%d", rr.Code, http.StatusServiceUnavailable)
	}
	if rr.Header().Get("Retry-After") != "2" {
		t.Fatalf("Retry-After 错误: %s", rr.Header().Get("Retry-After"))
	}

	var body struct {
		Code string `json:"code"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("返回 JSON 非法: %v", err)
	}
	if body.Code != "GATEWAY_CONCURRENCY_LIMITED" {
		t.Fatalf("错误码错误: %s", body.Code)
	}

	<-firstDone
}
