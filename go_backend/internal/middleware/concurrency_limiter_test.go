package middleware

import (
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
