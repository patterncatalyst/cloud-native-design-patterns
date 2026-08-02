package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
)

var version string

func main() {
	version = os.Getenv("APP_VERSION")
	if version == "" {
		version = "v1"
	}

	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok", "version": version})
	})

	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in struct {
			SKU      string `json:"sku"`
			Quantity int    `json:"quantity"`
		}
		json.NewDecoder(r.Body).Decode(&in)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"id": "1", "sku": in.SKU, "quantity": in.Quantity, "version": version,
		})
	})

	mux.HandleFunc("GET /orders", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"orders": []any{}, "version": version})
	})

	slog.Info("starting order-service", "version", version)
	http.ListenAndServe(":8080", mux)
}
