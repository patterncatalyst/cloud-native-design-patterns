package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/cenkalti/backoff/v7"
	"github.com/sony/gobreaker/v2"
	"golang.org/x/sync/semaphore"
)

const bulkheadSize = 5

var (
	backendURL string
	client     = &http.Client{}
	// Circuit breaker: 5 failures in a row open it, it stays open 10 s, then 2 successful trial calls close it.
	cb = gobreaker.NewCircuitBreaker[[]byte](gobreaker.Settings{
		Name:        "backend",
		MaxRequests: 2,
		Timeout:     10 * time.Second,
		ReadyToTrip: func(counts gobreaker.Counts) bool { return counts.ConsecutiveFailures >= 5 },
	})
	// Bulkhead: at most 5 calls in flight; TryAcquire turns the sixth away at once.
	bulkhead = semaphore.NewWeighted(bulkheadSize)
)

// statusError is a backend answer of 500 or above.
type statusError struct{ code int }

func (e statusError) Error() string { return fmt.Sprintf("HTTP %d", e.code) }

func main() {
	backendURL = os.Getenv("BACKEND_URL")
	if backendURL == "" {
		backendURL = "http://backend:8081"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /with-timeout", handleTimeout)
	mux.HandleFunc("GET /with-retry", handleRetry)
	mux.HandleFunc("GET /with-breaker", handleBreaker)
	mux.HandleFunc("GET /breaker-state", handleBreakerState)
	mux.HandleFunc("GET /with-deadline", handleDeadline)
	mux.HandleFunc("GET /with-bulkhead", handleBulkhead)
	mux.HandleFunc("GET /bulkhead-state", handleBulkheadState)

	slog.Info("starting edge-service on :8080")
	httpSrv := &http.Server{Addr: ":8080", Handler: mux}
	sigCtx, stopSignals := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stopSignals()
	go func() {
		<-sigCtx.Done()
		slog.Info("shutting down")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		httpSrv.Shutdown(shutdownCtx)
	}()
	if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func parse(body []byte) map[string]any {
	var parsed map[string]any
	json.Unmarshal(body, &parsed)
	return parsed
}

func callBackend(ctx context.Context, headers map[string]string) (int, []byte, error) {
	req, _ := http.NewRequestWithContext(ctx, "GET", backendURL+"/process", nil)
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	resp, err := client.Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	return resp.StatusCode, body, nil
}

// call2s is one backend call that gives up after 2 s; a 5xx comes back as a statusError.
func call2s(ctx context.Context) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	code, body, err := callBackend(ctx, nil)
	if err != nil {
		return nil, err
	}
	if code >= 500 {
		return nil, statusError{code}
	}
	return body, nil
}

func elapsed(start time.Time) float64 { return float64(time.Since(start).Milliseconds()) / 1000 }

func handleTimeout(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	code, body, err := callBackend(ctx, nil)
	if err != nil {
		writeJSON(w, 200, map[string]any{"error": "timeout", "elapsed_s": elapsed(start), "pattern": "timeout"})
		return
	}
	writeJSON(w, 200, map[string]any{"status": code, "elapsed_s": elapsed(start), "body": parse(body)})
}

func handleRetry(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	bo := backoff.NewExponentialBackOff() // 100 ms doubling to 2 s, each wait randomised by up to 50%
	bo.InitialInterval = 100 * time.Millisecond
	bo.MaxInterval = 2 * time.Second

	var attempts int
	body, err := backoff.Retry(r.Context(), func() ([]byte, error) {
		attempts++
		return call2s(r.Context())
	}, backoff.WithBackOff(bo), backoff.WithMaxTries(3), backoff.WithMaxElapsedTime(15*time.Second))

	if err != nil {
		if re := backoff.AsRetryError(err); re != nil {
			err = re.LastErr // the failure the caller cares about, not the stop reason
		}
		msg := "timeout"
		if se, ok := errors.AsType[statusError](err); ok {
			msg = se.Error()
		}
		writeJSON(w, 200, map[string]any{
			"error": msg, "attempts": attempts, "elapsed_s": elapsed(start), "pattern": "retry-exhausted",
		})
		return
	}
	writeJSON(w, 200, map[string]any{"status": 200, "attempts": attempts, "elapsed_s": elapsed(start), "body": parse(body)})
}

func handleBreaker(w http.ResponseWriter, r *http.Request) {
	body, err := cb.Execute(func() ([]byte, error) { return call2s(r.Context()) })
	if err == nil {
		writeJSON(w, 200, map[string]any{"source": "live", "body": parse(body), "breaker": cb.State().String()})
		return
	}
	reason := "upstream_unreachable"
	if errors.Is(err, gobreaker.ErrOpenState) || errors.Is(err, gobreaker.ErrTooManyRequests) {
		reason = "circuit_open"
	} else if se, ok := errors.AsType[statusError](err); ok {
		reason = fmt.Sprintf("upstream_%d", se.code)
	}
	writeJSON(w, 200, map[string]any{"source": "fallback", "reason": reason, "breaker": cb.State().String()})
}

// handleBreakerState reports closed, open or half-open.
func handleBreakerState(w http.ResponseWriter, _ *http.Request) {
	counts := cb.Counts()
	writeJSON(w, 200, map[string]any{
		"name": cb.Name(), "state": cb.State().String(), "consecutive_failures": counts.ConsecutiveFailures,
	})
}

func handleDeadline(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	budget := 1000
	if v, err := strconv.Atoi(r.URL.Query().Get("budget_ms")); err == nil {
		budget = v
	}
	remaining := budget - 50 // edge overhead

	if remaining < 50 {
		writeJSON(w, 200, map[string]any{
			"error": "deadline_exceeded", "reason": "insufficient budget at edge",
			"budget_ms": budget, "remaining_ms": remaining,
		})
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), time.Duration(remaining)*time.Millisecond)
	defer cancel()
	code, body, err := callBackend(ctx, map[string]string{"X-Deadline-Ms": strconv.Itoa(remaining)})
	if err != nil {
		writeJSON(w, 200, map[string]any{
			"error": "deadline_exceeded", "reason": "timed out waiting for backend",
			"budget_ms": budget, "elapsed_s": elapsed(start),
		})
		return
	}
	writeJSON(w, 200, map[string]any{
		"status": code, "budget_ms": budget, "remaining_ms": remaining, "elapsed_s": elapsed(start), "body": parse(body),
	})
}

func handleBulkhead(w http.ResponseWriter, r *http.Request) {
	if !bulkhead.TryAcquire(1) {
		writeJSON(w, 429, map[string]any{"error": "bulkhead_full", "pattern": "bulkhead"})
		return
	}
	defer bulkhead.Release(1)

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	code, body, err := callBackend(ctx, nil)
	if err != nil {
		writeJSON(w, 200, map[string]any{"error": "timeout"})
		return
	}
	writeJSON(w, 200, map[string]any{"status": code, "body": parse(body)})
}

func handleBulkheadState(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, 200, map[string]any{"max_concurrent": bulkheadSize})
}
