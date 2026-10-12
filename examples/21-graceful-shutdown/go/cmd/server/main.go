package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

type server struct {
	pool         *pgxpool.Pool
	shuttingDown atomic.Bool
	inFlight     atomic.Int64
}

func (s *server) healthz(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func (s *server) readyz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if s.shuttingDown.Load() {
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(map[string]any{"ready": false, "reason": "shutting down"})
		return
	}
	if err := s.pool.Ping(r.Context()); err != nil {
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(map[string]any{"ready": false, "reason": "db unreachable"})
		return
	}
	json.NewEncoder(w).Encode(map[string]any{"ready": true})
}

func (s *server) debugState(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"shutting_down": s.shuttingDown.Load(),
		"in_flight":     s.inFlight.Load(),
		"pid":           os.Getpid(),
	})
}

type orderIn struct {
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
}

type order struct {
	ID       string `json:"id"`
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
	Status   string `json:"status"`
}

func (s *server) createOrder(w http.ResponseWriter, r *http.Request) {
	s.inFlight.Add(1)
	defer s.inFlight.Add(-1)

	if s.shuttingDown.Load() {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(map[string]string{"error": "shutting down"})
		return
	}

	var in orderIn
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil || in.SKU == "" || in.Quantity <= 0 {
		w.WriteHeader(http.StatusBadRequest)
		return
	}

	id := uuid.New().String()
	_, err := s.pool.Exec(r.Context(),
		"INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, 'confirmed')",
		id, in.SKU, in.Quantity)
	if err != nil {
		slog.Error("insert failed", "err", err)
		w.WriteHeader(http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(order{ID: id, SKU: in.SKU, Quantity: in.Quantity, Status: "confirmed"})
}

func (s *server) listOrders(w http.ResponseWriter, r *http.Request) {
	rows, err := s.pool.Query(r.Context(),
		"SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50")
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var orders []order
	for rows.Next() {
		var o order
		if err := rows.Scan(&o.ID, &o.SKU, &o.Quantity, &o.Status); err != nil {
			continue
		}
		orders = append(orders, o)
	}
	if orders == nil {
		orders = []order{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(orders)
}

// shutdownTimeout bounds the connection drain; drain delay + shutdownTimeout stays under the
// 30s stop grace period.
const shutdownTimeout = 20 * time.Second

// drainDelay is the pre-stop delay that lets endpoint removal propagate (DRAIN_DELAY_SECONDS).
func drainDelay() time.Duration {
	if v, err := strconv.Atoi(os.Getenv("DRAIN_DELAY_SECONDS")); err == nil && v >= 0 {
		return time.Duration(v) * time.Second
	}
	return 5 * time.Second
}

func main() {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgresql://appuser:apppass@postgres:5432/appdb"
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dbURL)
	if err != nil {
		slog.Error("db connect failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	s := &server{pool: pool}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", s.healthz)
	mux.HandleFunc("GET /readyz", s.readyz)
	mux.HandleFunc("GET /debug/state", s.debugState)
	mux.HandleFunc("POST /orders", s.createOrder)
	mux.HandleFunc("GET /orders", s.listOrders)

	httpServer := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	// One SIGTERM starts the whole drain. Kubernetes sends it once and follows with SIGKILL
	// when terminationGracePeriodSeconds runs out.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	go func() {
		slog.Info("starting order-service", "pid", os.Getpid())
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("server error", "err", err)
			os.Exit(1)
		}
	}()

	// 1. Flip readiness so the endpoints controller removes this pod.
	<-ctx.Done()
	stop() // restore default handling: a later signal terminates immediately
	s.shuttingDown.Store(true)
	slog.Info("SIGTERM received — readiness flipped, draining in-flight requests")

	// 2. Keep serving while endpoints propagate (the pre-stop delay).
	delay := drainDelay()
	slog.Info("waiting for endpoints to update", "delay", delay.String())
	time.Sleep(delay)

	// 3. Stop accepting connections and finish in-flight requests, bounded so the whole
	//    sequence fits inside terminationGracePeriodSeconds.
	slog.Info("shutting down HTTP server", "in_flight", s.inFlight.Load())
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		slog.Error("shutdown incomplete", "err", err, "in_flight", s.inFlight.Load())
	}

	// 4. Cleanup (deferred pool.Close) and exit 0.
	slog.Info("order-service shutdown complete")
}
