package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/open-feature/go-sdk-contrib/providers/flagd/pkg"
	"github.com/open-feature/go-sdk/openfeature"
)

var ofClient *openfeature.Client

func main() {
	host := os.Getenv("FLAGD_HOST")
	if host == "" {
		host = "flagd"
	}
	port := uint16(8013)
	if p := os.Getenv("FLAGD_PORT"); p != "" {
		if n, err := strconv.Atoi(p); err == nil {
			port = uint16(n)
		}
	}

	provider, err := flagd.NewProvider(
		flagd.WithHost(host),
		flagd.WithPort(port),
	)
	if err != nil {
		slog.Error("flagd provider init failed", "err", err)
		os.Exit(1)
	}
	openfeature.SetProvider(provider)
	ofClient = openfeature.NewClient("flag-service")

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /checkout", handleCheckout)
	mux.HandleFunc("GET /recommendations", handleRecommendations)
	mux.HandleFunc("GET /ui-config", handleUIConfig)
	mux.HandleFunc("GET /flags", handleFlags)

	slog.Info("starting flag-service on :8080")
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

func evalCtx(r *http.Request) openfeature.EvaluationContext {
	user := r.Header.Get("X-User")
	if user == "" {
		user = "anonymous"
	}
	attrs := map[string]interface{}{}
	if plan := r.Header.Get("X-Plan"); plan != "" {
		attrs["plan"] = plan
	}
	return openfeature.NewEvaluationContext(user, attrs)
}

func handleCheckout(w http.ResponseWriter, r *http.Request) {
	ctx := evalCtx(r)
	newCheckout, _ := ofClient.BooleanValue(r.Context(), "new-checkout", false, ctx)
	path := "legacy"
	if newCheckout {
		path = "new"
	}
	writeJSON(w, 200, map[string]any{"path": path, "new_checkout": newCheckout})
}

func handleRecommendations(w http.ResponseWriter, r *http.Request) {
	ctx := evalCtx(r)
	enabled, _ := ofClient.BooleanValue(r.Context(), "recommendations-enabled", true, ctx)
	if enabled {
		writeJSON(w, 200, map[string]any{
			"reason":   "live",
			"products": []string{"product-a", "product-b", "product-c"},
		})
	} else {
		writeJSON(w, 200, map[string]any{
			"reason":   "killed",
			"products": []string{},
		})
	}
}

func handleUIConfig(w http.ResponseWriter, r *http.Request) {
	ctx := evalCtx(r)
	darkMode, _ := ofClient.BooleanValue(r.Context(), "dark-mode", false, ctx)
	writeJSON(w, 200, map[string]any{"dark_mode": darkMode})
}

func handleFlags(w http.ResponseWriter, r *http.Request) {
	ctx := evalCtx(r)
	newCheckout, _ := ofClient.BooleanValue(r.Context(), "new-checkout", false, ctx)
	recsEnabled, _ := ofClient.BooleanValue(r.Context(), "recommendations-enabled", true, ctx)
	darkMode, _ := ofClient.BooleanValue(r.Context(), "dark-mode", false, ctx)
	writeJSON(w, 200, map[string]any{
		"new-checkout":            newCheckout,
		"recommendations-enabled": recsEnabled,
		"dark-mode":               darkMode,
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
