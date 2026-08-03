package main

import (
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"sync"
	"sync/atomic"
)

var (
	serviceName string
	orders      sync.Map
	accessCount sync.Map
)

func main() {
	serviceName = os.Getenv("SERVICE_NAME")
	if serviceName == "" {
		serviceName = "stub"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok", "source": serviceName})
	})
	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in struct {
			SKU      string `json:"sku"`
			Quantity int    `json:"quantity"`
			Tenant   string `json:"tenant"`
		}
		json.NewDecoder(r.Body).Decode(&in)

		id := newUUID()
		o := map[string]any{
			"id": id, "sku": in.SKU, "quantity": in.Quantity,
			"tenant": in.Tenant, "source": serviceName,
		}
		orders.Store(id, o)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(201)
		json.NewEncoder(w).Encode(o)
	})
	mux.HandleFunc("GET /orders/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		val, _ := accessCount.LoadOrStore(id, &atomic.Int64{})
		val.(*atomic.Int64).Add(1)

		v, ok := orders.Load(id)
		if !ok {
			http.Error(w, "not found", 404)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(v)
	})
	mux.HandleFunc("GET /access-count/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		val, ok := accessCount.Load(id)
		count := int64(0)
		if ok {
			count = val.(*atomic.Int64).Load()
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"id": id, "count": count})
	})

	slog.Info("starting stub-service", "name", serviceName)
	http.ListenAndServe(":8080", mux)
}

func newUUID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
