package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os/signal"
	"strconv"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

var (
	mode      = "healthy"
	callCount atomic.Int64
	mu        sync.RWMutex
)

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /mode", func(w http.ResponseWriter, r *http.Request) {
		var in struct {
			Mode string `json:"mode"`
		}
		json.NewDecoder(r.Body).Decode(&in)
		mu.Lock()
		mode = in.Mode
		mu.Unlock()
		callCount.Store(0)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"mode": in.Mode, "call_count": 0})
	})

	mux.HandleFunc("GET /mode", func(w http.ResponseWriter, _ *http.Request) {
		mu.RLock()
		m := mode
		mu.RUnlock()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"mode": m, "call_count": callCount.Load()})
	})

	mux.HandleFunc("GET /process", func(w http.ResponseWriter, r *http.Request) {
		callCount.Add(1)

		if dl := r.Header.Get("X-Deadline-Ms"); dl != "" {
			ms, _ := strconv.Atoi(dl)
			if ms > 0 && ms < 100 {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]any{"status": "rejected", "reason": "deadline_too_small", "remaining_ms": ms})
				return
			}
		}

		mu.RLock()
		m := mode
		mu.RUnlock()

		w.Header().Set("Content-Type", "application/json")
		switch m {
		case "slow":
			time.Sleep(5 * time.Second)
			json.NewEncoder(w).Encode(map[string]string{"status": "ok", "mode": "slow"})
		case "failing":
			w.WriteHeader(500)
			json.NewEncoder(w).Encode(map[string]string{"error": "backend failing"})
		default:
			json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		}
	})

	slog.Info("starting backend-service on :8081")
	httpSrv := &http.Server{Addr: ":8081", Handler: mux}
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
