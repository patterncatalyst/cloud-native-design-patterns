package main

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		slog.Error("db connect failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in struct {
			SKU      string `json:"sku"`
			Quantity int    `json:"quantity"`
		}
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			http.Error(w, "bad request", 400)
			return
		}

		id := newUUID()
		payload, _ := json.Marshal(map[string]any{
			"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": "confirmed",
		})

		tx, err := pool.Begin(r.Context())
		if err != nil {
			slog.Error("begin tx failed", "err", err)
			http.Error(w, "internal error", 500)
			return
		}
		defer tx.Rollback(r.Context())

		if _, err := tx.Exec(r.Context(),
			"INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, 'confirmed')",
			id, in.SKU, in.Quantity); err != nil {
			slog.Error("insert order failed", "err", err)
			http.Error(w, "internal error", 500)
			return
		}

		if _, err := tx.Exec(r.Context(),
			"INSERT INTO outbox (aggregate_id, event_type, payload) VALUES ($1, 'order.placed', $2)",
			id, payload); err != nil {
			slog.Error("insert outbox failed", "err", err)
			http.Error(w, "internal error", 500)
			return
		}

		if err := tx.Commit(r.Context()); err != nil {
			slog.Error("commit failed", "err", err)
			http.Error(w, "internal error", 500)
			return
		}

		slog.Info("order placed with outbox", "id", id, "sku", in.SKU)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": "confirmed",
		})
	})

	mux.HandleFunc("GET /orders", func(w http.ResponseWriter, r *http.Request) {
		limit := 50
		if v := r.URL.Query().Get("limit"); v != "" {
			if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
				limit = n
			}
		}
		rows, err := pool.Query(r.Context(),
			"SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at DESC LIMIT $1", limit)
		if err != nil {
			http.Error(w, "internal error", 500)
			return
		}
		defer rows.Close()

		orders := make([]map[string]any, 0)
		for rows.Next() {
			var id, sku, status string
			var quantity int
			var createdAt time.Time
			if err := rows.Scan(&id, &sku, &quantity, &status, &createdAt); err != nil {
				continue
			}
			orders = append(orders, map[string]any{
				"id": id, "sku": sku, "quantity": quantity, "status": status,
				"created_at": createdAt.Format(time.RFC3339),
			})
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(orders)
	})

	mux.HandleFunc("GET /outbox", func(w http.ResponseWriter, r *http.Request) {
		limit := 50
		if v := r.URL.Query().Get("limit"); v != "" {
			if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
				limit = n
			}
		}
		rows, err := pool.Query(r.Context(),
			"SELECT id, aggregate_id, event_type, payload, created_at FROM outbox ORDER BY id DESC LIMIT $1", limit)
		if err != nil {
			http.Error(w, "internal error", 500)
			return
		}
		defer rows.Close()

		events := make([]map[string]any, 0)
		for rows.Next() {
			var id int64
			var aggID, eventType string
			var payload json.RawMessage
			var createdAt time.Time
			if err := rows.Scan(&id, &aggID, &eventType, &payload, &createdAt); err != nil {
				continue
			}
			events = append(events, map[string]any{
				"id": id, "aggregate_id": aggID, "event_type": eventType,
				"payload": json.RawMessage(payload), "created_at": createdAt.Format(time.RFC3339),
			})
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(events)
	})

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		slog.Info("shutting down order-service")
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting order-service")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func newUUID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
