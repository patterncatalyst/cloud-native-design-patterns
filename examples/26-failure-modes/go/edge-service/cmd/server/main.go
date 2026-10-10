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
)

var (
	backendURL string
	client     = &http.Client{}
	cb         *gobreaker.CircuitBreaker[[]byte]
	bulkhead   = make(chan struct{}, 5)
)

func main() {
	backendURL = os.Getenv("BACKEND_URL")
	if backendURL == "" {
		backendURL = "http://backend:8081"
	}

	cb = gobreaker.NewCircuitBreaker[[]byte](gobreaker.Settings{
		Name:        "backend",
		MaxRequests: 1,
		Timeout:     10 * time.Second,
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			return counts.ConsecutiveFailures >= 5
		},
	})

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

func callBackend(ctx context.Context, headers map[string]string) (int, []byte, error) {
	req, _ := http.NewRequestWithContext(ctx, "GET", backendURL, nil)
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

func handleTimeout(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	code, body, err := callBackend(ctx, nil)
	elapsed := time.Since(start).Seconds()

	if err != nil {
		writeJSON(w, 200, map[string]any{
			"error": "timeout", "elapsed_s": elapsed, "pattern": "timeout",
		})
		return
	}

	var parsed map[string]any
	json.Unmarshal(body, &parsed)
	writeJSON(w, 200, map[string]any{
		"status": code, "elapsed_s": elapsed, "data": parsed,
	})
}

func handleRetry(w http.ResponseWriter, r *http.Request) {
	bo := backoff.NewExponentialBackOff()
	bo.InitialInterval = 500 * time.Millisecond
	bo.MaxInterval = 2 * time.Second

	var attempts int
	var lastBody []byte
	var lastCode int

	// One try plus two retries, with exponential delay between them. Retry also stops when
	// the request context ends or 15 s have passed.
	_, err := backoff.Retry(r.Context(), func() (struct{}, error) {
		attempts++
		code, body, err := callBackend(r.Context(), nil)
		if err != nil {
			return struct{}{}, fmt.Errorf("backend unreachable: %w", err)
		}
		lastCode = code
		lastBody = body
		if code >= 500 {
			return struct{}{}, fmt.Errorf("backend error: %d", code)
		}
		return struct{}{}, nil
	}, backoff.WithBackOff(bo), backoff.WithMaxTries(3), backoff.WithMaxElapsedTime(15*time.Second))

	if err != nil {
		msg := err.Error()
		if re := backoff.AsRetryError(err); re != nil {
			msg = re.LastErr.Error() // the failure the caller cares about, not the stop reason
		}
		writeJSON(w, 200, map[string]any{
			"error": msg, "attempts": attempts, "pattern": "retry-exhausted",
		})
		return
	}

	var parsed map[string]any
	json.Unmarshal(lastBody, &parsed)
	writeJSON(w, 200, map[string]any{
		"status": lastCode, "attempts": attempts, "data": parsed,
	})
}

func handleBreaker(w http.ResponseWriter, r *http.Request) {
	body, err := cb.Execute(func() ([]byte, error) {
		code, body, err := callBackend(r.Context(), nil)
		if err != nil {
			return nil, err
		}
		if code >= 500 {
			return nil, fmt.Errorf("backend error: %d", code)
		}
		return body, nil
	})

	if err != nil {
		if errors.Is(err, gobreaker.ErrOpenState) || errors.Is(err, gobreaker.ErrTooManyRequests) {
			writeJSON(w, 200, map[string]any{
				"error": "circuit breaker open", "reason": "circuit_open", "source": "fallback",
			})
			return
		}
		writeJSON(w, 200, map[string]any{"error": err.Error(), "source": "backend"})
		return
	}

	var parsed map[string]any
	json.Unmarshal(body, &parsed)
	writeJSON(w, 200, map[string]any{"status": 200, "data": parsed})
}

func handleBreakerState(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, 200, map[string]any{"state": cb.State().String()})
}

func handleDeadline(w http.ResponseWriter, r *http.Request) {
	budgetStr := r.URL.Query().Get("budget_ms")
	budget, _ := strconv.Atoi(budgetStr)

	if budget < 100 {
		writeJSON(w, 200, map[string]any{
			"error": "insufficient budget at edge", "budget_ms": budget,
		})
		return
	}

	remaining := budget - 50
	ctx, cancel := context.WithTimeout(r.Context(), time.Duration(remaining)*time.Millisecond)
	defer cancel()

	headers := map[string]string{"X-Deadline-Remaining": strconv.Itoa(remaining)}
	code, body, err := callBackend(ctx, headers)
	if err != nil {
		writeJSON(w, 200, map[string]any{"error": "timeout", "budget_ms": budget})
		return
	}

	if code == 422 {
		var parsed map[string]any
		json.Unmarshal(body, &parsed)
		writeJSON(w, 200, parsed)
		return
	}

	writeJSON(w, 200, map[string]any{"status": code, "budget_ms": budget})
}

func handleBulkhead(w http.ResponseWriter, r *http.Request) {
	select {
	case bulkhead <- struct{}{}:
		defer func() { <-bulkhead }()
	default:
		writeJSON(w, 503, map[string]any{"error": "bulkhead full"})
		return
	}

	code, body, err := callBackend(r.Context(), nil)
	if err != nil {
		writeJSON(w, 200, map[string]any{"error": err.Error()})
		return
	}

	var parsed map[string]any
	json.Unmarshal(body, &parsed)
	writeJSON(w, 200, map[string]any{"status": code, "data": parsed})
}

func handleBulkheadState(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, 200, map[string]any{
		"max_concurrent": 5,
		"current":        len(bulkhead),
	})
}
