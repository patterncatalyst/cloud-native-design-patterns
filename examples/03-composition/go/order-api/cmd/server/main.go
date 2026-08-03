package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"

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

	mux.HandleFunc("GET /orders", func(w http.ResponseWriter, r *http.Request) {
		rows, err := pool.Query(r.Context(),
			"SELECT id, sku, quantity, status FROM orders ORDER BY id")
		if err != nil {
			http.Error(w, "internal error", 500)
			return
		}
		defer rows.Close()

		orders := make([]map[string]any, 0)
		for rows.Next() {
			var id, sku, status string
			var quantity int
			rows.Scan(&id, &sku, &quantity, &status)
			orders = append(orders, map[string]any{
				"id": id, "sku": sku, "quantity": quantity, "status": status,
			})
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(orders)
	})

	mux.HandleFunc("GET /orders/{id}", func(w http.ResponseWriter, r *http.Request) {
		var id, sku, status string
		var quantity int
		err := pool.QueryRow(r.Context(),
			"SELECT id, sku, quantity, status FROM orders WHERE id=$1",
			r.PathValue("id")).Scan(&id, &sku, &quantity, &status)
		if err != nil {
			http.Error(w, "not found", 404)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"id": id, "sku": sku, "quantity": quantity, "status": status,
		})
	})

	srv := &http.Server{Addr: ":8081", Handler: mux}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting order-api on :8081")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}
