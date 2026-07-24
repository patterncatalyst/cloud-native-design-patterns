package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type Server struct {
	pool    *pgxpool.Pool
	version string
}

type RootResponse struct {
	Service      string `json:"service"`
	Version      string `json:"version"`
	ConfigSource string `json:"config_source"`
}

type HealthResponse struct {
	Status string `json:"status"`
}

type ReadinessResponse struct {
	Status string                    `json:"status"`
	Checks map[string]string         `json:"checks"`
}

type Order struct {
	ID       int    `json:"id"`
	Customer string `json:"customer"`
	Total    string `json:"total"`
}

func (s *Server) handleRoot(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(RootResponse{
		Service:      "order-service",
		Version:      s.version,
		ConfigSource: "environment",
	})
}

func (s *Server) handleHealthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(HealthResponse{
		Status: "ok",
	})
}

func (s *Server) handleReadyz(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	w.Header().Set("Content-Type", "application/json")

	if err := s.pool.Ping(ctx); err != nil {
		slog.Error("readiness check failed", "error", err)
		json.NewEncoder(w).Encode(ReadinessResponse{
			Status: "down",
			Checks: map[string]string{
				"database": "unreachable",
			},
		})
		return
	}

	json.NewEncoder(w).Encode(ReadinessResponse{
		Status: "ready",
		Checks: map[string]string{
			"database": "ok",
		},
	})
}

func (s *Server) handleGetOrders(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	rows, err := s.pool.Query(ctx, "SELECT id, customer, total FROM orders")
	if err != nil {
		slog.Error("failed to query orders", "error", err)
		http.Error(w, "database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	orders := []Order{}
	for rows.Next() {
		var order Order
		if err := rows.Scan(&order.ID, &order.Customer, &order.Total); err != nil {
			slog.Error("failed to scan order", "error", err)
			http.Error(w, "scan error", http.StatusInternalServerError)
			return
		}
		orders = append(orders, order)
	}

	if err := rows.Err(); err != nil {
		slog.Error("rows iteration error", "error", err)
		http.Error(w, "iteration error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(orders)
}

func (s *Server) handlePostOrder(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	customer := r.URL.Query().Get("customer")
	total := r.URL.Query().Get("total")

	if customer == "" || total == "" {
		http.Error(w, "customer and total required", http.StatusBadRequest)
		return
	}

	var id int
	err := s.pool.QueryRow(ctx,
		"INSERT INTO orders (customer, total) VALUES ($1, $2::numeric) RETURNING id",
		customer, total).Scan(&id)
	if err != nil {
		slog.Error("failed to insert order", "error", err)
		http.Error(w, "insert error", http.StatusInternalServerError)
		return
	}

	order := Order{
		ID:       id,
		Customer: customer,
		Total:    total,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(order)
}

func (s *Server) handleOrders(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.handleGetOrders(w, r)
	case http.MethodPost:
		s.handlePostOrder(w, r)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func main() {
	slog.Info("starting order-service")

	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgresql://appuser:apppass@postgres:5432/appdb"
	}

	version := os.Getenv("SERVICE_VERSION")
	if version == "" {
		version = "0.0.0"
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dbURL)
	if err != nil {
		slog.Error("failed to create connection pool", "error", err)
		os.Exit(1)
	}
	defer pool.Close()

	// Wait for database to be ready
	for i := 0; i < 30; i++ {
		if err := pool.Ping(ctx); err == nil {
			slog.Info("connected to database")
			break
		}
		slog.Info("waiting for database", "attempt", i+1)
		time.Sleep(time.Second)
	}

	server := &Server{
		pool:    pool,
		version: version,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", server.handleRoot)
	mux.HandleFunc("/healthz", server.handleHealthz)
	mux.HandleFunc("/readyz", server.handleReadyz)
	mux.HandleFunc("/orders", server.handleOrders)

	httpServer := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	// Graceful shutdown
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		slog.Info("server listening", "addr", httpServer.Addr)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("server error", "error", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()
	slog.Info("shutting down gracefully")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		slog.Error("shutdown error", "error", err)
	}

	slog.Info("server stopped")
}
