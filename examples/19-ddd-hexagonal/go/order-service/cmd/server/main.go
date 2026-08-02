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
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/19-ddd-hexagonal/go/order-service/adapters"
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/19-ddd-hexagonal/go/order-service/domain"
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

	repo := adapters.NewPostgresRepo(pool)
	pub := &adapters.LogPublisher{}
	placeOrder := domain.NewPlaceOrder(repo, pub)

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
		json.NewDecoder(r.Body).Decode(&in)

		order, err := placeOrder.Execute(r.Context(), domain.PlaceOrderCmd{
			SKU: in.SKU, Quantity: in.Quantity,
		})
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(422)
			json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"id": order.ID, "sku": order.SKU, "quantity": order.Quantity, "status": order.Status,
		})
	})

	mux.HandleFunc("GET /orders/{id}", func(w http.ResponseWriter, r *http.Request) {
		order, err := repo.FindByID(r.Context(), r.PathValue("id"))
		if err != nil {
			http.Error(w, "not found", 404)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"id": order.ID, "sku": order.SKU, "quantity": order.Quantity, "status": order.Status,
		})
	})

	mux.HandleFunc("GET /orders", func(w http.ResponseWriter, r *http.Request) {
		orders, err := repo.FindAll(r.Context())
		if err != nil {
			http.Error(w, "internal error", 500)
			return
		}
		result := make([]map[string]any, 0, len(orders))
		for _, o := range orders {
			result = append(result, map[string]any{
				"id": o.ID, "sku": o.SKU, "quantity": o.Quantity, "status": o.Status,
			})
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
	})

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		slog.Info("shutting down")
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting order-service")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}
