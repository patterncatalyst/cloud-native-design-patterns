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
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/twmb/franz-go/pkg/kgo"
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

	bootstrap := os.Getenv("KAFKA_BOOTSTRAP")
	if bootstrap == "" {
		bootstrap = "kafka:9094"
	}

	producer, err := kgo.NewClient(
		kgo.SeedBrokers(bootstrap),
		kgo.AllowAutoTopicCreation(),
	)
	if err != nil {
		slog.Error("kafka producer init failed", "err", err)
		os.Exit(1)
	}
	defer producer.Close()

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
		_, err := pool.Exec(r.Context(),
			"INSERT INTO orders (id, sku, quantity) VALUES ($1, $2, $3)",
			id, in.SKU, in.Quantity)
		if err != nil {
			slog.Error("insert order failed", "err", err)
			http.Error(w, "internal error", 500)
			return
		}

		event, _ := json.Marshal(map[string]any{
			"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": "pending",
		})
		rec := &kgo.Record{Topic: "order.placed", Key: []byte(id), Value: event}
		for attempt := range 5 {
			results := producer.ProduceSync(r.Context(), rec)
			if err := results.FirstErr(); err != nil {
				slog.Warn("kafka produce retry", "attempt", attempt+1, "err", err)
				time.Sleep(time.Duration(attempt+1) * 500 * time.Millisecond)
				continue
			}
			break
		}

		slog.Info("order placed", "id", id, "sku", in.SKU)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": "pending",
		})
	})

	mux.HandleFunc("GET /orders", func(w http.ResponseWriter, r *http.Request) {
		rows, err := pool.Query(r.Context(),
			"SELECT id, sku, quantity, status FROM orders ORDER BY created_at")
		if err != nil {
			http.Error(w, "internal error", 500)
			return
		}
		defer rows.Close()

		orders := make([]map[string]any, 0)
		for rows.Next() {
			var id, sku, status string
			var quantity int
			if err := rows.Scan(&id, &sku, &quantity, &status); err != nil {
				continue
			}
			orders = append(orders, map[string]any{
				"id": id, "sku": sku, "quantity": quantity, "status": status,
			})
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(orders)
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
