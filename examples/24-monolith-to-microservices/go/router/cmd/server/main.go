package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"os"
	"sync"
	"time"
)

type rules struct {
	mu           sync.RWMutex
	TenantRoutes map[string]string `json:"tenant_routes"`
	Default      string            `json:"default"`
}

var (
	routing  *rules
	backends map[string]string
	client   = &http.Client{Timeout: 5 * time.Second}
)

func main() {
	backends = map[string]string{
		"monolith":    os.Getenv("MONOLITH_URL"),
		"new-service": os.Getenv("NEW_SERVICE_URL"),
	}
	routing = &rules{
		TenantRoutes: map[string]string{"acme": "new-service"},
		Default:      "monolith",
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /rules", func(w http.ResponseWriter, _ *http.Request) {
		routing.mu.RLock()
		defer routing.mu.RUnlock()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"tenant_routes": routing.TenantRoutes, "default": routing.Default,
		})
	})
	mux.HandleFunc("PUT /rules", func(w http.ResponseWriter, r *http.Request) {
		var update struct {
			TenantRoutes map[string]string `json:"tenant_routes"`
			Default      string            `json:"default"`
		}
		json.NewDecoder(r.Body).Decode(&update)
		routing.mu.Lock()
		if update.TenantRoutes != nil {
			routing.TenantRoutes = update.TenantRoutes
		}
		if update.Default != "" {
			routing.Default = update.Default
		}
		routing.mu.Unlock()
		slog.Info("rules updated")
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "updated"})
	})
	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		var in struct {
			Tenant string `json:"tenant"`
		}
		json.Unmarshal(body, &in)

		routing.mu.RLock()
		target := routing.Default
		if dest, ok := routing.TenantRoutes[in.Tenant]; ok {
			target = dest
		}
		routing.mu.RUnlock()

		url := backends[target] + "/orders"
		resp, err := client.Post(url, "application/json", bytes.NewReader(body))
		if err != nil {
			http.Error(w, "backend error", 502)
			return
		}
		defer resp.Body.Close()
		respBody, _ := io.ReadAll(resp.Body)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(resp.StatusCode)
		w.Write(respBody)
	})

	slog.Info("starting router on :8080")
	http.ListenAndServe(":8080", mux)
}
